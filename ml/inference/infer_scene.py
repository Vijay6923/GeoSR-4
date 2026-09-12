"""Runs a trained model over an arbitrary-size Sentinel-2 scene (not just
the dataset's pre-cut 121x121 patches): tile, normalize, infer, blend,
denormalize. PRD section 25-26 (tiled inference, overlapping tiles) and
40-41 (geospatial preservation). Supports EDSR and SwinIR (--model-type),
and the heteroscedastic uncertainty head (--uncertainty, EDSR only -- see
decisions.md D016), which additionally produces an uncertainty map.

run_sr_inference() is the reusable core (used by both this CLI script and
the backend API, ml/backend/app/main.py D021, so tiling/blending logic
isn't duplicated). main() below is the file-in/file-out CLI wrapper.
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
from geospatial.preprocessing.cloud_mask import compute_valid_mask, cloud_cover_fraction, apply_cloud_mask

SCALE_FACTOR = 4


def build_model(model_type, uncertainty=False, n_blocks=16, n_channels=64,
                 embed_dim=60, depths="2,2,2,2", num_heads=6, window_size=11):
    if model_type == "edsr":
        out_channels = 8 if uncertainty else 4
        return EDSR(out_channels=out_channels, n_channels=n_channels, n_blocks=n_blocks)
    if uncertainty:
        raise ValueError("uncertainty head is only implemented for EDSR (out_channels=8) -- see decisions.md D016")
    depths_t = tuple(int(d) for d in depths.split(","))
    return SwinIR(embed_dim=embed_dim, depths=depths_t, num_heads=num_heads, window_size=window_size)


def run_sr_inference(model, scene: np.ndarray, tile_size: int, overlap: int, device: str,
                      lr_ranges: np.ndarray, hr_ranges: np.ndarray, uncertainty: bool = False):
    """scene: (C,H,W) raw (un-normalized) LR array. Returns sr_scene (C,H*4,W*4)
    in physical HR-domain units, and std_scene (same shape) or None."""
    scene_norm = _normalize(scene, lr_ranges)
    tiles, padded_shape, orig_shape = extract_tiles(scene_norm, tile_size, overlap)

    mean_predictions = []
    logvar_predictions = []
    model.eval()
    with torch.no_grad():
        for tile, row, col in tiles:
            x = torch.from_numpy(tile).unsqueeze(0).to(device)
            out = model(x)
            if uncertainty:
                mean, log_var = split_mean_logvar(out)
                mean_predictions.append((mean.clamp(0.0, 1.0)[0].cpu().numpy(), row, col))
                logvar_predictions.append((log_var[0].cpu().numpy(), row, col))
            else:
                mean_predictions.append((out.clamp(0.0, 1.0)[0].cpu().numpy(), row, col))

    sr_scene_norm = blend_tiles(mean_predictions, padded_shape, tile_size, SCALE_FACTOR, orig_shape)
    sr_scene = denormalize(sr_scene_norm, hr_ranges)

    std_scene = None
    if uncertainty:
        logvar_scene = blend_tiles(logvar_predictions, padded_shape, tile_size, SCALE_FACTOR, orig_shape)
        std_scene_norm = np.exp(0.5 * logvar_scene)
        band_scale = (hr_ranges[:, 1] - hr_ranges[:, 0]).reshape(-1, 1, 1)
        std_scene = std_scene_norm * band_scale

    return sr_scene, std_scene


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
    p.add_argument("--scl", type=str, default=None,
                    help="optional Sentinel-2 SCL band GeoTIFF, same footprint/grid as --input "
                         "(e.g. from fetch_sentinel2_aoi.py) -- masks cloud/shadow/nodata pixels "
                         "to 0 before inference, since the model was never trained on clouds")
    p.add_argument("--max-cloud-fraction", type=float, default=0.5,
                    help="abort if more than this fraction of the scene is cloud/shadow/nodata (only checked with --scl)")
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

    if args.scl:
        with rasterio.open(args.scl) as src:
            scl = src.read(1)
        cloud_pct = cloud_cover_fraction(scl) * 100
        print(f"cloud/shadow/nodata fraction: {cloud_pct:.2f}%")
        if cloud_pct / 100 > args.max_cloud_fraction:
            raise ValueError(
                f"scene is {cloud_pct:.1f}% cloud/shadow/nodata, above --max-cloud-fraction "
                f"({args.max_cloud_fraction * 100:.0f}%) -- refusing to run SR over unreliable input"
            )
        scene = apply_cloud_mask(scene, compute_valid_mask(scl), fill_value=0.0)

    lr_ranges, hr_ranges = load_norm_stats()

    model = build_model(args.model_type, args.uncertainty, args.n_blocks, args.n_channels,
                         args.embed_dim, args.depths, args.num_heads, args.window_size).to(args.device)
    model.load_state_dict(torch.load(args.checkpoint, map_location=args.device))

    print(f"scene {scene.shape}, tile_size={args.tile_size}, overlap={args.overlap}")
    sr_scene, std_scene = run_sr_inference(
        model, scene, args.tile_size, args.overlap, args.device, lr_ranges, hr_ranges, args.uncertainty)

    write_sr_geotiff(args.output, sr_scene, src_transform, src_crs, SCALE_FACTOR)
    print(f"wrote {args.output}  shape={sr_scene.shape}")

    if args.uncertainty:
        write_sr_geotiff(args.uncertainty_output, std_scene, src_transform, src_crs, SCALE_FACTOR)
        print(f"wrote {args.uncertainty_output}  shape={std_scene.shape}")


if __name__ == "__main__":
    main()
