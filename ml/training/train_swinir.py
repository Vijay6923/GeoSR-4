"""Trains the SwinIR baseline. Same L1-only, smoke-test-locally /
train-on-Colab workflow as train_edsr.py (decisions.md D010). See D012 for
why window_size=11 and the chosen embed_dim/depths."""

import argparse
import os
import sys
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

sys.path.insert(0, ".")
from ml.datasets.sen2naip import SEN2NAIPCrossSensor, tile_disjoint_split
from ml.models.swinir.swinir import SwinIR
from ml.evaluation.metrics import compute_all_metrics
from ml.losses.spectral import SpectralAngleLoss
from ml.losses.edge import EdgeLoss
from ml.losses.perceptual import VGGPerceptualLoss

ROOT = "ml/datasets/raw/sen2naip/cross-sensor/extracted/cross-sensor"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--max-rois", type=int, default=None, help="cap train set size, for smoke tests")
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--embed-dim", type=int, default=60)
    p.add_argument("--depths", type=str, default="2,2,2,2", help="comma-separated RSTB depths")
    p.add_argument("--num-heads", type=int, default=6)
    p.add_argument("--window-size", type=int, default=11)
    p.add_argument("--checkpoint-dir", type=str, default="experiments/swinir")
    p.add_argument("--log-every", type=int, default=10)
    p.add_argument("--lambda-spectral", type=float, default=0.0, help="PRD section 34-35, 0 = L1 only (baseline)")
    p.add_argument("--lambda-edge", type=float, default=0.0, help="PRD section 37, 0 = L1 only (baseline)")
    p.add_argument("--lambda-perceptual", type=float, default=0.0, help="PRD section 36, VGG perceptual loss -- see decisions.md D023")
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
    depths = tuple(int(d) for d in args.depths.split(","))
    print(f"device: {args.device}  depths: {depths}")

    splits = tile_disjoint_split(ROOT)
    train_rois = splits["train"][: args.max_rois] if args.max_rois else splits["train"]
    train_ds = SEN2NAIPCrossSensor(train_rois)
    val_ds = SEN2NAIPCrossSensor(splits["val"])
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)

    print(f"train pairs: {len(train_ds)}  val pairs: {len(val_ds)}")

    model = SwinIR(
        embed_dim=args.embed_dim, depths=depths,
        num_heads=args.num_heads, window_size=args.window_size,
    ).to(args.device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    l1_loss = nn.L1Loss()
    spectral_loss = SpectralAngleLoss().to(args.device)
    edge_loss = EdgeLoss().to(args.device)
    perceptual_loss = VGGPerceptualLoss().to(args.device) if args.lambda_perceptual > 0 else None

    print(f"loss: L1 + {args.lambda_spectral} * spectral + {args.lambda_edge} * edge + {args.lambda_perceptual} * perceptual")

    os.makedirs(args.checkpoint_dir, exist_ok=True)

    step = 0
    for epoch in range(args.epochs):
        epoch_start = time.time()
        for batch in train_loader:
            lr = batch["lr"].to(args.device)
            hr = batch["hr"].to(args.device)

            sr = model(lr)
            loss = l1_loss(sr, hr)
            if args.lambda_spectral > 0:
                loss = loss + args.lambda_spectral * spectral_loss(sr, hr)
            if args.lambda_edge > 0:
                loss = loss + args.lambda_edge * edge_loss(sr, hr)
            if perceptual_loss is not None:
                loss = loss + args.lambda_perceptual * perceptual_loss(sr, hr)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            if step % args.log_every == 0:
                print(f"epoch {epoch} step {step} loss {loss.item():.4f}")
            step += 1

        print(f"epoch {epoch} done in {time.time() - epoch_start:.1f}s")
        metrics = evaluate(model, val_ds, args.device)
        print(f"epoch {epoch} val metrics: {metrics}")

        if torch.cuda.is_available():
            torch.cuda.empty_cache()  # D025: switching train(batch=16)<->eval(batch=1) fragments the allocator

        ckpt_path = f"{args.checkpoint_dir}/swinir_epoch{epoch}.pt"
        torch.save(model.state_dict(), ckpt_path)
        print(f"saved {ckpt_path}")


if __name__ == "__main__":
    main()
