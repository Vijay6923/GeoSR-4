"""PSNR, SSIM, SAM, ERGAS — the four metrics the PRD requires for every model
comparison (see PRD section 14/47-50). Operates on (C, H, W) numpy arrays in
the same [0,1] normalized scale the dataset loader produces.
"""

import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

# HR pixel size / LR pixel size, per D006's verified metadata (2.5m / 10m).
RESOLUTION_RATIO = 2.5 / 10.0


def compute_psnr(pred: np.ndarray, target: np.ndarray, data_range=1.0) -> float:
    return float(peak_signal_noise_ratio(target, pred, data_range=data_range))


def compute_ssim(pred: np.ndarray, target: np.ndarray, data_range=1.0) -> float:
    return float(structural_similarity(target, pred, data_range=data_range, channel_axis=0))


def compute_sam(pred: np.ndarray, target: np.ndarray, eps=1e-8) -> float:
    """Spectral Angle Mapper, in degrees. Lower is better (more spectrally similar)."""
    pred_flat = pred.reshape(pred.shape[0], -1)
    target_flat = target.reshape(target.shape[0], -1)
    dot = np.sum(pred_flat * target_flat, axis=0)
    denom = np.linalg.norm(pred_flat, axis=0) * np.linalg.norm(target_flat, axis=0) + eps
    cos_angle = np.clip(dot / denom, -1.0, 1.0)
    return float(np.degrees(np.mean(np.arccos(cos_angle))))


def compute_ergas(pred: np.ndarray, target: np.ndarray, resolution_ratio=RESOLUTION_RATIO, eps=1e-8) -> float:
    """Lower is better. Remote-sensing-specific reconstruction error, per-band
    RMSE normalized by that band's mean, scaled by the resolution ratio."""
    n_bands = pred.shape[0]
    band_terms = []
    for c in range(n_bands):
        rmse = np.sqrt(np.mean((pred[c] - target[c]) ** 2))
        band_mean = np.mean(target[c])
        band_terms.append((rmse / (band_mean + eps)) ** 2)
    return float(100 * resolution_ratio * np.sqrt(np.mean(band_terms)))


def compute_all_metrics(pred: np.ndarray, target: np.ndarray) -> dict:
    return {
        "psnr": compute_psnr(pred, target),
        "ssim": compute_ssim(pred, target),
        "sam": compute_sam(pred, target),
        "ergas": compute_ergas(pred, target),
    }
