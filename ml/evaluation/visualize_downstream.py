"""Visualizes the mask counts from downstream_segmentation.py -- reads
/tmp/downstream_masks.npz and renders each image with its SAM segment
boundaries overlaid, so the segment-count numbers can be sanity-checked
visually rather than trusted as bare numbers."""

import numpy as np
import matplotlib.pyplot as plt


def overlay_masks(ax, rgb, masks, title):
    ax.imshow(rgb)
    rng = np.random.default_rng(0)
    for m in masks:
        color = rng.random(3)
        overlay = np.zeros((*m.shape, 4))
        overlay[m] = [*color, 0.45]
        ax.imshow(overlay)
        contour_color = tuple(color)
        ax.contour(m.astype(float), levels=[0.5], colors=[contour_color], linewidths=1.2)
    ax.set_title(f"{title} ({len(masks)} segments)", fontsize=11)
    ax.axis("off")


def main():
    data = np.load("/tmp/downstream_masks.npz", allow_pickle=True)
    has_hr = data["hr_rgb"].size > 0

    n = 3 if has_hr else 2
    fig, axes = plt.subplots(1, n, figsize=(7 * n, 7))

    overlay_masks(axes[0], data["lr_rgb"], data["lr_masks"], "Bicubic-upsampled input")
    overlay_masks(axes[1], data["sr_rgb"], data["sr_masks"], "GeoSR-4 output")
    if has_hr:
        overlay_masks(axes[2], data["hr_rgb"], data["hr_masks"], "Ground truth (ceiling)")

    plt.tight_layout()
    plt.savefig("/tmp/downstream_comparison.png", dpi=130)
    print("saved /tmp/downstream_comparison.png")


if __name__ == "__main__":
    main()
