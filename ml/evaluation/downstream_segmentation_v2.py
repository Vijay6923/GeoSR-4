"""Downstream task validation v2 (fixes D033's core flaw): does SR actually
help recover real building footprints better than bicubic upsampling?

D033 used SAM's own zero-shot segments as a stand-in for "ground truth" --
comparing the model against itself, which is circular, and gave a noisy,
inconclusive result (bicubic scored a higher raw segment count than SR,
opposite of the hypothesis). This version anchors to a real, independent,
externally-sourced ground truth instead: OpenStreetMap building footprints
(fetch_osm_buildings.py) rasterized onto the same pixel grid.

Metric: run SAM's automatic mask generator on bicubic-upsampled input and
on the SR output separately, take the union of all detected segment
boundaries (regardless of what SAM thinks each segment *is* -- no
building/not-building classification, which would add another judgment
call), and compute IoU of that union mask against the real OSM building
mask. If SR helps, real building footprints should fall inside SAM's
detected object boundaries more often than with blurry bicubic input.
See decisions.md D047.
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
MIN_MASK_AREA = 30  # px, filters SAM noise specks -- same as D033


def to_rgb_uint8(arr: np.ndarray, stretch_ref: np.ndarray = None) -> np.ndarray:
    ref = stretch_ref if stretch_ref is not None else arr
    rgb = arr[list(RGB_BANDS)]
    ref_rgb = ref[list(RGB_BANDS)]
    out = np.zeros((rgb.shape[1], rgb.shape[2], 3), dtype=np.uint8)
    for i in range(3):
        lo, hi = np.percentile(ref_rgb[i], [2, 98])
        stretched = np.clip((rgb[i] - lo) / (hi - lo + 1e-8), 0, 1)
        out[:, :, i] = (stretched * 255).astype(np.uint8)
    return out


def segment_union_mask(mask_generator, rgb_uint8: np.ndarray) -> tuple:
    masks = mask_generator.generate(rgb_uint8)
    masks = [m for m in masks if m["area"] >= MIN_MASK_AREA]
    union = np.zeros(rgb_uint8.shape[:2], dtype=bool)
    for m in masks:
        union |= m["segmentation"]
    return union, len(masks)


def iou(pred: np.ndarray, gt: np.ndarray) -> float:
    intersection = np.logical_and(pred, gt).sum()
    union = np.logical_or(pred, gt).sum()
    return float(intersection) / float(union) if union > 0 else 0.0


def center_crop(arr: np.ndarray, size: int) -> np.ndarray:
    """arr: (...,H,W). Crops the center size x size region -- keeps SAM
    runtime tractable on CPU for the full-scene Delhi AOI (1600x1600),
    while still testing on real dense urban content."""
    h, w = arr.shape[-2:]
    top = (h - size) // 2
    left = (w - size) // 2
    return arr[..., top:top + size, left:left + size]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lr", type=str, required=True)
    p.add_argument("--sr", type=str, required=True)
    p.add_argument("--osm-mask", type=str, required=True, help="from fetch_osm_buildings.py, same grid as --sr")
    p.add_argument("--sam-checkpoint", type=str, default="ml/models/sam/sam_vit_b_01ec64.pth")
    p.add_argument("--points-per-side", type=int, default=16)
    p.add_argument("--crop-size", type=int, default=640, help="center-crop size on the SR/OSM grid, for CPU runtime")
    args = p.parse_args()

    with rasterio.open(args.lr) as src:
        lr = src.read().astype(np.float32)
    with rasterio.open(args.sr) as src:
        sr = src.read().astype(np.float32)
    with rasterio.open(args.osm_mask) as src:
        osm_mask_full = src.read(1).astype(bool)

    scale = sr.shape[1] // lr.shape[1]
    print(f"LR shape {lr.shape}, SR shape {sr.shape}, scale {scale}x")

    lr_ranges, hr_ranges = load_norm_stats()
    lr_norm = _normalize(lr, lr_ranges)
    bicubic_01 = upsample_bicubic(torch.from_numpy(lr_norm).unsqueeze(0))[0].numpy()
    bicubic = denormalize(bicubic_01, hr_ranges)

    # crop all three (bicubic, sr, osm mask) to the same center region
    bicubic_c = center_crop(bicubic, args.crop_size)
    sr_c = center_crop(sr, args.crop_size)
    osm_mask = center_crop(osm_mask_full, args.crop_size)
    print(f"cropped to {args.crop_size}x{args.crop_size} -- OSM building coverage in crop: {osm_mask.mean() * 100:.2f}%")

    stretch_ref = sr_c
    bicubic_rgb = to_rgb_uint8(bicubic_c, stretch_ref)
    sr_rgb = to_rgb_uint8(sr_c, stretch_ref)

    print("loading SAM (ViT-B)...")
    sam = sam_model_registry["vit_b"](checkpoint=args.sam_checkpoint)
    mask_generator = SamAutomaticMaskGenerator(sam, points_per_side=args.points_per_side, min_mask_region_area=MIN_MASK_AREA)

    print("segmenting bicubic-upsampled input...")
    bicubic_union, n_bicubic = segment_union_mask(mask_generator, bicubic_rgb)
    print("segmenting SR output...")
    sr_union, n_sr = segment_union_mask(mask_generator, sr_rgb)

    bicubic_iou = iou(bicubic_union, osm_mask)
    sr_iou = iou(sr_union, osm_mask)

    print(f"\nSegments found (min area {MIN_MASK_AREA}px):")
    print(f"  Bicubic-upsampled input: {n_bicubic}")
    print(f"  GeoSR-4 output:          {n_sr}")
    print(f"\nIoU vs real OSM building footprints (ground truth, n={int(osm_mask.sum())} px):")
    print(f"  Bicubic-upsampled input: {bicubic_iou:.4f}")
    print(f"  GeoSR-4 output:          {sr_iou:.4f}")

    np.savez(
        "/tmp/downstream_v2_masks.npz",
        bicubic_rgb=bicubic_rgb, sr_rgb=sr_rgb, osm_mask=osm_mask,
        bicubic_union=bicubic_union, sr_union=sr_union,
    )
    print("saved masks/images to /tmp/downstream_v2_masks.npz for visualization")


if __name__ == "__main__":
    main()
