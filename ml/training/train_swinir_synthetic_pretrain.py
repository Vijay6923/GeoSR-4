"""D048: synthetic-degradation pretraining -- pretrains SwinIR on the
synthetic NAIP-degradation corpus (generate_synthetic_pairs.py), then
fine-tunes the SAME model on the real SEN2NAIPCrossSensor train split,
evaluating on the real val split throughout (same protocol as train_swinir.py
so results are directly comparable to D013's from-scratch baseline).

Same L1-only default as D013's baseline (no perceptual/spectral/edge loss)
to isolate "does synthetic pretraining help" as its own single variable,
not entangled with the D023/D040/D042 loss-function questions.
"""

import argparse
import os
import sys
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

sys.path.insert(0, ".")
from ml.datasets.sen2naip import SEN2NAIPCrossSensor, tile_disjoint_split, load_norm_stats
from ml.datasets.synthetic_naip import SyntheticNAIPDataset
from ml.models.swinir.swinir import SwinIR
from ml.evaluation.metrics import compute_all_metrics

ROOT = "ml/datasets/raw/sen2naip/cross-sensor/extracted/cross-sensor"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--pretrain-epochs", type=int, default=20, help="epochs on the synthetic corpus")
    p.add_argument("--finetune-epochs", type=int, default=20, help="epochs on the real train split afterwards")
    p.add_argument("--batch-size", type=int, default=8, help="used for the (small) synthetic corpus")
    p.add_argument("--finetune-batch-size", type=int, default=16, help="used for the real train split")
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--embed-dim", type=int, default=60)
    p.add_argument("--depths", type=str, default="2,2,2,2")
    p.add_argument("--num-heads", type=int, default=6)
    p.add_argument("--window-size", type=int, default=11)
    p.add_argument("--checkpoint-dir", type=str, default="experiments/swinir_synthetic_pretrain")
    p.add_argument("--log-every", type=int, default=10)
    p.add_argument("--amp", action="store_true")
    p.add_argument("--skip-pretrain", action="store_true",
                    help="smoke-test convenience: skip straight to fine-tuning on real data (for testing "
                         "the fine-tune loop alone without waiting on the synthetic phase)")
    p.add_argument("--max-rois", type=int, default=None, help="cap real train set size, for smoke tests")
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


def run_epochs(model, loader, val_ds, optimizer, scaler, amp_enabled, device, n_epochs, checkpoint_dir,
                filename_prefix, log_every, start_step=0):
    l1_loss = nn.L1Loss()
    os.makedirs(checkpoint_dir, exist_ok=True)
    step = start_step
    for epoch in range(n_epochs):
        epoch_start = time.time()
        for batch in loader:
            lr = batch["lr"].to(device)
            hr = batch["hr"].to(device)

            optimizer.zero_grad()
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=amp_enabled):
                sr = model(lr)
            sr = sr.float()
            loss = l1_loss(sr, hr)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            if step % log_every == 0:
                print(f"[{filename_prefix}] epoch {epoch} step {step} loss {loss.item():.4f}")
            step += 1

        print(f"[{filename_prefix}] epoch {epoch} done in {time.time() - epoch_start:.1f}s")
        metrics = evaluate(model, val_ds, device)
        print(f"[{filename_prefix}] epoch {epoch} val metrics (real data): {metrics}")

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        ckpt_path = f"{checkpoint_dir}/{filename_prefix}_epoch{epoch}.pt"
        torch.save(model.state_dict(), ckpt_path)
        print(f"saved {ckpt_path}")
    return step


def main():
    args = parse_args()
    depths = tuple(int(d) for d in args.depths.split(","))
    print(f"device: {args.device}  depths: {depths}")

    splits = tile_disjoint_split(ROOT)
    real_train_rois = splits["train"][: args.max_rois] if args.max_rois else splits["train"]
    real_train_ds = SEN2NAIPCrossSensor(real_train_rois)
    real_val_ds = SEN2NAIPCrossSensor(splits["val"])
    print(f"real train pairs: {len(real_train_ds)}  real val pairs: {len(real_val_ds)}")

    model = SwinIR(embed_dim=args.embed_dim, depths=depths, num_heads=args.num_heads,
                    window_size=args.window_size).to(args.device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    amp_enabled = args.amp and args.device == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=amp_enabled)
    if args.amp and not amp_enabled:
        print("--amp requested but no CUDA device -- running in plain fp32 (no-op on CPU)")

    if not args.skip_pretrain:
        synthetic_ds = SyntheticNAIPDataset()
        print(f"synthetic pretrain pairs: {len(synthetic_ds)}")
        synthetic_loader = DataLoader(synthetic_ds, batch_size=min(args.batch_size, len(synthetic_ds)), shuffle=True)

        print(f"\n=== Phase 1: pretraining on synthetic corpus, {args.pretrain_epochs} epochs ===")
        run_epochs(model, synthetic_loader, real_val_ds, optimizer, scaler, amp_enabled, args.device,
                   args.pretrain_epochs, args.checkpoint_dir, "swinir_pretrain", args.log_every)
    else:
        print("--skip-pretrain set -- going straight to fine-tuning")

    print(f"\n=== Phase 2: fine-tuning on real data, {args.finetune_epochs} epochs ===")
    real_train_loader = DataLoader(real_train_ds, batch_size=args.finetune_batch_size, shuffle=True)
    run_epochs(model, real_train_loader, real_val_ds, optimizer, scaler, amp_enabled, args.device,
               args.finetune_epochs, args.checkpoint_dir, "swinir_finetune", args.log_every)


if __name__ == "__main__":
    main()
