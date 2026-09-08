"""Shared PixelShuffle upsample block, used by both EDSR and SwinIR.

ICNR initialization (Aitken et al., 2017) fixes the checkerboard/ripple
artifact PixelShuffle produces under standard random init: at
initialization, each of the r^2 sub-pixel positions starts from
independent random weights, so the network begins training from an
already-inconsistent upsample and the artifact can persist. ICNR instead
initializes all r^2 positions from the SAME kernel, so PixelShuffle starts
out equivalent to nearest-neighbor upsampling (artifact-free at init) --
see decisions.md D023, and D020 for the artifact this fixes.
"""

import torch
import torch.nn as nn


def icnr_init(conv: nn.Conv2d, upscale_factor: int, init_fn=nn.init.kaiming_normal_):
    """conv.weight: (out_channels, in_channels, kh, kw) where
    out_channels = base_channels * upscale_factor**2 (PixelShuffle's expected
    layout). Also equalizes bias across each repeated group -- nn.Conv2d's
    default bias init is independently random per output channel, which
    would otherwise break the uniform-2x2-patch property this is for."""
    out_channels, in_channels, kh, kw = conv.weight.shape
    r2 = upscale_factor ** 2
    base_channels = out_channels // r2

    sub_kernel = torch.zeros(base_channels, in_channels, kh, kw)
    init_fn(sub_kernel)
    conv.weight.data.copy_(sub_kernel.repeat_interleave(r2, dim=0))

    if conv.bias is not None:
        sub_bias = torch.zeros(base_channels)
        conv.bias.data.copy_(sub_bias.repeat_interleave(r2, dim=0))


class UpsampleBlock(nn.Module):
    """One 2x upsample via ICNR-initialized sub-pixel convolution."""

    def __init__(self, n_channels: int):
        super().__init__()
        self.conv = nn.Conv2d(n_channels, n_channels * 4, 3, padding=1)
        icnr_init(self.conv, upscale_factor=2)
        self.shuffle = nn.PixelShuffle(2)

    def forward(self, x):
        return self.shuffle(self.conv(x))
