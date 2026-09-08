"""Quick local demo visualization: LR input vs SR output vs ground-truth HR,
side by side. Not part of the production pipeline -- just for showing the
result on a local machine before the web dashboard (Phase 10) exists."""

import argparse
import sys
import numpy as np
import rasterio
import matplotlib.pyplot as plt

sys.path.insert(0, ".")

RGB_BANDS = (0, 1, 2)  # R, G, B out of the 4-band R,G,B,NIR order (see decisions.md D006)


def to_rgb_display(arr: np.ndarray) -> np.ndarray:
    """arr: (C,H,W) in any positive range -> (H,W,3) uint8 for display, per-band 2-98 percentile stretch."""
    rgb = arr[list(RGB_BANDS)]
    out = np.zeros((rgb.shape[1], rgb.shape[2], 3), dtype=np.uint8)
    for i in range(3):
        band = rgb[i]
        lo, hi = np.percentile(band, [2, 98])
        stretched = np.clip((band - lo) / (hi - lo + 1e-8), 0, 1)
        out[:, :, i] = (stretched * 255).astype(np.uint8)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lr", type=str, required=True)
    p.add_argument("--sr", type=str, required=True)
    p.add_argument("--hr", type=str, default=None, help="ground truth, if available")
    p.add_argument("--output", type=str, default="demo_comparison.png")
    args = p.parse_args()

    with rasterio.open(args.lr) as src:
        lr = src.read().astype(np.float32)
    with rasterio.open(args.sr) as src:
        sr = src.read().astype(np.float32)

    panels = [("Input: Sentinel-2 (10m)", to_rgb_display(lr)), ("GeoSR-4 Output (2.5m)", to_rgb_display(sr))]

    if args.hr:
        with rasterio.open(args.hr) as src:
            hr = src.read().astype(np.float32)
        panels.append(("Ground Truth NAIP (2.5m)", to_rgb_display(hr)))

    fig, axes = plt.subplots(1, len(panels), figsize=(6 * len(panels), 6))
    if len(panels) == 1:
        axes = [axes]
    for ax, (title, img) in zip(axes, panels):
        ax.imshow(img)
        ax.set_title(title)
        ax.axis("off")

    plt.tight_layout()
    plt.savefig(args.output, dpi=150)
    print(f"saved {args.output}")


if __name__ == "__main__":
    main()
