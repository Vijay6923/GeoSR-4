"""Cloud/shadow/nodata masking using Sentinel-2 L2A's own Scene
Classification Layer (SCL) band -- a per-pixel land-cover classification
ESA ships with every L2A product specifically for this purpose. Verified
class codes (2026): 0 nodata, 1 saturated/defective, 2 dark-area shadow,
3 cloud shadow, 4 vegetation, 5 not-vegetated, 6 water, 7 unclassified,
8 cloud medium prob., 9 cloud high prob., 10 thin cirrus, 11 snow/ice.

Named as a known gap in decisions.md/the defense brief -- this closes it
for any pipeline that has the SCL band available (our own AOI fetches;
not guaranteed for an arbitrary 4-band-only user upload).
"""

import numpy as np

# Classes excluded from "usable for SR" -- nodata, sensor defects, cloud
# shadow, both cloud-probability classes, and thin cirrus. Snow (11) and
# dark-area/topographic shadow (2) are kept as usable: they're real
# observed surface, not atmospheric contamination.
INVALID_SCL_CLASSES = {0, 1, 3, 8, 9, 10}


def compute_valid_mask(scl: np.ndarray) -> np.ndarray:
    """scl: (H, W) integer class array. Returns a boolean array, True = usable pixel."""
    invalid = np.isin(scl, list(INVALID_SCL_CLASSES))
    return ~invalid


def cloud_cover_fraction(scl: np.ndarray) -> float:
    """Fraction (0-1) of pixels flagged as cloud/shadow/nodata/defective."""
    return 1.0 - compute_valid_mask(scl).mean()


def apply_cloud_mask(scene: np.ndarray, valid_mask: np.ndarray, fill_value: float = 0.0) -> np.ndarray:
    """scene: (C, H, W). valid_mask: (H, W) boolean, same H/W as scene.
    Sets invalid pixels to fill_value across all bands."""
    out = scene.copy()
    out[:, ~valid_mask] = fill_value
    return out
