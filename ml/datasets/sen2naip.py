"""PyTorch Dataset for the SEN2NAIP cross-sensor split (real Sentinel-2 <-> NAIP
pairs). See decisions.md D002/D003/D006 for why this split and this
normalization/splitting strategy were chosen.

Each ROI_* folder contains:
  lr.tif        4 x 121 x 121, int32, Sentinel-2 reflectance scale (~0-10000), 10m
  hr.tif        4 x 484 x 484, uint8, NAIP RGB+NIR (0-255), 2.5m
  metadata.json acquisition dates, S2 scene id (contains the MGRS tile), QA scores
"""

import glob
import json
import os
import re
import numpy as np
import rasterio
import torch
from torch.utils.data import Dataset

LR_REFLECTANCE_MAX = 10000.0
HR_PIXEL_MAX = 255.0
TILE_RE = re.compile(r"_T(\d\d[A-Z]{3})_")


def _tile_id(metadata: dict) -> str:
    m = TILE_RE.search(metadata["s2_id"])
    return m.group(1) if m else "UNKNOWN"


def tile_disjoint_split(root: str, val_frac=0.1, test_frac=0.1, seed=42):
    """Groups ROIs by S2 MGRS tile, then assigns whole tiles to train/val/test
    so no two patches from the same tile land in different splits."""
    roi_dirs = sorted(glob.glob(os.path.join(root, "ROI_*")))
    tile_to_rois = {}
    for roi_dir in roi_dirs:
        meta_path = os.path.join(roi_dir, "metadata.json")
        if not os.path.exists(meta_path):
            continue
        with open(meta_path) as f:
            meta = json.load(f)
        tile_to_rois.setdefault(_tile_id(meta), []).append(roi_dir)

    tiles = sorted(tile_to_rois.keys())
    rng = np.random.default_rng(seed)
    rng.shuffle(tiles)

    n_val = max(1, int(len(tiles) * val_frac))
    n_test = max(1, int(len(tiles) * test_frac))
    val_tiles = set(tiles[:n_val])
    test_tiles = set(tiles[n_val:n_val + n_test])
    train_tiles = set(tiles[n_val + n_test:])

    def flatten(tile_set):
        rois = []
        for t in tile_set:
            rois.extend(tile_to_rois[t])
        return sorted(rois)

    return {
        "train": flatten(train_tiles),
        "val": flatten(val_tiles),
        "test": flatten(test_tiles),
    }


class SEN2NAIPCrossSensor(Dataset):
    def __init__(self, roi_dirs: list[str]):
        self.roi_dirs = roi_dirs

    def __len__(self):
        return len(self.roi_dirs)

    def __getitem__(self, idx):
        roi_dir = self.roi_dirs[idx]

        with rasterio.open(os.path.join(roi_dir, "lr.tif")) as src:
            lr = src.read().astype(np.float32)
            lr[lr == src.nodata] = 0.0

        with rasterio.open(os.path.join(roi_dir, "hr.tif")) as src:
            hr = src.read().astype(np.float32)

        lr = np.clip(lr / LR_REFLECTANCE_MAX, 0.0, 1.0)
        hr = np.clip(hr / HR_PIXEL_MAX, 0.0, 1.0)

        with open(os.path.join(roi_dir, "metadata.json")) as f:
            meta = json.load(f)

        return {
            "lr": torch.from_numpy(lr),
            "hr": torch.from_numpy(hr),
            "roi_id": meta["roi_id"],
            "tile_id": _tile_id(meta),
        }
