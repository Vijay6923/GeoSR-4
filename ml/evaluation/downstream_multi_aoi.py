"""D047 follow-up: runs the per-building best-IoU downstream metric
(downstream_segmentation_v2.py) across several real Indian urban AOIs and
pools the results, instead of trusting a single 640x640 Delhi crop. See
decisions.md D047 for why both the multi-AOI averaging and the
per-building (not flat-union) metric were needed.
"""

import argparse
import sys
import numpy as np

sys.path.insert(0, ".")
from geospatial.preprocessing.fetch_osm_buildings import fetch_and_rasterize
from ml.evaluation.downstream_segmentation_v2 import evaluate_aoi, load_sam

# (name, LR GeoTIFF, SR GeoTIFF) -- SR already generated via infer_scene.py
# against experiments/swinir_quality/swinir_epoch29.pt, same as D030/D047
AOIS = [
    ("connaught_place_delhi", "experiments/india_aoi/delhi_connaught_place.tif", "experiments/india_aoi/delhi_sr_output.tif"),
    ("bandra_mumbai", "experiments/india_aoi/bandra_mumbai.tif", "experiments/india_aoi/bandra_mumbai_sr_output.tif"),
    ("koramangala_bangalore", "experiments/india_aoi/koramangala_bangalore.tif", "experiments/india_aoi/koramangala_bangalore_sr_output.tif"),
    ("anna_nagar_chennai", "experiments/india_aoi/anna_nagar_chennai.tif", "experiments/india_aoi/anna_nagar_chennai_sr_output.tif"),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sam-checkpoint", type=str, default="ml/models/sam/sam_vit_b_01ec64.pth")
    p.add_argument("--crop-size", type=int, default=640)
    args = p.parse_args()

    print("loading SAM (ViT-B)...")
    mask_generator = load_sam(args.sam_checkpoint)

    all_bicubic, all_sr = [], []
    per_aoi_results = []

    for name, lr_path, sr_path in AOIS:
        print(f"\n=== {name} ===")
        try:
            osm_instances, _, n_found = fetch_and_rasterize(sr_path, instances=True)
        except Exception as e:
            print(f"  SKIPPED (OSM fetch failed): {e}")
            continue
        print(f"  {n_found} OSM building footprints found")

        result = evaluate_aoi(lr_path, sr_path, osm_instances, mask_generator, crop_size=args.crop_size)
        print(f"  buildings in crop: {result['n_buildings_in_crop']}, scored (area>=20px): {result['n_buildings_scored']}")
        print(f"  SAM segments -- bicubic: {result['n_bicubic_segments']}, SR: {result['n_sr_segments']}")
        if result["bicubic_scores"]:
            print(f"  mean best-IoU -- bicubic: {np.mean(result['bicubic_scores']):.4f}, SR: {np.mean(result['sr_scores']):.4f}")
        else:
            print("  no buildings large enough to score in this crop")

        all_bicubic.extend(result["bicubic_scores"])
        all_sr.extend(result["sr_scores"])
        per_aoi_results.append((name, result))

    print("\n" + "=" * 60)
    print(f"POOLED across {len(per_aoi_results)} AOIs, n={len(all_bicubic)} buildings total:")
    if all_bicubic:
        print(f"  Bicubic-upsampled mean best-IoU: {np.mean(all_bicubic):.4f}  (std {np.std(all_bicubic):.4f})")
        print(f"  GeoSR-4 output mean best-IoU:    {np.mean(all_sr):.4f}  (std {np.std(all_sr):.4f})")
    else:
        print("  no buildings scored across any AOI")


if __name__ == "__main__":
    main()
