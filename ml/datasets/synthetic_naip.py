"""PyTorch Dataset for the synthetic NAIP-degradation pretraining corpus
(D048, see generate_synthetic_pairs.py). Mirrors SEN2NAIPCrossSensor's
shape/normalization pattern (D008's percentile-normalization philosophy),
but uses its own stats file since the synthetic pairs are on the
degradation model's harmonized-reflectance scale, not the real dataset's
raw DN scale -- the two are not comparable, only used in separate phases
(pretrain vs fine-tune) of the same model.
"""

import glob
import json
import os
import numpy as np
import rasterio
import torch
from torch.utils.data import Dataset

STATS_PATH = "configs/normalization_stats_synthetic.json"


def load_synthetic_norm_stats():
    with open(STATS_PATH) as f:
        stats = json.load(f)
    return np.array(stats["lr_p2_p98"], dtype=np.float32), np.array(stats["hr_p2_p98"], dtype=np.float32)


def _normalize(arr: np.ndarray, band_ranges: np.ndarray) -> np.ndarray:
    lo = band_ranges[:, 0].reshape(-1, 1, 1)
    hi = band_ranges[:, 1].reshape(-1, 1, 1)
    return np.clip((arr - lo) / (hi - lo), 0.0, 1.0)


class SyntheticNAIPDataset(Dataset):
    def __init__(self, root: str = "ml/datasets/raw/synthetic_naip"):
        self.roi_dirs = sorted(glob.glob(os.path.join(root, "ROI_synth_*")))
        if not self.roi_dirs:
            raise ValueError(f"no synthetic ROIs found under {root} -- run generate_synthetic_pairs.py first")
        self.lr_ranges, self.hr_ranges = load_synthetic_norm_stats()

    def __len__(self):
        return len(self.roi_dirs)

    def __getitem__(self, idx):
        roi_dir = self.roi_dirs[idx]
        with rasterio.open(os.path.join(roi_dir, "lr.tif")) as src:
            lr = src.read().astype(np.float32)
        with rasterio.open(os.path.join(roi_dir, "hr.tif")) as src:
            hr = src.read().astype(np.float32)

        lr = _normalize(lr, self.lr_ranges)
        hr = _normalize(hr, self.hr_ranges)

        return {"lr": torch.from_numpy(lr), "hr": torch.from_numpy(hr), "roi_id": os.path.basename(roi_dir)}
