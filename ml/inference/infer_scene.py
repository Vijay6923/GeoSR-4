"""Runs a trained model over an arbitrary-size Sentinel-2 GeoTIFF (not just
the dataset's pre-cut 121x121 patches): tile, normalize, infer, blend,
denormalize, write a GeoTIFF with correct upscaled CRS/transform.

PRD section 25-26 (tiled inference, overlapping tiles) and 40-41
(geospatial preservation). Only EDSR is supported here for now -- SwinIR
needs its tile size to be a window_size multiple (see decisions.md D012),
which isn't handled yet.
"""

import argparse
import sys
import numpy as np
import rasterio
import torch

sys.path.insert(0, ".")
from ml.datasets.sen2naip import load_norm_stats, _normalize, denormalize
from ml.models.edsr.edsr import EDSR
from geospatial.tiling.tiler import extract_tiles, blend_tiles
from geospatial.geotiff.export import write_sr_geotiff

SCALE_FACTOR = 4


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=str, required=True, help="input Sentinel-2 GeoTIFF")
    p.add_argument("--output", type=str, required=True, help="output SR GeoTIFF path")
    p.add_argument("--checkpoint", type=str, required=True)
    p.add_argument("--tile-size", type=int, default=121, help="matches training patch size")
    p.add_argument("--overlap", type=int, default=16)
    p.add_argument("--n-blocks", type=int, default=16)
    p.add_argument("--n-channels", type=int, default=64)
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    args = p.parse_args()

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

    model = EDSR(n_channels=args.n_channels, n_blocks=args.n_blocks).to(args.device)
    model.load_state_dict(torch.load(args.checkpoint, map_location=args.device))
    model.eval()

    predictions = []
    with torch.no_grad():
        for i, (tile, row, col) in enumerate(tiles):
            x = torch.from_numpy(tile).unsqueeze(0).to(args.device)
            sr = model(x).clamp(0.0, 1.0)[0].cpu().numpy()
            predictions.append((sr, row, col))
            if (i + 1) % 20 == 0:
                print(f"  {i + 1}/{len(tiles)} tiles inferred...")

    sr_scene_norm = blend_tiles(predictions, padded_shape, args.tile_size, SCALE_FACTOR, orig_shape)
    sr_scene = denormalize(sr_scene_norm, hr_ranges)

    write_sr_geotiff(args.output, sr_scene, src_transform, src_crs, SCALE_FACTOR)
    print(f"wrote {args.output}  shape={sr_scene.shape}")


if __name__ == "__main__":
    main()
