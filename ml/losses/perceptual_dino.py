"""DINOv2/DINOv3 perceptual loss -- alternative backbone for the perceptual
loss in perceptual.py (see that file's docstring for why a perceptual loss
helps at all). This file exists specifically for the domain-mismatch problem:
VGG is ImageNet-pretrained on natural photos, and so is the default DINOv2
checkpoint here -- but Meta also released a DINOv3 checkpoint pretrained on
SAT-493M (satellite imagery), a much closer domain match for Sentinel-2 SR
than either. That checkpoint is gated (Meta license, manual approval, can
take days -- see decisions.md D042), so this defaults to the freely
available DINOv2 checkpoint (no gating, usable immediately) and takes
`model_id` as a constructor arg so the DINOv3 sat493m checkpoint can be
swapped in with zero other code changes once access is approved.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModel

IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
RGB_BANDS = (0, 1, 2)  # R,G,B out of R,G,B,NIR -- see decisions.md D006
DINO_INPUT_SIZE = 224  # divisible by both DINOv2 (patch14) and DINOv3 (patch16) patch sizes

# free, no gating -- swap to "facebook/dinov3-vitl16-pretrain-sat493m" (satellite
# domain, gated) once access is approved (decisions.md D042)
DEFAULT_MODEL_ID = "facebook/dinov2-small"


class DINOPerceptualLoss(nn.Module):
    def __init__(self, model_id: str = DEFAULT_MODEL_ID):
        super().__init__()
        self.backbone = AutoModel.from_pretrained(model_id).eval()
        for p in self.backbone.parameters():
            p.requires_grad = False
        self.register_buffer("mean", IMAGENET_MEAN)
        self.register_buffer("std", IMAGENET_STD)

    def _prepare(self, x: torch.Tensor) -> torch.Tensor:
        rgb = x[:, list(RGB_BANDS), :, :]
        rgb = F.interpolate(rgb, size=(DINO_INPUT_SIZE, DINO_INPUT_SIZE), mode="bilinear", align_corners=False)
        return (rgb - self.mean) / self.std

    def _features(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(pixel_values=x).last_hidden_state

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        pred_feat = self._features(self._prepare(pred))
        with torch.no_grad():
            target_feat = self._features(self._prepare(target))
        return F.l1_loss(pred_feat, target_feat)
