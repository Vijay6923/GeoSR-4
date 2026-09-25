"""Fetches real, HR-only NAIP imagery (no paired Sentinel-2 needed) from
Microsoft Planetary Computer's public STAC API (no account/auth required --
uses short-lived SAS-signed URLs). This is the raw material for synthetic
pretraining (D048): NAIP HR is far more abundant than paired SEN2NAIP
locations, so this lets us build a synthetic-degradation training corpus
much larger than the 2283 real train pairs, by degrading additional real
HR tiles into synthetic LR with opensr-degradation instead of only reusing
the HR half of pairs we already have real LR for.

Resamples NAIP's native 0.6m imagery down to 2.5m/px, 484x484 -- matching
this project's own HR grid convention (121px @ 10m LR -> 484px @ 2.5m HR,
4x scale factor, see D006/D012).
"""

import argparse
import sys
import numpy as np
import planetary_computer
import rasterio
from pystac_client import Client
from rasterio.enums import Resampling
from rasterio.warp import transform
from rasterio.windows import Window

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
TARGET_GSD = 2.5  # m/px, matches this project's HR convention
TARGET_SIZE = 484  # px


def fetch_naip_hr(lon: float, lat: float, output_path: str, datetime_range: str = "2020-01-01/2023-12-31"):
    catalog = Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)
    search = catalog.search(collections=["naip"], bbox=[lon - 0.02, lat - 0.02, lon + 0.02, lat + 0.02],
                             datetime=datetime_range, max_items=5)
    items = list(search.items())
    if not items:
        raise ValueError(f"no NAIP coverage found near ({lon}, {lat}) in {datetime_range}")

    for item in items:
        href = item.assets["image"].href
        with rasterio.open(href) as src:
            xs, ys = transform("EPSG:4326", src.crs, [lon], [lat])
            row, col = src.index(xs[0], ys[0])
            if not (0 <= row < src.height and 0 <= col < src.width):
                continue  # AOI falls in an adjacent tile, not this one

            ground_size_m = TARGET_SIZE * TARGET_GSD  # 1210m for 484px @ 2.5m
            native_gsd = src.res[0]  # ~0.6m
            native_half_px = int((ground_size_m / native_gsd) / 2)

            window = Window(col - native_half_px, row - native_half_px, native_half_px * 2, native_half_px * 2)
            win_transform = src.window_transform(window)
            crs = src.crs

            # decimated read: resample native ~0.6m window directly down to
            # TARGET_SIZE x TARGET_SIZE (2.5m/px) in one pass, no intermediate
            # full-resolution array
            data = src.read(
                window=window,
                out_shape=(src.count, TARGET_SIZE, TARGET_SIZE),
                resampling=Resampling.average,
            ).astype(np.float32)

        # rescale the transform to reflect the actual output pixel size (2.5m, not native)
        out_transform = win_transform * win_transform.scale(
            (native_half_px * 2) / TARGET_SIZE, (native_half_px * 2) / TARGET_SIZE
        )

        profile = {
            "driver": "GTiff", "height": TARGET_SIZE, "width": TARGET_SIZE,
            "count": data.shape[0], "dtype": "float32", "crs": crs, "transform": out_transform,
        }
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(data)
        print(f"fetched {item.id} -> {output_path}  shape={data.shape}  GSD={TARGET_GSD}m")
        return

    raise ValueError(f"found {len(items)} NAIP items near ({lon}, {lat}) but none actually cover the point")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--output", type=str, required=True)
    args = p.parse_args()
    fetch_naip_hr(args.lon, args.lat, args.output)


if __name__ == "__main__":
    main()
