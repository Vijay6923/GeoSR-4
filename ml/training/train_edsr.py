"""Trains the EDSR baseline. L1 reconstruction loss only (PRD section 33) --
spectral/perceptual/edge loss terms come later (Phase 5), once this baseline
number exists to compare against.

Same script for local smoke-testing (CPU, tiny --max-rois) and real training
(Colab/Kaggle GPU, full dataset). See notebooks/train_edsr_colab.ipynb for
the GPU run, and decisions.md D009 for why compute is split this way.
"""

import argparse
import sys
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

sys.path.insert(0, ".")
from ml.datasets.sen2naip import SEN2NAIPCrossSensor, tile_disjoint_split
from ml.models.edsr.edsr import EDSR
from ml.evaluation.metrics import compute_all_metrics

ROOT = "ml/datasets/raw/sen2naip/cross-sensor/extracted/cross-sensor"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--max-rois", type=int, default=None, help="cap train set size, for smoke tests")
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--n-blocks", type=int, default=16)
    p.add_argument("--n-channels", type=int, default=64)
    p.add_argument("--checkpoint-dir", type=str, default="experiments/edsr")
    p.add_argument("--log-every", type=int, default=10)
    return p.parse_args()


def evaluate(model, val_ds, device, max_samples=50):
    model.eval()
    results = {"psnr": [], "ssim": [], "sam": [], "ergas": []}
    with torch.no_grad():
        for i in range(min(max_samples, len(val_ds))):
            sample = val_ds[i]
            lr = sample["lr"].unsqueeze(0).to(device)
            sr = model(lr)[0].clamp(0.0, 1.0).cpu().numpy()
            hr = sample["hr"].numpy()
            m = compute_all_metrics(sr, hr)
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

    model = EDSR(n_channels=args.n_channels, n_blocks=args.n_blocks).to(args.device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.L1Loss()

    import os
    os.makedirs(args.checkpoint_dir, exist_ok=True)

    step = 0
    for epoch in range(args.epochs):
        epoch_start = time.time()
        for batch in train_loader:
            lr = batch["lr"].to(args.device)
            hr = batch["hr"].to(args.device)

            sr = model(lr)
            loss = criterion(sr, hr)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            if step % args.log_every == 0:
                print(f"epoch {epoch} step {step} loss {loss.item():.4f}")
            step += 1

        print(f"epoch {epoch} done in {time.time() - epoch_start:.1f}s")
        metrics = evaluate(model, val_ds, args.device)
        print(f"epoch {epoch} val metrics: {metrics}")

        ckpt_path = f"{args.checkpoint_dir}/edsr_epoch{epoch}.pt"
        torch.save(model.state_dict(), ckpt_path)
        print(f"saved {ckpt_path}")


if __name__ == "__main__":
    main()
