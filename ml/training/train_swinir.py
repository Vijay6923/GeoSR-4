"""Trains the SwinIR baseline. Same L1-only, smoke-test-locally /
train-on-Colab workflow as train_edsr.py (decisions.md D010). See D012 for
why window_size=11 and the chosen embed_dim/depths."""

import argparse
import os
import re
import sys
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

sys.path.insert(0, ".")
from ml.datasets.sen2naip import SEN2NAIPCrossSensor, tile_disjoint_split
from ml.models.swinir.swinir import SwinIR
from ml.evaluation.metrics import compute_all_metrics
from ml.losses.spectral import SpectralAngleLoss
from ml.losses.edge import EdgeLoss
from ml.losses.perceptual import VGGPerceptualLoss
from ml.losses.perceptual_dino import DINOPerceptualLoss, DEFAULT_MODEL_ID as DEFAULT_DINO_MODEL_ID

ROOT = "ml/datasets/raw/sen2naip/cross-sensor/extracted/cross-sensor"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--max-rois", type=int, default=None, help="cap train set size, for smoke tests")
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--embed-dim", type=int, default=60)
    p.add_argument("--depths", type=str, default="2,2,2,2", help="comma-separated RSTB depths")
    p.add_argument("--num-heads", type=int, default=6)
    p.add_argument("--window-size", type=int, default=11)
    p.add_argument("--checkpoint-dir", type=str, default="experiments/swinir")
    p.add_argument("--log-every", type=int, default=10)
    p.add_argument("--lambda-spectral", type=float, default=0.0, help="PRD section 34-35, 0 = L1 only (baseline)")
    p.add_argument("--lambda-edge", type=float, default=0.0, help="PRD section 37, 0 = L1 only (baseline)")
    p.add_argument("--lambda-perceptual", type=float, default=0.0, help="PRD section 36, perceptual loss -- see decisions.md D023")
    p.add_argument("--perceptual-backbone", type=str, default="vgg", choices=["vgg", "dino"],
                    help="which frozen network to compare features against for the perceptual loss -- "
                         "'vgg' (default, D023) or 'dino' (DINOv2/DINOv3, see decisions.md D042)")
    p.add_argument("--dino-model-id", type=str, default=DEFAULT_DINO_MODEL_ID,
                    help="HF model id for --perceptual-backbone dino. Defaults to the free DINOv2 checkpoint; "
                         "pass 'facebook/dinov3-vitl16-pretrain-sat493m' once gated access is approved "
                         "(requires `huggingface-cli login` with an approved token -- D042)")
    p.add_argument("--no-icnr-init", action="store_true",
                    help="disable ICNR upsample init (random init instead) -- D040 ablation only, "
                         "isolates ICNR's contribution from the perceptual loss's. Leave ICNR on otherwise.")
    p.add_argument("--amp", action="store_true",
                    help="mixed-precision training (uses GPU Tensor Cores, e.g. on T4) -- no-op on CPU. "
                         "Loss terms (SAM's acos, edge loss's sqrt) still computed in float32 for "
                         "numerical stability -- see decisions.md D035 for why.")
    p.add_argument("--resume-from", type=str, default=None,
                    help="checkpoint path (e.g. experiments/x/swinir_epoch23.pt) to resume from -- "
                         "for Colab/Kaggle session disconnects (D042). Loads model weights and continues "
                         "from checkpoint_epoch+1; optimizer state (Adam momentum) is NOT restored -- "
                         "a known, accepted simplification for this recovery path, not a precision run.")
    return p.parse_args()


def evaluate(model, val_ds, device, max_samples=50):
    model.eval()
    results = {"psnr": [], "ssim": [], "sam": [], "ergas": []}
    with torch.no_grad():
        for i in range(min(max_samples, len(val_ds))):
            sample = val_ds[i]
            lr = sample["lr"].unsqueeze(0).to(device)
            sr = model(lr)[0].clamp(0.0, 1.0).cpu().numpy()
            hr = sample["hr"].numpy()
            m = compute_all_metrics(sr, hr)
            for k, v in m.items():
                results[k].append(v)
    model.train()
    return {k: sum(v) / len(v) for k, v in results.items()}


