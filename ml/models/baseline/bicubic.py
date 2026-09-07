"""Stage 1 baseline (PRD section 27): plain bicubic upsampling, no learning.
This is the floor every later model must beat."""

import torch
import torch.nn.functional as F

SCALE_FACTOR = 4


def upsample_bicubic(lr: torch.Tensor) -> torch.Tensor:
    """lr: (B, C, H, W) -> (B, C, H*4, W*4)"""
    return F.interpolate(lr, scale_factor=SCALE_FACTOR, mode="bicubic", align_corners=False).clamp(0.0, 1.0)
