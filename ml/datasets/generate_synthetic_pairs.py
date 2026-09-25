"""Builds a synthetic pretraining corpus (D048): fetches real HR-only NAIP
tiles from diverse US locations (fetch_naip_hr.py), degrades each into a
synthetic (LR, HR) pair (synthetic_degradation.py), and saves them in the
same on-disk shape as the real SEN2NAIP ROIs so a dedicated
SyntheticNAIPDataset can load them the same way.

Locations are hand-picked across many US states/land-cover types
(urban, suburban, agricultural, mixed) for diversity -- NAIP has no
metadata that groups tiles the way Sentinel-2's MGRS tiles do, so there's
no tile-disjoint-split equivalent to worry about here; this corpus is used
for pretraining only, evaluation always stays on the real SEN2NAIP val
split.
"""

import argparse
import json
import os
import sys
import numpy as np
import rasterio
import torch

sys.path.insert(0, ".")
from geospatial.preprocessing.fetch_naip_hr import fetch_naip_hr
from ml.datasets.synthetic_degradation import degrade_hr_to_pair

OUT_ROOT = "ml/datasets/raw/synthetic_naip"

# (lon, lat) -- spread across CONUS states/land-cover types for diversity.
# Deliberately avoids the SEN2NAIP cross-sensor locations (different exact
# coordinates), so this is genuinely additional HR coverage, not a
# duplicate of tiles we already have real LR for.
LOCATIONS = [
    (-119.20, 36.30),  # CA Central Valley, urban+ag mix (verified visually, D048)
    (-96.80, 32.90),   # Dallas TX suburb
    (-93.60, 41.60),   # Des Moines IA, agriculture
    (-84.40, 33.75),   # Atlanta GA suburb
    (-122.30, 47.60),  # Seattle WA urban
    (-104.99, 39.74),  # Denver CO urban
    (-80.84, 35.23),   # Charlotte NC suburb
    (-97.74, 30.27),   # Austin TX urban
    (-86.16, 39.77),   # Indianapolis IN
    (-81.38, 28.54),   # Orlando FL
    (-95.36, 29.76),   # Houston TX
    (-112.07, 33.45),  # Phoenix AZ
    (-90.20, 38.63),   # St Louis MO
    (-77.04, 38.91),   # Washington DC suburb
    (-121.49, 38.58),  # Sacramento CA
    (-83.05, 42.33),   # Detroit MI
    (-71.06, 42.36),   # Boston MA
    (-117.16, 32.72),  # San Diego CA
    (-95.94, 41.26),   # Omaha NE
    (-78.64, 35.78),   # Raleigh NC
]


def generate_one(idx: int, lon: float, lat: float) -> bool:
    roi_dir = os.path.join(OUT_ROOT, f"ROI_synth_{idx:04d}")
    os.makedirs(roi_dir, exist_ok=True)
    hr_raw_path = os.path.join(roi_dir, "_hr_raw_naip.tif")

    try:
        fetch_naip_hr(lon, lat, hr_raw_path)
    except Exception as e:
        print(f"  ROI_synth_{idx:04d} SKIPPED (NAIP fetch failed): {e}")
        return False

    with rasterio.open(hr_raw_path) as src:
        hr_raw = src.read().astype(np.float32)
        crs = src.crs
        hr_transform = src.transform

    lr_synth, hr_harmonized = degrade_hr_to_pair(torch.from_numpy(hr_raw))
    lr_synth = lr_synth.numpy()
    hr_harmonized = hr_harmonized.numpy()

    # lr grid = hr grid scaled 4x (same footprint, 1/4 the pixels each side)
    lr_transform = hr_transform * hr_transform.scale(4, 4)

    with rasterio.open(
        os.path.join(roi_dir, "lr.tif"), "w", driver="GTiff",
        height=lr_synth.shape[1], width=lr_synth.shape[2], count=4,
        dtype="float32", crs=crs, transform=lr_transform,
    ) as dst:
        dst.write(lr_synth)

    with rasterio.open(
        os.path.join(roi_dir, "hr.tif"), "w", driver="GTiff",
        height=hr_harmonized.shape[1], width=hr_harmonized.shape[2], count=4,
        dtype="float32", crs=crs, transform=hr_transform,
    ) as dst:
        dst.write(hr_harmonized)

    os.remove(hr_raw_path)
    print(f"  ROI_synth_{idx:04d} OK  ({lon}, {lat})")
    return True


def compute_and_save_stats():
    """Same percentile-normalization philosophy as the real dataset (D008)
    -- computed fresh from this synthetic corpus's own pixel distribution,
    since it's on a different scale (harmonized-reflectance) than the real
    dataset's raw DN scale."""
    roi_dirs = sorted(
        d for d in os.listdir(OUT_ROOT) if d.startswith("ROI_synth_") and os.path.isdir(os.path.join(OUT_ROOT, d))
    )
    lr_pixels = [[] for _ in range(4)]
    hr_pixels = [[] for _ in range(4)]
    for roi in roi_dirs:
        with rasterio.open(os.path.join(OUT_ROOT, roi, "lr.tif")) as src:
            lr = src.read()
        with rasterio.open(os.path.join(OUT_ROOT, roi, "hr.tif")) as src:
            hr = src.read()
        for b in range(4):
            lr_pixels[b].append(lr[b].flatten())
            hr_pixels[b].append(hr[b].flatten())

    lr_ranges = [list(np.percentile(np.concatenate(lr_pixels[b]), [2, 98])) for b in range(4)]
    hr_ranges = [list(np.percentile(np.concatenate(hr_pixels[b]), [2, 98])) for b in range(4)]

    stats = {"lr_p2_p98": lr_ranges, "hr_p2_p98": hr_ranges, "n_rois": len(roi_dirs)}
    stats_path = "configs/normalization_stats_synthetic.json"
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"wrote {stats_path} (from {len(roi_dirs)} synthetic ROIs)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=len(LOCATIONS), help="how many locations to fetch (from the curated list)")
    args = p.parse_args()

    os.makedirs(OUT_ROOT, exist_ok=True)
    ok = 0
    for i, (lon, lat) in enumerate(LOCATIONS[: args.n]):
        if generate_one(i, lon, lat):
            ok += 1
    print(f"\n{ok}/{args.n} synthetic pairs generated successfully")

    if ok > 0:
        compute_and_save_stats()


if __name__ == "__main__":
    main()
