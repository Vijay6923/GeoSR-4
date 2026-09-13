"""Confidence-weighted fusion of EDSR-uncertainty and SwinIR outputs.

Where EDSR's own predicted uncertainty is low (confident), trust EDSR's
mean prediction more. Where EDSR is unsure, fall back toward SwinIR
(D020/D029: generally the sharper, better-performing model). Both models
already run through run_sr_inference() and land in the same physical
HR-domain scale after denormalize(), so they're directly blendable
per-pixel without any extra rescaling.

Pure inference-time logic -- no training, reuses both existing checkpoints.
"""

import argparse
import sys
import numpy as np
import rasterio
import torch

sys.path.insert(0, ".")
from ml.datasets.sen2naip import load_norm_stats
from ml.inference.infer_scene import build_model, run_sr_inference, SCALE_FACTOR
from geospatial.geotiff.export import write_sr_geotiff

EDSR_CHECKPOINT = "experiments/edsr_uncertainty/edsr_unc_epoch19.pt"
SWINIR_CHECKPOINT = "experiments/swinir_quality/swinir_epoch29.pt"


def confidence_weighted_fuse(edsr_mean: np.ndarray, edsr_std: np.ndarray, swinir_out: np.ndarray) -> tuple:
    """All three: (C,H,W), same physical scale. Returns (fused, edsr_weight_map)."""
    std_per_pixel = edsr_std.mean(axis=0)  # (H,W), averaged across bands
    lo, hi = np.percentile(std_per_pixel, [2, 98])
    normalized_std = np.clip((std_per_pixel - lo) / (hi - lo + 1e-8), 0.0, 1.0)
    edsr_weight = 1.0 - normalized_std  # confident (low std) -> trust EDSR more

    edsr_weight_3ch = edsr_weight[None, :, :]  # broadcast across bands
    fused = edsr_weight_3ch * edsr_mean + (1 - edsr_weight_3ch) * swinir_out
    return fused, edsr_weight


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=str, required=True)
    p.add_argument("--output", type=str, required=True)
    p.add_argument("--weight-map-output", type=str, default=None, help="optional: save the EDSR-weight map for inspection")
    p.add_argument("--tile-size", type=int, default=121)
    p.add_argument("--overlap", type=int, default=16)
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    args = p.parse_args()

    with rasterio.open(args.input) as src:
        scene = src.read().astype(np.float32)
        if src.nodata is not None:
            scene[scene == src.nodata] = 0.0
        src_transform = src.transform
        src_crs = src.crs

    lr_ranges, hr_ranges = load_norm_stats()

    edsr = build_model("edsr", uncertainty=True, n_blocks=16, n_channels=64).to(args.device)
    edsr.load_state_dict(torch.load(EDSR_CHECKPOINT, map_location=args.device))

    swinir = build_model("swinir", embed_dim=60, depths="2,2,2,2", num_heads=6, window_size=11).to(args.device)
    swinir.load_state_dict(torch.load(SWINIR_CHECKPOINT, map_location=args.device))

    edsr_mean, edsr_std = run_sr_inference(edsr, scene, args.tile_size, args.overlap, args.device, lr_ranges, hr_ranges, uncertainty=True)
    swinir_out, _ = run_sr_inference(swinir, scene, args.tile_size, args.overlap, args.device, lr_ranges, hr_ranges, uncertainty=False)

    fused, weight_map = confidence_weighted_fuse(edsr_mean, edsr_std, swinir_out)

    write_sr_geotiff(args.output, fused, src_transform, src_crs, SCALE_FACTOR)
    print(f"wrote {args.output}  shape={fused.shape}")
    print(f"EDSR weight: mean={weight_map.mean():.3f} (0=all SwinIR, 1=all EDSR)")

    if args.weight_map_output:
        np.save(args.weight_map_output, weight_map)
        print(f"saved weight map to {args.weight_map_output}")


if __name__ == "__main__":
    main()
