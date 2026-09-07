"""Generic GeoTIFF metadata extraction — used for both the paired training
data and arbitrary Sentinel-2 scenes supplied at inference time."""

import rasterio


def read_geotiff_metadata(path: str) -> dict:
    with rasterio.open(path) as src:
        return {
            "width": src.width,
            "height": src.height,
            "bands": src.count,
            "dtype": src.dtypes[0],
            "crs": str(src.crs),
            "transform": tuple(src.transform),
            "resolution": src.res,
            "bounds": tuple(src.bounds),
            "nodata": src.nodata,
        }
