"""Runs the bicubic baseline over the full validation split and reports real
PSNR/SSIM/SAM/ERGAS numbers. PRD section 14: never put fabricated numbers in
the final project — this script is how we get real ones."""

import sys
import numpy as np
from torch.utils.data import DataLoader

sys.path.insert(0, ".")
from ml.datasets.sen2naip import SEN2NAIPCrossSensor, tile_disjoint_split
from ml.models.baseline.bicubic import upsample_bicubic
from ml.evaluation.metrics import compute_all_metrics

ROOT = "ml/datasets/raw/sen2naip/cross-sensor/extracted/cross-sensor"


def main():
    splits = tile_disjoint_split(ROOT)
    val_ds = SEN2NAIPCrossSensor(splits["val"])
    loader = DataLoader(val_ds, batch_size=1, shuffle=False)

    results = {"psnr": [], "ssim": [], "sam": [], "ergas": []}
    for i, batch in enumerate(loader):
        sr = upsample_bicubic(batch["lr"])
        pred = sr[0].numpy()
        target = batch["hr"][0].numpy()
        m = compute_all_metrics(pred, target)
        for k, v in m.items():
            results[k].append(v)
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(val_ds)} pairs evaluated...")

    print(f"\nModel Performance — Bicubic baseline (n={len(val_ds)} validation pairs)")
    print(f"PSNR   {np.mean(results['psnr']):.2f} dB  (std {np.std(results['psnr']):.2f})")
    print(f"SSIM   {np.mean(results['ssim']):.4f}  (std {np.std(results['ssim']):.4f})")
    print(f"SAM    {np.mean(results['sam']):.2f}°  (std {np.std(results['sam']):.2f})")
    print(f"ERGAS  {np.mean(results['ergas']):.2f}  (std {np.std(results['ergas']):.2f})")


if __name__ == "__main__":
    main()
