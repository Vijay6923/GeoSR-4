"""Downstream task validation v2 (fixes D033's core flaw): does SR actually
help recover real building footprints better than bicubic upsampling?

D033 used SAM's own zero-shot segments as a stand-in for "ground truth" --
comparing the model against itself, which is circular, and gave a noisy,
inconclusive result. This version anchors to a real, independent,
externally-sourced ground truth instead: OpenStreetMap building footprints
(fetch_osm_buildings.py) rasterized onto the same pixel grid.

First cut of this metric (union-of-all-SAM-segments IoU vs the OSM mask,
single Delhi AOI) was *also* inconclusive (bicubic 0.1770 vs SR 0.1768,
practically tied). Two real weaknesses in that first cut, both addressed
here (see decisions.md D047 follow-up):
  1. Single AOI -- one crop is not enough to trust a tied result over.
     This module is written so a caller can run it over several AOIs and
     pool the per-building scores.
  2. The union-mask IoU credits/penalizes every SAM segment equally,
     including roads/trees/shadows that have nothing to do with buildings
     -- diluting whatever real signal exists. This version instead scores
     *each individual OSM building* by its best-matching SAM segment's IoU
     (mean best-per-instance IoU, the standard way instance-segmentation
     quality is judged) -- a much more building-specific test.
"""

import numpy as np
import torch
from segment_anything import SamAutomaticMaskGenerator, sam_model_registry

import sys
sys.path.insert(0, ".")
from ml.models.baseline.bicubic import upsample_bicubic
from ml.datasets.sen2naip import load_norm_stats, _normalize, denormalize

RGB_BANDS = (0, 1, 2)
MIN_MASK_AREA = 30  # px, filters SAM noise specks -- same as D033
MIN_BUILDING_PX = 20  # skip buildings too small to possibly resolve at this GSD, either way


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


def segment_masks(mask_generator, rgb_uint8: np.ndarray) -> list:
    masks = mask_generator.generate(rgb_uint8)
    return [m["segmentation"] for m in masks if m["area"] >= MIN_MASK_AREA]


def per_building_best_iou(sam_masks: list, osm_instances: np.ndarray, min_building_px: int = MIN_BUILDING_PX) -> list:
    """osm_instances: (H,W) int array, 0=background, 1..N=building id.
    Returns one best-IoU score per building (skipping buildings smaller
    than min_building_px) -- the standard "mean best-matching-instance
    IoU" used to judge instance segmentation quality, here reused so
    roads/trees/shadows in sam_masks can't dilute a building-specific
    score the way a flat union-mask IoU would."""
    building_ids = np.unique(osm_instances)
    building_ids = building_ids[building_ids != 0]
    scores = []
    for bid in building_ids:
        b_mask = osm_instances == bid
        if b_mask.sum() < min_building_px:
            continue
        best = 0.0
        for s in sam_masks:
            if not np.any(s & b_mask):
                continue
            inter = np.logical_and(b_mask, s).sum()
            union = np.logical_or(b_mask, s).sum()
            best = max(best, inter / union)
        scores.append(best)
    return scores


def center_crop(arr: np.ndarray, size: int) -> np.ndarray:
    h, w = arr.shape[-2:]
    top = (h - size) // 2
    left = (w - size) // 2
    return arr[..., top:top + size, left:left + size]


def load_sam(checkpoint: str, points_per_side: int = 16) -> SamAutomaticMaskGenerator:
    sam = sam_model_registry["vit_b"](checkpoint=checkpoint)
    return SamAutomaticMaskGenerator(sam, points_per_side=points_per_side, min_mask_region_area=MIN_MASK_AREA)


def evaluate_aoi(lr_path: str, sr_path: str, osm_instances_full: np.ndarray, mask_generator, crop_size: int = 640) -> dict:
    """Runs both bicubic and SR through SAM, scores each against the real
    OSM building instances (per-instance best-IoU). Returns per-building
    score lists for bicubic and SR, plus context (n buildings, segment
    counts) for a single AOI."""
    import rasterio

    with rasterio.open(lr_path) as src:
        lr = src.read().astype(np.float32)
    with rasterio.open(sr_path) as src:
        sr = src.read().astype(np.float32)

    lr_ranges, hr_ranges = load_norm_stats()
    lr_norm = _normalize(lr, lr_ranges)
    bicubic_01 = upsample_bicubic(torch.from_numpy(lr_norm).unsqueeze(0))[0].numpy()
    bicubic = denormalize(bicubic_01, hr_ranges)

    bicubic_c = center_crop(bicubic, crop_size)
    sr_c = center_crop(sr, crop_size)
    osm_c = center_crop(osm_instances_full, crop_size)

    n_buildings = len(np.unique(osm_c)) - (1 if 0 in osm_c else 0)

    stretch_ref = sr_c
    bicubic_rgb = to_rgb_uint8(bicubic_c, stretch_ref)
    sr_rgb = to_rgb_uint8(sr_c, stretch_ref)

    bicubic_sam_masks = segment_masks(mask_generator, bicubic_rgb)
    sr_sam_masks = segment_masks(mask_generator, sr_rgb)

    bicubic_scores = per_building_best_iou(bicubic_sam_masks, osm_c)
    sr_scores = per_building_best_iou(sr_sam_masks, osm_c)

    return {
        "n_buildings_in_crop": n_buildings,
        "n_buildings_scored": len(bicubic_scores),
        "n_bicubic_segments": len(bicubic_sam_masks),
        "n_sr_segments": len(sr_sam_masks),
        "bicubic_scores": bicubic_scores,
        "sr_scores": sr_scores,
    }
