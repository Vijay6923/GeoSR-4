"""Single-pass heteroscedastic uncertainty (PRD section 38-39, alternative
to the MC-ensemble PRD suggests). The model outputs 2x channels: predicted
mean and log-variance, trained with Gaussian NLL. One forward pass gives
both the SR image and a per-pixel confidence map, instead of N forward
passes for an ensemble -- see decisions.md D016 for why this was chosen
over the ensemble approach on a Colab-T4 compute budget."""

import torch

LOG_VAR_CLAMP = 10.0


def split_mean_logvar(output: torch.Tensor):
    """output: (B, 2*C, H, W) -> mean (B,C,H,W), log_var (B,C,H,W)"""
    c = output.shape[1] // 2
    mean = output[:, :c]
    log_var = output[:, c:].clamp(-LOG_VAR_CLAMP, LOG_VAR_CLAMP)
    return mean, log_var


def uncertainty_calibration(mean: torch.Tensor, log_var: torch.Tensor, target: torch.Tensor) -> float:
    """Correlation between predicted std and actual absolute error. A
    well-calibrated uncertainty head should show positive correlation:
    where the model predicts high uncertainty, it should actually be
    more wrong."""
    std = torch.exp(0.5 * log_var).flatten()
    err = (mean - target).abs().flatten()
    std_c = std - std.mean()
    err_c = err - err.mean()
    corr = (std_c * err_c).sum() / (std_c.norm() * err_c.norm() + 1e-8)
    return corr.item()
