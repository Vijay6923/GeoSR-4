"""Runs a trained model over an arbitrary-size Sentinel-2 GeoTIFF (not just
the dataset's pre-cut 121x121 patches): tile, normalize, infer, blend,
denormalize, write a GeoTIFF with correct upscaled CRS/transform.

PRD section 25-26 (tiled inference, overlapping tiles) and 40-41
(geospatial preservation). Supports EDSR and SwinIR (--model-type), and
the heteroscedastic uncertainty head (--uncertainty, EDSR only -- see
decisions.md D016), which additionally writes an uncertainty GeoTIFF.
"""

import argparse
import sys
import numpy as np
import rasterio
import torch

sys.path.insert(0, ".")
from ml.datasets.sen2naip import load_norm_stats, _normalize, denormalize
from ml.models.edsr.edsr import EDSR
from ml.models.swinir.swinir import SwinIR
from ml.uncertainty.heteroscedastic import split_mean_logvar
from geospatial.tiling.tiler import extract_tiles, blend_tiles
from geospatial.geotiff.export import write_sr_geotiff

SCALE_FACTOR = 4


def build_model(args):
    if args.model_type == "edsr":
        out_channels = 8 if args.uncertainty else 4
        return EDSR(out_channels=out_channels, n_channels=args.n_channels, n_blocks=args.n_blocks)
    if args.uncertainty:
        raise ValueError("uncertainty head is only implemented for EDSR (out_channels=8) -- see decisions.md D016")
    depths = tuple(int(d) for d in args.depths.split(","))
    return SwinIR(embed_dim=args.embed_dim, depths=depths, num_heads=args.num_heads, window_size=args.window_size)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=str, required=True, help="input Sentinel-2 GeoTIFF")
    p.add_argument("--output", type=str, required=True, help="output SR GeoTIFF path")
    p.add_argument("--uncertainty-output", type=str, default=None, help="output uncertainty (std) GeoTIFF path, required if --uncertainty")
    p.add_argument("--checkpoint", type=str, required=True)
    p.add_argument("--model-type", type=str, choices=["edsr", "swinir"], default="edsr")
    p.add_argument("--uncertainty", action="store_true", help="EDSR checkpoint trained with train_edsr_uncertainty.py")
    p.add_argument("--tile-size", type=int, default=121, help="matches training patch size; must be a multiple of --window-size for swinir")
    p.add_argument("--overlap", type=int, default=16)
    p.add_argument("--n-blocks", type=int, default=16, help="edsr only")
    p.add_argument("--n-channels", type=int, default=64, help="edsr only")
    p.add_argument("--embed-dim", type=int, default=60, help="swinir only")
    p.add_argument("--depths", type=str, default="2,2,2,2", help="swinir only")
    p.add_argument("--num-heads", type=int, default=6, help="swinir only")
    p.add_argument("--window-size", type=int, default=11, help="swinir only")
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    args = p.parse_args()

    if args.uncertainty and args.uncertainty_output is None:
        raise ValueError("--uncertainty-output is required when --uncertainty is set")
    if args.model_type == "swinir" and args.tile_size % args.window_size != 0:
        raise ValueError(f"--tile-size ({args.tile_size}) must be a multiple of --window-size ({args.window_size}) for swinir")

    with rasterio.open(args.input) as src:
        scene = src.read().astype(np.float32)
        if src.nodata is not None:
            scene[scene == src.nodata] = 0.0
        src_transform = src.transform
        src_crs = src.crs

    lr_ranges, hr_ranges = load_norm_stats()
    scene_norm = _normalize(scene, lr_ranges)

    tiles, padded_shape, orig_shape = extract_tiles(scene_norm, args.tile_size, args.overlap)
    print(f"scene {scene.shape} -> {len(tiles)} tiles of {args.tile_size}x{args.tile_size} (overlap {args.overlap})")

    model = build_model(args).to(args.device)
    model.load_state_dict(torch.load(args.checkpoint, map_location=args.device))
    model.eval()

    mean_predictions = []
    logvar_predictions = []
    with torch.no_grad():
        for i, (tile, row, col) in enumerate(tiles):
            x = torch.from_numpy(tile).unsqueeze(0).to(args.device)
            out = model(x)
            if args.uncertainty:
                mean, log_var = split_mean_logvar(out)
                mean_predictions.append((mean.clamp(0.0, 1.0)[0].cpu().numpy(), row, col))
                logvar_predictions.append((log_var[0].cpu().numpy(), row, col))
            else:
                mean_predictions.append((out.clamp(0.0, 1.0)[0].cpu().numpy(), row, col))
            if (i + 1) % 20 == 0:
                print(f"  {i + 1}/{len(tiles)} tiles inferred...")

    sr_scene_norm = blend_tiles(mean_predictions, padded_shape, args.tile_size, SCALE_FACTOR, orig_shape)
    sr_scene = denormalize(sr_scene_norm, hr_ranges)
    write_sr_geotiff(args.output, sr_scene, src_transform, src_crs, SCALE_FACTOR)
    print(f"wrote {args.output}  shape={sr_scene.shape}")

    if args.uncertainty:
        logvar_scene = blend_tiles(logvar_predictions, padded_shape, args.tile_size, SCALE_FACTOR, orig_shape)
        std_scene_norm = np.exp(0.5 * logvar_scene)
        # std scales linearly under the same affine denormalization (Var(aX) = a^2 Var(X))
        band_scale = (hr_ranges[:, 1] - hr_ranges[:, 0]).reshape(-1, 1, 1)
        std_scene = std_scene_norm * band_scale
        write_sr_geotiff(args.uncertainty_output, std_scene, src_transform, src_crs, SCALE_FACTOR)
        print(f"wrote {args.uncertainty_output}  shape={std_scene.shape}")


if __name__ == "__main__":
    main()
