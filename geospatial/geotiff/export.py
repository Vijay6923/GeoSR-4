"""Writes an SR array to a GeoTIFF with the CRS/transform correctly scaled
from the source LR raster (PRD section 40-41: geospatial metadata must
survive the whole pipeline, or the output is just a pretty image in the
wrong place on Earth)."""

import numpy as np
import rasterio
from rasterio.transform import Affine


def write_sr_geotiff(path: str, array: np.ndarray, src_transform: Affine, src_crs, scale_factor: int):
    """array: (C, H, W) float32. src_transform/src_crs come from the input
    LR raster -- pixel size shrinks by scale_factor, origin stays the same."""
    new_transform = src_transform * Affine.scale(1.0 / scale_factor, 1.0 / scale_factor)
    C, H, W = array.shape

    profile = {
        "driver": "GTiff",
        "height": H,
        "width": W,
        "count": C,
        "dtype": "float32",
        "crs": src_crs,
        "transform": new_transform,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array.astype(np.float32))
