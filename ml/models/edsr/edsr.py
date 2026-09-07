"""EDSR baseline (PRD section 27, Stage 2) -- standard residual-block CNN
SR architecture, 16 blocks / 64 channels (the "EDSR-baseline" config from the
original paper, ~1.5M params). No batch norm, per EDSR's own finding that BN
hurts SR quality. 4x upsampling via two PixelShuffle(2) stages.
"""

import torch
import torch.nn as nn


class ResidualBlock(nn.Module):
    def __init__(self, n_channels):
        super().__init__()
        self.conv1 = nn.Conv2d(n_channels, n_channels, 3, padding=1)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(n_channels, n_channels, 3, padding=1)

    def forward(self, x):
        return x + self.conv2(self.relu(self.conv1(x)))


class UpsampleBlock(nn.Module):
    """One 2x upsample via sub-pixel convolution."""

    def __init__(self, n_channels):
        super().__init__()
        self.conv = nn.Conv2d(n_channels, n_channels * 4, 3, padding=1)
        self.shuffle = nn.PixelShuffle(2)

    def forward(self, x):
        return self.shuffle(self.conv(x))


class EDSR(nn.Module):
    def __init__(self, in_channels=4, out_channels=4, n_channels=64, n_blocks=16, scale_factor=4):
        super().__init__()
        assert scale_factor in (2, 4), "only 2x or 4x supported by this upsample head"

        self.head = nn.Conv2d(in_channels, n_channels, 3, padding=1)
        self.body = nn.Sequential(*[ResidualBlock(n_channels) for _ in range(n_blocks)])
        self.body_tail = nn.Conv2d(n_channels, n_channels, 3, padding=1)

        n_upsamples = 1 if scale_factor == 2 else 2
        self.upsample = nn.Sequential(*[UpsampleBlock(n_channels) for _ in range(n_upsamples)])

        self.tail = nn.Conv2d(n_channels, out_channels, 3, padding=1)

    def forward(self, x):
        feat = self.head(x)
        res = self.body_tail(self.body(feat))
        feat = feat + res
        feat = self.upsample(feat)
        return self.tail(feat)
