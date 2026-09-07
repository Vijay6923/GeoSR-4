"""Computes per-band 2nd/98th percentile stats from a sample of the TRAIN
split only (never val/test, to avoid leakage), for LR and HR independently.
Fixed /10000 and /255 divisors don't put LR and HR on a comparable scale --
see decisions.md D008. Output feeds sen2naip.py's normalization."""

import json
import sys
import numpy as np
import rasterio

sys.path.insert(0, ".")
from ml.datasets.sen2naip import tile_disjoint_split

ROOT = "ml/datasets/raw/sen2naip/cross-sensor/extracted/cross-sensor"
SAMPLE_SIZE = 300
PERCENTILES = (2, 98)


def band_percentiles(roi_dirs, filename, nodata_aware):
    samples = [[] for _ in range(4)]
    for roi_dir in roi_dirs:
        with rasterio.open(f"{roi_dir}/{filename}") as src:
            arr = src.read().astype(np.float32)
            if nodata_aware and src.nodata is not None:
                arr[arr == src.nodata] = np.nan
        for b in range(4):
            band = arr[b]
            valid = band[~np.isnan(band)] if nodata_aware else band.flatten()
            samples[b].append(valid)
    return [np.percentile(np.concatenate(s), PERCENTILES).tolist() for s in samples]


def main():
    splits = tile_disjoint_split(ROOT)
    rng = np.random.default_rng(42)
    train_rois = list(rng.choice(splits["train"], size=min(SAMPLE_SIZE, len(splits["train"])), replace=False))

    print(f"Computing stats from {len(train_rois)} training ROIs...")
    lr_stats = band_percentiles(train_rois, "lr.tif", nodata_aware=True)
    hr_stats = band_percentiles(train_rois, "hr.tif", nodata_aware=False)

    stats = {"lr_p2_p98": lr_stats, "hr_p2_p98": hr_stats, "n_rois_sampled": len(train_rois)}
    with open("configs/normalization_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
