"""Fetches a real Sentinel-2 L2A crop for any lon/lat AOI from the public
AWS Open Data archive (via Element84's Earth Search STAC API) -- no account
or authentication needed. Used for qualitative validation on regions with
no paired training/ground-truth data available (e.g. India -- see
decisions.md D030), where we can run inference but can't compute metrics.
"""

import argparse
import numpy as np
import rasterio
from pystac_client import Client
from rasterio.warp import transform
from rasterio.windows import Window

STAC_URL = "https://earth-search.aws.element84.com/v1"
BAND_ASSETS = ["red", "green", "blue", "nir"]  # R,G,B,NIR -- matches training band order (D006)


def fetch_aoi(lon: float, lat: float, half_size_px: int, output_path: str,
              datetime_range: str = "2025-06-01/2026-03-01", max_cloud: float = 10.0):
    catalog = Client.open(STAC_URL)
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=[lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05],
        datetime=datetime_range,
        query={"eo:cloud_cover": {"lt": max_cloud}},
        max_items=20,
    )
    items = sorted(search.items(), key=lambda i: i.properties.get("eo:cloud_cover", 100))
    if not items:
        raise ValueError(f"no low-cloud Sentinel-2 scenes found near ({lon}, {lat}) in {datetime_range}")

    # try items in cloud-cover order until the AOI actually falls inside the tile
    for item in items:
        with rasterio.open(item.assets["red"].href) as ref:
            xs, ys = transform("EPSG:4326", ref.crs, [lon], [lat])
            row, col = ref.index(xs[0], ys[0])
            if not (0 <= row < ref.height and 0 <= col < ref.width):
                continue  # AOI falls in an adjacent tile, not this one

            window = Window(col - half_size_px, row - half_size_px, half_size_px * 2, half_size_px * 2)
            win_transform = ref.window_transform(window)
            crs = ref.crs

        arrays = [rasterio.open(item.assets[b].href).read(1, window=window) for b in BAND_ASSETS]
        stack = np.stack(arrays)

        profile = {
            "driver": "GTiff", "height": stack.shape[1], "width": stack.shape[2],
            "count": 4, "dtype": stack.dtype, "crs": crs, "transform": win_transform,
        }
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(stack)

        print(f"fetched {item.id} (cloud cover {item.properties.get('eo:cloud_cover'):.3f}%) -> {output_path}")
        print(f"shape: {stack.shape}, bounds: {rasterio.transform.array_bounds(stack.shape[1], stack.shape[2], win_transform)}")
        return

    raise ValueError(f"found scenes near ({lon}, {lat}) but the AOI didn't fall inside any of their tiles")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--half-size-px", type=int, default=200, help="200 -> 400x400px = 4km x 4km at 10m")
    p.add_argument("--output", type=str, required=True)
    p.add_argument("--datetime-range", type=str, default="2025-06-01/2026-03-01")
    p.add_argument("--max-cloud", type=float, default=10.0)
    args = p.parse_args()
    fetch_aoi(args.lon, args.lat, args.half_size_px, args.output, args.datetime_range, args.max_cloud)
