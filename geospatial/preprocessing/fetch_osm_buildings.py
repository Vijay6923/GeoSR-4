"""Fetches real OpenStreetMap building footprints for a given raster's
extent and rasterizes them into a binary mask aligned to that raster's own
pixel grid. This exists to fix D033's core flaw: that earlier downstream-
task attempt used SAM's own zero-shot segments as a stand-in for "ground
truth" -- comparing the model against itself, which is circular and gave
an inconclusive, unusable result. OSM building footprints are a real,
independent, externally-sourced ground truth -- see decisions.md D047.
"""

import argparse
import sys
import numpy as np
import rasterio
import requests
from rasterio.features import rasterize
from rasterio.warp import transform, transform_bounds

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Overpass rejects requests with no descriptive User-Agent (406) -- not
# a network failure, caught by checking the actual response body, not
# just the HTTP status
HEADERS = {"User-Agent": "GeoSR-4-research/1.0 (SIH26142 academic project)"}


def fetch_building_ways(lon_min: float, lat_min: float, lon_max: float, lat_max: float, timeout: int = 120) -> dict:
    query = f"""
    [out:json][timeout:{timeout}];
    (
      way["building"]({lat_min},{lon_min},{lat_max},{lon_max});
    );
    out body;
    >;
    out skel qt;
    """
    resp = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=timeout + 10)
    resp.raise_for_status()
    return resp.json()


def osm_json_to_polygons(osm_json: dict) -> list:
    """Returns a list of rings, each a list of (lon, lat) tuples -- one per
    OSM building way. Ways referencing missing nodes (outside the query
    bbox's node set) are skipped."""
    nodes = {el["id"]: (el["lon"], el["lat"]) for el in osm_json["elements"] if el["type"] == "node"}
    polygons = []
    for el in osm_json["elements"]:
        if el["type"] != "way" or "building" not in el.get("tags", {}):
            continue
        coords = [nodes[nid] for nid in el["nodes"] if nid in nodes]
        if len(coords) < 3:
            continue
        polygons.append(coords)
    return polygons


def rasterize_buildings(polygons_lonlat: list, dst_crs, dst_transform, dst_shape: tuple) -> np.ndarray:
    if not polygons_lonlat:
        return np.zeros(dst_shape, dtype=np.uint8)

    shapes = []
    for coords in polygons_lonlat:
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        xs, ys = transform("EPSG:4326", dst_crs, lons, lats)
        ring = list(zip(xs, ys))
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        shapes.append(({"type": "Polygon", "coordinates": [ring]}, 1))

    return rasterize(shapes, out_shape=dst_shape, transform=dst_transform, fill=0, dtype=np.uint8)


def fetch_and_rasterize(reference_path: str) -> tuple:
    """reference_path: any GeoTIFF whose extent/CRS/pixel grid the mask
    should match (LR, SR or HR -- all share the same geographic footprint,
    just different pixel grids). Returns (mask, profile) for writing."""
    with rasterio.open(reference_path) as src:
        dst_crs = src.crs
        dst_transform = src.transform
        dst_shape = (src.height, src.width)
        lon_min, lat_min, lon_max, lat_max = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
        profile = {
            "driver": "GTiff", "dtype": "uint8", "count": 1,
            "height": dst_shape[0], "width": dst_shape[1],
            "crs": dst_crs, "transform": dst_transform, "nodata": 0,
        }

    osm_json = fetch_building_ways(lon_min, lat_min, lon_max, lat_max)
    polygons = osm_json_to_polygons(osm_json)
    mask = rasterize_buildings(polygons, dst_crs, dst_transform, dst_shape)
    return mask, profile, len(polygons)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reference", type=str, required=True, help="GeoTIFF whose extent/CRS/grid the mask should match")
    p.add_argument("--output", type=str, required=True, help="output building-mask GeoTIFF path")
    args = p.parse_args()

    mask, profile, n_buildings = fetch_and_rasterize(args.reference)
    print(f"found {n_buildings} OSM building footprints")
    print(f"building pixel coverage: {mask.mean() * 100:.2f}%")

    with rasterio.open(args.output, "w", **profile) as dst:
        dst.write(mask[None, :, :])
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
