"""Edge-aware loss (PRD section 37) -- Sobel-gradient L1 distance between SR
and HR, to keep road/building/field/water boundaries sharp instead of
letting L1 alone smooth them out."""

import torch
import torch.nn as nn
import torch.nn.functional as F


class EdgeLoss(nn.Module):
    def __init__(self):
        super().__init__()
        sobel_x = torch.tensor([[-1., 0., 1.], [-2., 0., 2.], [-1., 0., 1.]])
        sobel_y = sobel_x.t()
        self.register_buffer("sobel_x", sobel_x.view(1, 1, 3, 3))
        self.register_buffer("sobel_y", sobel_y.view(1, 1, 3, 3))

    def _gradient_magnitude(self, x):
        B, C, H, W = x.shape
        x = x.reshape(B * C, 1, H, W)
        gx = F.conv2d(x, self.sobel_x, padding=1)
        gy = F.conv2d(x, self.sobel_y, padding=1)
        mag = torch.sqrt(gx ** 2 + gy ** 2 + 1e-8)
        return mag.reshape(B, C, H, W)

    def forward(self, pred, target):
        return F.l1_loss(self._gradient_magnitude(pred), self._gradient_magnitude(target))
