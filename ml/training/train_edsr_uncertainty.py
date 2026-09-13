"""Trains EDSR with a heteroscedastic uncertainty head (out_channels=8:
4 mean + 4 log-variance), Gaussian NLL loss. See ml/uncertainty/heteroscedastic.py
and decisions.md D016.

Reports both standard reconstruction metrics (on the mean prediction) and
an uncertainty calibration check (does predicted variance correlate with
actual error?) at each epoch.
"""

import argparse
import os
import sys
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

sys.path.insert(0, ".")
from ml.datasets.sen2naip import SEN2NAIPCrossSensor, tile_disjoint_split
from ml.models.edsr.edsr import EDSR
from ml.evaluation.metrics import compute_all_metrics
from ml.uncertainty.heteroscedastic import split_mean_logvar, uncertainty_calibration

ROOT = "ml/datasets/raw/sen2naip/cross-sensor/extracted/cross-sensor"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--max-rois", type=int, default=None)
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--n-blocks", type=int, default=16)
    p.add_argument("--n-channels", type=int, default=64)
    p.add_argument("--checkpoint-dir", type=str, default="experiments/edsr_uncertainty")
    p.add_argument("--log-every", type=int, default=10)
    p.add_argument("--amp", action="store_true",
                    help="mixed-precision training (uses GPU Tensor Cores, e.g. on T4) -- "
                         "no-op on CPU. Loss (exp/division in Gaussian NLL) is still computed "
                         "in float32 for numerical stability; only the model forward pass runs fp16.")
    return p.parse_args()


def evaluate(model, val_ds, device, max_samples=50):
    model.eval()
    results = {"psnr": [], "ssim": [], "sam": [], "ergas": [], "calibration": []}
    with torch.no_grad():
        for i in range(min(max_samples, len(val_ds))):
            sample = val_ds[i]
            lr = sample["lr"].unsqueeze(0).to(device)
            hr = sample["hr"].unsqueeze(0).to(device)
            out = model(lr)
            mean, log_var = split_mean_logvar(out)

            results["calibration"].append(uncertainty_calibration(mean, log_var, hr))
            m = compute_all_metrics(mean.clamp(0.0, 1.0)[0].cpu().numpy(), hr[0].cpu().numpy())
            for k, v in m.items():
                results[k].append(v)
    model.train()
    return {k: sum(v) / len(v) for k, v in results.items()}


def main():
    args = parse_args()
    print(f"device: {args.device}")

    splits = tile_disjoint_split(ROOT)
    train_rois = splits["train"][: args.max_rois] if args.max_rois else splits["train"]
    train_ds = SEN2NAIPCrossSensor(train_rois)
    val_ds = SEN2NAIPCrossSensor(splits["val"])
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)

    print(f"train pairs: {len(train_ds)}  val pairs: {len(val_ds)}")

    model = EDSR(out_channels=8, n_channels=args.n_channels, n_blocks=args.n_blocks).to(args.device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    nll_loss = nn.GaussianNLLLoss()

    amp_enabled = args.amp and args.device == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=amp_enabled)
    if args.amp and not amp_enabled:
        print("--amp requested but no CUDA device -- running in plain fp32 (no-op on CPU)")

    os.makedirs(args.checkpoint_dir, exist_ok=True)

    step = 0
    for epoch in range(args.epochs):
        epoch_start = time.time()
        for batch in train_loader:
            lr = batch["lr"].to(args.device)
            hr = batch["hr"].to(args.device)

            optimizer.zero_grad()

            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=amp_enabled):
                out = model(lr)

            # loss (exp/division in Gaussian NLL) computed in fp32 regardless --
            # mixed precision here risks numerical instability on top of the
            # gradient-explosion history this loss already has (D016/D025)
            out = out.float()
            mean, log_var = split_mean_logvar(out)
            var = torch.exp(log_var)
            loss = nll_loss(mean, hr, var)

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)  # so clip_grad_norm_ sees true (unscaled) gradients
            grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            scaler.step(optimizer)
            scaler.update()

            if step % args.log_every == 0:
                print(f"epoch {epoch} step {step} loss {loss.item():.4f} grad_norm {grad_norm:.4f}")
            step += 1

        print(f"epoch {epoch} done in {time.time() - epoch_start:.1f}s")
        metrics = evaluate(model, val_ds, args.device)
        print(f"epoch {epoch} val metrics: {metrics}")

        if torch.cuda.is_available():
            torch.cuda.empty_cache()  # D025: switching train<->eval batch size fragments the allocator

        ckpt_path = f"{args.checkpoint_dir}/edsr_unc_epoch{epoch}.pt"
        torch.save(model.state_dict(), ckpt_path)
        print(f"saved {ckpt_path}")


if __name__ == "__main__":
    main()
