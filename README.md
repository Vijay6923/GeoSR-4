---
title: GeoSR-4
emoji: 🛰️
colorFrom: blue
colorTo: orange
sdk: docker
app_port: 7860
pinned: false
---

# GeoSR-4

AI-based super-resolution for medium-resolution satellite imagery — SIH 2026 Problem Statement **26142** (NTRO, Space Technology theme).

**10 m Sentinel-2 imagery → deep learning reconstruction → <4 m geospatially consistent output**, with explicit uncertainty estimation and quantitative validation (not just visual sharpening).

## Docs

- [`GeoSR-4-Complete-PRD.md`](./GeoSR-4-Complete-PRD.md) — full product & technical PRD (architecture, ML pipeline, phased build plan)
- [`SIH26142.TXT`](./SIH26142.TXT) — original problem statement text
- [`decisions.md`](./decisions.md) — running log of project decisions and the reasoning behind each one

## Status

Working end-to-end demo: SwinIR super-resolution (DINOv3-sat493m perceptual loss, D042), EDSR-based uncertainty estimation, confidence-weighted fusion, NDVI/Urban Analysis/Change Detection features, real Indian-AOI validation. Full history and reasoning for every decision in `decisions.md` (D001–D056+).

## Live demo

Deployed as a single Docker container on Hugging Face Spaces (frontend + backend, one URL, no separate hosting) -- see `decisions.md` D056 for the deployment approach.

## Repo structure

```
frontend/      React + TypeScript dashboard
backend/       FastAPI application
ml/            models, datasets, losses, training, inference, uncertainty, evaluation
geospatial/    preprocessing, tiling, alignment, GeoTIFF handling
experiments/   training run outputs (gitignored)
notebooks/     exploratory notebooks
configs/       run/model configs
tests/
docker/
```

## Running the full stack (backend + frontend)

Backend (from repo root, needs `experiments/swinir/swinir_epoch19.pt` present -- see the SwinIR Colab notebook):

```bash
uvicorn backend.app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the printed `localhost` URL, upload a 4-band (R,G,B,NIR) Sentinel-2 GeoTIFF, and the SR output renders in the page -- see `decisions.md` D021/D022 for why this is synchronous (no job queue) and single-page for now.

## Local demo (CLI, no server)

Once you have a trained checkpoint (e.g. `experiments/swinir/swinir_epoch19.pt`, downloaded from a Colab training run -- see the notebooks):

```bash
# 1. Run the model over an LR GeoTIFF, producing an SR GeoTIFF
python ml/inference/infer_scene.py \
  --input path/to/input_lr.tif \
  --output path/to/output_sr.tif \
  --checkpoint experiments/swinir/swinir_epoch19.pt \
  --model-type swinir --embed-dim 60 --depths 2,2,2,2 --num-heads 6 --window-size 11 \
  --tile-size 121 --overlap 16

# 2. Visualize LR vs SR vs ground truth (if available) side by side
python ml/inference/visualize_demo.py \
  --lr path/to/input_lr.tif \
  --sr path/to/output_sr.tif \
  --hr path/to/ground_truth_hr.tif \
  --output demo_comparison.png
```

See `decisions.md` D020 for why SwinIR (not EDSR) was chosen for the demo, and a known checkerboard-texture artifact from PixelShuffle upsampling that's flagged for a future fix, not yet resolved.

## Dataset

Training/validation data is [`isp-uv-es/SEN2NAIP`](https://huggingface.co/datasets/isp-uv-es/SEN2NAIP) (CC-BY-4.0). The raw zip is not committed to this repo (too large, easily reproducible). To fetch the cross-sensor split used so far:

```python
from huggingface_hub import hf_hub_download

hf_hub_download(
    repo_id="isp-uv-es/SEN2NAIP",
    repo_type="dataset",
    filename="cross-sensor/cross-sensor.zip",
    local_dir="ml/datasets/raw/sen2naip",
)
```