def main():
    args = parse_args()
    depths = tuple(int(d) for d in args.depths.split(","))
    print(f"device: {args.device}  depths: {depths}")

    splits = tile_disjoint_split(ROOT)
    train_rois = splits["train"][: args.max_rois] if args.max_rois else splits["train"]
    train_ds = SEN2NAIPCrossSensor(train_rois)
    val_ds = SEN2NAIPCrossSensor(splits["val"])
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)

    print(f"train pairs: {len(train_ds)}  val pairs: {len(val_ds)}")

    model = SwinIR(
        embed_dim=args.embed_dim, depths=depths,
        num_heads=args.num_heads, window_size=args.window_size,
        use_icnr_init=not args.no_icnr_init,
    ).to(args.device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    l1_loss = nn.L1Loss()
    spectral_loss = SpectralAngleLoss().to(args.device)
    edge_loss = EdgeLoss().to(args.device)
    perceptual_loss = None
    if args.lambda_perceptual > 0:
        if args.perceptual_backbone == "dino":
            perceptual_loss = DINOPerceptualLoss(args.dino_model_id).to(args.device)
        else:
            perceptual_loss = VGGPerceptualLoss().to(args.device)

    print(f"loss: L1 + {args.lambda_spectral} * spectral + {args.lambda_edge} * edge + "
          f"{args.lambda_perceptual} * perceptual ({args.perceptual_backbone})")

    start_epoch = 0
    if args.resume_from:
        model.load_state_dict(torch.load(args.resume_from, map_location=args.device))
        resumed_epoch = int(re.search(r"epoch(\d+)", args.resume_from).group(1))
        start_epoch = resumed_epoch + 1
        print(f"resumed from {args.resume_from} (epoch {resumed_epoch}) -- continuing at epoch {start_epoch}")

    amp_enabled = args.amp and args.device == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=amp_enabled)
    if args.amp and not amp_enabled:
        print("--amp requested but no CUDA device -- running in plain fp32 (no-op on CPU)")

    os.makedirs(args.checkpoint_dir, exist_ok=True)

    step = start_epoch * len(train_loader)
    for epoch in range(start_epoch, args.epochs):
        epoch_start = time.time()
        for batch in train_loader:
            lr = batch["lr"].to(args.device)
            hr = batch["hr"].to(args.device)

            optimizer.zero_grad()

            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=amp_enabled):
                sr = model(lr)

            # loss terms (SAM's acos, edge loss's sqrt) computed in fp32 --
            # same reasoning as D035, these have known gradient-stability
            # edge cases mixed precision would add risk to for no benefit
            sr = sr.float()
            loss = l1_loss(sr, hr)
            if args.lambda_spectral > 0:
                loss = loss + args.lambda_spectral * spectral_loss(sr, hr)
            if args.lambda_edge > 0:
                loss = loss + args.lambda_edge * edge_loss(sr, hr)
            if perceptual_loss is not None:
                loss = loss + args.lambda_perceptual * perceptual_loss(sr, hr)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            if step % args.log_every == 0:
                print(f"epoch {epoch} step {step} loss {loss.item():.4f}")
            step += 1

        print(f"epoch {epoch} done in {time.time() - epoch_start:.1f}s")
        metrics = evaluate(model, val_ds, args.device)
        print(f"epoch {epoch} val metrics: {metrics}")

        if torch.cuda.is_available():
            torch.cuda.empty_cache()  # D025: switching train(batch=16)<->eval(batch=1) fragments the allocator

        ckpt_path = f"{args.checkpoint_dir}/swinir_epoch{epoch}.pt"
        torch.save(model.state_dict(), ckpt_path)
        print(f"saved {ckpt_path}")


if __name__ == "__main__":
    main()
