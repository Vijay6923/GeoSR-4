"""Phase 8 downstream task validation (PRD section 51-52): does SR actually
help identify more real structures, not just look sharper? Uses Meta's
Segment Anything Model (SAM, ViT-B) in zero-shot automatic mask generation
mode -- no labeled building/road data needed, since none exists for this
dataset. Counts distinct segments SAM finds in bicubic-upsampled input vs
our SR output vs (where available) real ground truth, as a proxy for "how
many separable real-world objects can an analyst/algorithm actually pick
out of this image."
"""

import argparse
import sys
import numpy as np
import rasterio
import torch
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator

sys.path.insert(0, ".")
from ml.models.baseline.bicubic import upsample_bicubic
from ml.datasets.sen2naip import load_norm_stats, _normalize, denormalize

RGB_BANDS = (0, 1, 2)
MIN_MASK_AREA = 30  # px, filters SAM noise specks -- tuned for our 484x484-scale crops


def to_rgb_uint8(arr: np.ndarray, stretch_ref: np.ndarray = None) -> np.ndarray:
    """arr, stretch_ref: (C,H,W). Computes the 2-98 percentile stretch from
    stretch_ref (or arr itself if not given) so multiple images can share
    the same contrast basis for a fair segment-count comparison."""
    ref = stretch_ref if stretch_ref is not None else arr
    rgb = arr[list(RGB_BANDS)]
    ref_rgb = ref[list(RGB_BANDS)]
    out = np.zeros((rgb.shape[1], rgb.shape[2], 3), dtype=np.uint8)
    for i in range(3):
        lo, hi = np.percentile(ref_rgb[i], [2, 98])
        stretched = np.clip((rgb[i] - lo) / (hi - lo + 1e-8), 0, 1)
        out[:, :, i] = (stretched * 255).astype(np.uint8)
    return out


def count_segments(mask_generator, rgb_uint8: np.ndarray):
    masks = mask_generator.generate(rgb_uint8)
    masks = [m for m in masks if m["area"] >= MIN_MASK_AREA]
    return masks


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lr", type=str, required=True)
    p.add_argument("--sr", type=str, required=True)
    p.add_argument("--hr", type=str, default=None, help="ground truth, if available")
    p.add_argument("--sam-checkpoint", type=str, default="ml/models/sam/sam_vit_b_01ec64.pth")
    p.add_argument("--points-per-side", type=int, default=16, help="lower = faster on CPU, fewer candidate segments")
    args = p.parse_args()

    with rasterio.open(args.lr) as src:
        lr = src.read().astype(np.float32)
    with rasterio.open(args.sr) as src:
        sr = src.read().astype(np.float32)

    # upsample_bicubic expects [0,1]-normalized input (D008) and returns
    # [0,1]-clamped output -- normalize first, then denormalize back to the
    # same physical HR-domain scale as sr/hr so all three share one scale
    # for a valid percentile-stretch comparison. Skipping this silently
    # produces a uniform-color image (raw reflectance values all clamped
    # to 1.0) -- caught by inspecting the actual rendered image, not just
    # trusting the segment count.
    lr_ranges, hr_ranges = load_norm_stats()
    lr_norm = _normalize(lr, lr_ranges)
    lr_upsampled_01 = upsample_bicubic(torch.from_numpy(lr_norm).unsqueeze(0))[0].numpy()
    lr_upsampled = denormalize(lr_upsampled_01, hr_ranges)

    hr = None
    if args.hr:
        with rasterio.open(args.hr) as src:
            hr = src.read().astype(np.float32)

    stretch_ref = hr if hr is not None else sr  # shared contrast basis across all three
    lr_rgb = to_rgb_uint8(lr_upsampled, stretch_ref)
    sr_rgb = to_rgb_uint8(sr, stretch_ref)

    print("loading SAM (ViT-B)...")
    sam = sam_model_registry["vit_b"](checkpoint=args.sam_checkpoint)
    mask_generator = SamAutomaticMaskGenerator(
        sam, points_per_side=args.points_per_side, min_mask_region_area=MIN_MASK_AREA)

    print("segmenting bicubic-upsampled input...")
    lr_masks = count_segments(mask_generator, lr_rgb)
    print("segmenting SR output...")
    sr_masks = count_segments(mask_generator, sr_rgb)

    print(f"\nDistinct segments found (min area {MIN_MASK_AREA}px):")
    print(f"  Bicubic-upsampled input: {len(lr_masks)}")
    print(f"  GeoSR-4 output:          {len(sr_masks)}")

    if hr is not None:
        hr_rgb = to_rgb_uint8(hr, stretch_ref)
        print("segmenting ground truth...")
        hr_masks = count_segments(mask_generator, hr_rgb)
        print(f"  Ground truth (ceiling): {len(hr_masks)}")

    np.savez("/tmp/downstream_masks.npz",
             lr_rgb=lr_rgb, sr_rgb=sr_rgb,
             hr_rgb=hr_rgb if hr is not None else np.array([]),
             lr_masks=np.array([m["segmentation"] for m in lr_masks]),
             sr_masks=np.array([m["segmentation"] for m in sr_masks]),
             hr_masks=np.array([m["segmentation"] for m in hr_masks]) if hr is not None else np.array([]))
    print("saved masks/images to /tmp/downstream_masks.npz for visualization")


if __name__ == "__main__":
    main()
