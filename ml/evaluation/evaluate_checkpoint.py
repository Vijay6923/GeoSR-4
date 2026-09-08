"""Evaluates a trained checkpoint on the FULL validation split (279 pairs),
same protocol as run_baseline.py, so the two numbers are directly comparable.
The per-epoch numbers printed during training only sample 50 pairs for
speed -- this is the real number to log in decisions.md."""

import argparse
import sys
import numpy as np
import torch
from torch.utils.data import DataLoader

sys.path.insert(0, ".")
from ml.datasets.sen2naip import SEN2NAIPCrossSensor, tile_disjoint_split
from ml.models.edsr.edsr import EDSR
from ml.models.swinir.swinir import SwinIR
from ml.evaluation.metrics import compute_all_metrics

ROOT = "ml/datasets/raw/sen2naip/cross-sensor/extracted/cross-sensor"


def build_model(args):
    if args.model_type == "edsr":
        return EDSR(n_channels=args.n_channels, n_blocks=args.n_blocks)
    depths = tuple(int(d) for d in args.depths.split(","))
    return SwinIR(embed_dim=args.embed_dim, depths=depths,
                  num_heads=args.num_heads, window_size=args.window_size)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", type=str, required=True)
    p.add_argument("--model-type", type=str, choices=["edsr", "swinir"], default="edsr")
    p.add_argument("--n-blocks", type=int, default=16, help="EDSR only")
    p.add_argument("--n-channels", type=int, default=64, help="EDSR only")
    p.add_argument("--embed-dim", type=int, default=60, help="SwinIR only")
    p.add_argument("--depths", type=str, default="2,2,2,2", help="SwinIR only")
    p.add_argument("--num-heads", type=int, default=6, help="SwinIR only")
    p.add_argument("--window-size", type=int, default=11, help="SwinIR only")
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    args = p.parse_args()

    splits = tile_disjoint_split(ROOT)
    val_ds = SEN2NAIPCrossSensor(splits["val"])
    loader = DataLoader(val_ds, batch_size=1, shuffle=False)

    model = build_model(args).to(args.device)
    model.load_state_dict(torch.load(args.checkpoint, map_location=args.device))
    model.eval()

    results = {"psnr": [], "ssim": [], "sam": [], "ergas": []}
    with torch.no_grad():
        for i, batch in enumerate(loader):
            sr = model(batch["lr"].to(args.device)).clamp(0.0, 1.0)[0].cpu().numpy()
            hr = batch["hr"][0].numpy()
            m = compute_all_metrics(sr, hr)
            for k, v in m.items():
                results[k].append(v)
            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{len(val_ds)} pairs evaluated...")

    print(f"\nModel Performance — {args.checkpoint} (n={len(val_ds)} validation pairs)")
    print(f"PSNR   {np.mean(results['psnr']):.2f} dB  (std {np.std(results['psnr']):.2f})")
    print(f"SSIM   {np.mean(results['ssim']):.4f}  (std {np.std(results['ssim']):.4f})")
    print(f"SAM    {np.mean(results['sam']):.2f}°  (std {np.std(results['sam']):.2f})")
    print(f"ERGAS  {np.mean(results['ergas']):.2f}  (std {np.std(results['ergas']):.2f})")


if __name__ == "__main__":
    main()
