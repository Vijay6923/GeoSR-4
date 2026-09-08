"""VGG perceptual loss (PRD section 36) -- the standard fix for the blur
that pure L1/L2 pixel loss produces (well documented since SRGAN/ESRGAN:
pixel loss rewards the statistical average of plausible outputs, which
looks smooth; comparing high-level CNN features instead pushes the model
toward outputs that look sharp/realistic to a human viewer).

VGG is pretrained on natural RGB ImageNet photos, not satellite imagery --
domain mismatch is real, but low/mid-level features (edges, textures)
transfer reasonably well and this is standard practice in remote-sensing SR
literature (see decisions.md D023). Only the R,G,B bands are fed to VGG,
NIR is dropped for this loss term specifically -- matches the PRD's own
note (section 36) that natural-image perceptual models shouldn't blindly
ingest all Sentinel-2 bands.
"""

import torch
import torch.nn as nn
import torchvision.models as tv_models

IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
RGB_BANDS = (0, 1, 2)  # R,G,B out of R,G,B,NIR -- see decisions.md D006


class VGGPerceptualLoss(nn.Module):
    def __init__(self, layer_idx: int = 15):
        """layer_idx=15 -> up to relu3_3 in vgg16.features, a common choice
        for perceptual loss (captures edges/textures, not just low-level
        pixel gradients or high-level semantic content)."""
        super().__init__()
        vgg = tv_models.vgg16(weights=tv_models.VGG16_Weights.IMAGENET1K_V1)
        self.features = vgg.features[:layer_idx].eval()
        for p in self.features.parameters():
            p.requires_grad = False
        self.register_buffer("mean", IMAGENET_MEAN)
        self.register_buffer("std", IMAGENET_STD)

    def _prepare(self, x: torch.Tensor) -> torch.Tensor:
        rgb = x[:, list(RGB_BANDS), :, :]
        return (rgb - self.mean) / self.std

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        pred_feat = self.features(self._prepare(pred))
        with torch.no_grad():
            target_feat = self.features(self._prepare(target))
        return torch.nn.functional.l1_loss(pred_feat, target_feat)
