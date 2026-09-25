"""NDVI (Normalized Difference Vegetation Index) -- a standard, well-established
remote-sensing formula, not a trained model: NDVI = (NIR - Red) / (NIR + Red).
No claim about SR helping this vs bicubic is made or needed here (unlike the
downstream-task validation attempts, D033/D047) -- this is just real band math
run on the real SR output, offered as a feature in its own right (see
decisions.md D049: "Crop Monitoring" was a PRD-listed use case with no
built feature behind it until this).
"""

import numpy as np

RED_BAND = 0
NIR_BAND = 3


def compute_ndvi(scene: np.ndarray) -> np.ndarray:
    """scene: (4,H,W) R,G,B,NIR, any consistent raw scale. Returns (H,W)
    float array in [-1, 1] (clipped -- division noise at very low reflectance
    can otherwise produce out-of-range values)."""
    red = scene[RED_BAND].astype(np.float64)
    nir = scene[NIR_BAND].astype(np.float64)
    denom = nir + red
    ndvi = np.where(denom > 1e-6, (nir - red) / denom, 0.0)
    return np.clip(ndvi, -1.0, 1.0).astype(np.float32)
