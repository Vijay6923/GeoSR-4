"""Evaluates confidence-weighted EDSR/SwinIR fusion on the FULL validation
split (279 pairs), reporting EDSR-alone, SwinIR-alone, and fused metrics
side by side -- so we know if fusion genuinely helps on average, not just
on one lucky/unlucky sample."""

import sys
import numpy as np
import torch
from torch.utils.data import DataLoader

sys.path.insert(0, ".")
from ml.datasets.sen2naip import SEN2NAIPCrossSensor, tile_disjoint_split
from ml.inference.infer_scene import build_model
from ml.uncertainty.heteroscedastic import split_mean_logvar
from ml.inference.fuse_models import confidence_weighted_fuse, EDSR_CHECKPOINT, SWINIR_CHECKPOINT
from ml.evaluation.metrics import compute_all_metrics

ROOT = "ml/datasets/raw/sen2naip/cross-sensor/extracted/cross-sensor"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def main():
    splits = tile_disjoint_split(ROOT)
    val_ds = SEN2NAIPCrossSensor(splits["val"])
    loader = DataLoader(val_ds, batch_size=1, shuffle=False)

    edsr = build_model("edsr", uncertainty=True, n_blocks=16, n_channels=64).to(DEVICE)
    edsr.load_state_dict(torch.load(EDSR_CHECKPOINT, map_location=DEVICE))
    edsr.eval()

    swinir = build_model("swinir", embed_dim=60, depths="2,2,2,2", num_heads=6, window_size=11).to(DEVICE)
    swinir.load_state_dict(torch.load(SWINIR_CHECKPOINT, map_location=DEVICE))
    swinir.eval()

    results = {"edsr": {"psnr": [], "ssim": [], "sam": [], "ergas": []},
               "swinir": {"psnr": [], "ssim": [], "sam": [], "ergas": []},
               "fused": {"psnr": [], "ssim": [], "sam": [], "ergas": []}}

    with torch.no_grad():
        for i, batch in enumerate(loader):
            lr = batch["lr"].to(DEVICE)
            hr = batch["hr"][0].numpy()

            edsr_out = edsr(lr)
            edsr_mean, edsr_log_var = split_mean_logvar(edsr_out)
            edsr_mean_np = edsr_mean.clamp(0.0, 1.0)[0].cpu().numpy()
            edsr_std_np = torch.exp(0.5 * edsr_log_var)[0].cpu().numpy()

            swinir_np = swinir(lr).clamp(0.0, 1.0)[0].cpu().numpy()

            fused_np, _ = confidence_weighted_fuse(edsr_mean_np, edsr_std_np, swinir_np)
            fused_np = np.clip(fused_np, 0.0, 1.0)

            for name, pred in [("edsr", edsr_mean_np), ("swinir", swinir_np), ("fused", fused_np)]:
                m = compute_all_metrics(pred, hr)
                for k, v in m.items():
                    results[name][k].append(v)

            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{len(val_ds)} pairs evaluated...")

    print(f"\nFusion evaluation (n={len(val_ds)} validation pairs)")
    for name in ["edsr", "swinir", "fused"]:
        r = results[name]
        print(f"{name:8s} PSNR {np.mean(r['psnr']):.2f}  SSIM {np.mean(r['ssim']):.4f}  "
              f"SAM {np.mean(r['sam']):.2f}  ERGAS {np.mean(r['ergas']):.2f} (median {np.median(r['ergas']):.2f})")


if __name__ == "__main__":
    main()
