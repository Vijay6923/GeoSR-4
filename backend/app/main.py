"""GeoSR-4 backend -- synchronous MVP (decisions.md D021). One endpoint:
upload a Sentinel-2 GeoTIFF, get back an SR GeoTIFF + browser-viewable PNG
previews in the same response. No job queue, no database -- see D004/D021
for why that's deferred past today's demo scope.

Run from the repo root: uvicorn backend.app.main:app --reload
"""

import base64
import io
import sys
from typing import Optional
import numpy as np
import rasterio
import torch
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from rasterio.io import MemoryFile

sys.path.insert(0, ".")
from ml.datasets.sen2naip import load_norm_stats, _normalize
from ml.inference.infer_scene import build_model, run_sr_inference, SCALE_FACTOR
from ml.evaluation.metrics import compute_all_metrics
from geospatial.geotiff.export import write_sr_geotiff
from ml.inference.visualize_demo import to_rgb_display

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB -- fine for demo-size patches, not full scenes (see D021)
TILE_SIZE = 121
OVERLAP = 16
CHECKPOINT_PATH = "experiments/swinir_quality/swinir_epoch29.pt"  # D029: perceptual+ICNR, visibly sharper texture
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

app = FastAPI(title="GeoSR-4 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local dev only -- tighten before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

_state = {}


@app.on_event("startup")
def load_model():
    model = build_model("swinir", embed_dim=60, depths="2,2,2,2", num_heads=6, window_size=11).to(DEVICE)
    model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=DEVICE))
    model.eval()
    lr_ranges, hr_ranges = load_norm_stats()
    _state["model"] = model
    _state["lr_ranges"] = lr_ranges
    _state["hr_ranges"] = hr_ranges
    print(f"model loaded on {DEVICE}")


def _png_base64(rgb_array: np.ndarray) -> str:
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    plt.imsave(buf, rgb_array, format="png")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _read_geotiff_bytes(raw: bytes, label: str):
    try:
        with MemoryFile(raw) as memfile, memfile.open() as src:
            arr = src.read().astype(np.float32)
            if src.nodata is not None:
                arr[arr == src.nodata] = 0.0
            return arr, src.transform, src.crs
    except rasterio.errors.RasterioIOError:
        raise HTTPException(400, f"could not read {label} as a GeoTIFF")


@app.post("/api/infer")
async def infer(file: UploadFile = File(...), hr_reference: Optional[UploadFile] = File(None)):
    if not file.filename.lower().endswith((".tif", ".tiff")):
        raise HTTPException(400, "file must be a GeoTIFF (.tif/.tiff)")

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, f"file too large (max {MAX_UPLOAD_BYTES // (1024*1024)} MB for this demo)")

    scene, src_transform, src_crs = _read_geotiff_bytes(raw, "the input file")
    if scene.shape[0] != 4:
        raise HTTPException(400, f"expected 4 bands (R,G,B,NIR), got {scene.shape[0]}")

    sr_scene, _ = run_sr_inference(
        _state["model"], scene, TILE_SIZE, OVERLAP, DEVICE,
        _state["lr_ranges"], _state["hr_ranges"], uncertainty=False,
    )

    # Metrics need a ground-truth HR reference -- only computed if the user
    # provided one (e.g. a dataset hr.tif). Never fabricated otherwise.
    metrics = None
    if hr_reference is not None:
        hr_raw = await hr_reference.read()
        hr_arr, _, _ = _read_geotiff_bytes(hr_raw, "the ground-truth reference")
        if hr_arr.shape != sr_scene.shape:
            raise HTTPException(
                400,
                f"ground-truth reference shape {list(hr_arr.shape)} doesn't match "
                f"the SR output shape {list(sr_scene.shape)} -- must be the matching "
                f"{SCALE_FACTOR}x-resolution reference for this exact input",
            )
        sr_norm = _normalize(sr_scene, _state["hr_ranges"])  # invert sr_scene's own denormalization
        hr_norm = _normalize(hr_arr, _state["hr_ranges"])
        metrics = compute_all_metrics(sr_norm, hr_norm)

    with MemoryFile() as memfile:
        write_sr_geotiff(memfile.name, sr_scene, src_transform, src_crs, SCALE_FACTOR)
        output_geotiff_b64 = base64.b64encode(memfile.read()).decode("ascii")

    input_preview = _png_base64(to_rgb_display(scene))
    output_preview = _png_base64(to_rgb_display(sr_scene))

    return {
        "input_preview_png": input_preview,
        "output_preview_png": output_preview,
        "output_geotiff": output_geotiff_b64,
        "input_shape": list(scene.shape),
        "output_shape": list(sr_scene.shape),
        "input_resolution_m": 10.0,
        "output_resolution_m": 10.0 / SCALE_FACTOR,
        "metrics": metrics,
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "model_loaded": "model" in _state, "device": DEVICE}
