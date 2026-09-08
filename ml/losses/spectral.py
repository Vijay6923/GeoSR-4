"""Differentiable Spectral Angle Mapper loss (PRD section 34-35). Same
formula as ml/evaluation/metrics.py's compute_sam, but torch-native (and
angle-clamped away from +/-1 for acos gradient stability) so it's usable
during training, not just evaluation."""

import torch
import torch.nn as nn


class SpectralAngleLoss(nn.Module):
    def __init__(self, eps=1e-8):
        super().__init__()
        self.eps = eps

    def forward(self, pred, target):
        B, C, H, W = pred.shape
        pred_flat = pred.reshape(B, C, -1)
        target_flat = target.reshape(B, C, -1)
        dot = (pred_flat * target_flat).sum(dim=1)
        denom = pred_flat.norm(dim=1) * target_flat.norm(dim=1) + self.eps
        cos_angle = torch.clamp(dot / denom, -1.0 + 1e-7, 1.0 - 1e-7)
        return torch.acos(cos_angle).mean()
