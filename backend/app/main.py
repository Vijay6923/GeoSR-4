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
from pydantic import BaseModel
from rasterio.io import MemoryFile
from PIL import Image

sys.path.insert(0, ".")
from ml.datasets.sen2naip import load_norm_stats, _normalize
from ml.inference.infer_scene import build_model, run_sr_inference, SCALE_FACTOR
from ml.inference.fuse_models import confidence_weighted_fuse
from ml.evaluation.metrics import compute_all_metrics
from ml.evaluation.ndvi import compute_ndvi
from geospatial.geotiff.export import write_sr_geotiff
from ml.inference.visualize_demo import to_rgb_display

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB -- fine for demo-size patches, not full scenes (see D021)
TILE_SIZE = 121
OVERLAP = 16
CHECKPOINT_PATH = "experiments/swinir_quality/swinir_epoch29.pt"  # D029: perceptual+ICNR, visibly sharper texture
UNCERTAINTY_CHECKPOINT_PATH = "experiments/edsr_uncertainty/edsr_unc_epoch19.pt"  # D036
SAM_CHECKPOINT_PATH = "ml/models/sam/sam_vit_b_01ec64.pth"  # D033/D047, reused for D050 (live Urban Analysis)
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

    # second model, dual-inference (D036): SwinIR gives the sharp image,
    # this EDSR-uncertainty model gives the confidence map -- not the same
    # architecture as the pretty-image model, so run separately
    uncertainty_model = build_model("edsr", uncertainty=True, n_blocks=16, n_channels=64).to(DEVICE)
    uncertainty_model.load_state_dict(torch.load(UNCERTAINTY_CHECKPOINT_PATH, map_location=DEVICE))
    uncertainty_model.eval()

    lr_ranges, hr_ranges = load_norm_stats()
    _state["model"] = model
    _state["uncertainty_model"] = uncertainty_model
    _state["lr_ranges"] = lr_ranges
    _state["hr_ranges"] = hr_ranges

    # D050: SAM for the live "Urban Analysis" feature -- fast settings
    # (small points_per_side) since this runs synchronously in a request,
    # unlike the offline D033/D047 evaluations which could afford to be slower
    try:
        from segment_anything import SamAutomaticMaskGenerator, sam_model_registry
        sam = sam_model_registry["vit_b"](checkpoint=SAM_CHECKPOINT_PATH).to(DEVICE)
        _state["sam_mask_generator"] = SamAutomaticMaskGenerator(sam, points_per_side=12, min_mask_region_area=30)
        print("SAM loaded for Urban Analysis")
    except Exception as e:
        _state["sam_mask_generator"] = None
        print(f"SAM not available, Urban Analysis will be disabled: {e}")

    print(f"models loaded on {DEVICE}")


def _png_base64(rgb_array: np.ndarray) -> str:
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    plt.imsave(buf, rgb_array, format="png")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _heatmap_png_base64(values: np.ndarray) -> str:
    """values: (H,W) float predicted-std array, color-mapped per-request
    (own min/max -- not comparable across requests) with a colorbar baked
    into the image so the scale is a real number, not just relative
    brightness -- see decisions.md D043 (previously had no legend at all)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    h, w = values.shape
    fig, ax = plt.subplots(figsize=(w / 100, h / 100 + 0.5), dpi=100)
    im = ax.imshow(values, cmap="inferno")
    ax.axis("off")
    cbar = fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.05, pad=0.03)
    # tick labels double as plain-language anchors at the extremes -- low std
    # = model is confident, high std = model is unsure (D043)
    lo, hi = float(values.min()), float(values.max())
    ticks = np.linspace(lo, hi, 5)
    cbar.set_ticks(ticks)
    cbar.set_ticklabels(
        [f"{ticks[0]:.0f}\nConfident"] + [f"{t:.0f}" for t in ticks[1:-1]] + [f"{ticks[-1]:.0f}\nUncertain"]
    )
    cbar.ax.tick_params(labelsize=6)
    cbar.set_label("predicted std (raw pixel-value units, same scale as input GeoTIFF)", fontsize=7)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _ndvi_png_base64(ndvi: np.ndarray) -> str:
    """ndvi: (H,W) float in [-1,1]. Fixed color scale (not per-request
    min/max like the uncertainty heatmap, D043) -- NDVI has a real,
    meaningful absolute range, so a scene with little vegetation should
    look uniformly low, not get contrast-stretched to look "average"."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    h, w = ndvi.shape
    fig, ax = plt.subplots(figsize=(w / 100, h / 100 + 0.5), dpi=100)
    im = ax.imshow(ndvi, cmap="RdYlGn", vmin=-1, vmax=1)
    ax.axis("off")
    cbar = fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.05, pad=0.03)
    cbar.set_ticks([-1, -0.5, 0, 0.5, 1])
    cbar.set_ticklabels(["-1\nWater/built-up", "-0.5", "0", "0.5", "1\nDense vegetation"])
    cbar.ax.tick_params(labelsize=6)
    cbar.set_label("NDVI = (NIR - Red) / (NIR + Red)", fontsize=7)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _segmentation_overlay_png_base64(rgb: np.ndarray, masks: list) -> str:
    """rgb: (H,W,3) uint8. masks: list of SAM segmentation dicts. Draws each
    detected segment as a distinct semi-transparent color over the real
    image -- this is real zero-shot detection (D033/D047's SAM setup, just
    fast settings for a live request), not a trained classifier and not a
    claim that SR finds more/better segments than bicubic would (D047 found
    that comparison inconclusive) -- see decisions.md D050."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    h, w = rgb.shape[:2]
    fig, ax = plt.subplots(figsize=(w / 100, h / 100 + 0.4), dpi=100)
    ax.imshow(rgb)

    rng = np.random.default_rng(0)
    overlay = np.zeros((h, w, 4))
    for m in masks:
        color = np.concatenate([rng.random(3), [0.45]])
        overlay[m["segmentation"]] = color
    ax.imshow(overlay)
    ax.axis("off")
    ax.set_title(f"{len(masks)} distinct structures/objects detected", fontsize=9)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _change_png_base64(change_map: np.ndarray) -> str:
    """change_map: (H,W) float, normalized-space mean-absolute-difference
    between two SR outputs, roughly [0,1] -- fixed color scale (same
    reasoning as NDVI, D049: this has a real, meaningful absolute range
    since both inputs were normalized the same way, not a per-request
    stretch that would make every scene look 'medium change')."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    h, w = change_map.shape
    fig, ax = plt.subplots(figsize=(w / 100, h / 100 + 0.5), dpi=100)
    im = ax.imshow(change_map, cmap="inferno", vmin=0, vmax=0.5)
    ax.axis("off")
    cbar = fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.05, pad=0.03)
    cbar.set_ticks([0, 0.125, 0.25, 0.375, 0.5])
    cbar.set_ticklabels(["0\nNo change", "", "0.25", "", "0.5+\nMajor change"])
    cbar.ax.tick_params(labelsize=6)
    cbar.set_label("mean absolute difference (normalized reflectance)", fontsize=7)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
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

    swinir_out, _ = run_sr_inference(
        _state["model"], scene, TILE_SIZE, OVERLAP, DEVICE,
        _state["lr_ranges"], _state["hr_ranges"], uncertainty=False,
    )
    edsr_mean, edsr_std = run_sr_inference(
        _state["uncertainty_model"], scene, TILE_SIZE, OVERLAP, DEVICE,
        _state["lr_ranges"], _state["hr_ranges"], uncertainty=True,
    )
    uncertainty_preview = _heatmap_png_base64(edsr_std.mean(axis=0))

    # D038: confidence-weighted fusion beats either model alone on every
    # metric across the full validation set -- this is what we serve now,
    # not raw SwinIR
    sr_scene, _ = confidence_weighted_fuse(edsr_mean, edsr_std, swinir_out)

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
    ndvi_preview = _ndvi_png_base64(compute_ndvi(sr_scene))

    return {
        "input_preview_png": input_preview,
        "output_preview_png": output_preview,
        "uncertainty_preview_png": uncertainty_preview,
        "ndvi_preview_png": ndvi_preview,
        "output_geotiff": output_geotiff_b64,
        "input_shape": list(scene.shape),
        "output_shape": list(sr_scene.shape),
        "input_resolution_m": 10.0,
        "output_resolution_m": 10.0 / SCALE_FACTOR,
        "metrics": metrics,
    }


class UrbanAnalysisRequest(BaseModel):
    image_png_base64: str


@app.post("/api/urban-analysis")
def urban_analysis(req: UrbanAnalysisRequest):
    """D050: real zero-shot structure/building segmentation on the SR
    output PNG the frontend already has (no need to re-run SR inference --
    reuses ml/evaluation/downstream_segmentation_v2.py's SAM setup, D033/D047,
    at faster settings since this runs synchronously in a request)."""
    if _state.get("sam_mask_generator") is None:
        raise HTTPException(503, "Urban Analysis is unavailable -- SAM model failed to load on this server")

    try:
        png_bytes = base64.b64decode(req.image_png_base64)
        rgb = np.array(Image.open(io.BytesIO(png_bytes)).convert("RGB"))
    except Exception:
        raise HTTPException(400, "could not decode image_png_base64 as an image")

    masks = _state["sam_mask_generator"].generate(rgb)
    masks = [m for m in masks if m["area"] >= 30]

    return {
        "overlay_png": _segmentation_overlay_png_base64(rgb, masks),
        "n_segments": len(masks),
    }


@app.post("/api/change-detection")
async def change_detection(before: UploadFile = File(...), after: UploadFile = File(...)):
    """D050: real before/after change detection -- runs SR on both uploads
    and reports mean-absolute-difference between the two SR outputs.
    Assumes both inputs are already the same pixel grid (same AOI, same
    crop, different acquisition dates) -- no georeferencing/alignment is
    attempted here, just a shape check; a real mismatch (different crop
    extents) is rejected rather than silently comparing misaligned pixels."""
    for f, label in [(before, "'before'"), (after, "'after'")]:
        if not f.filename.lower().endswith((".tif", ".tiff")):
            raise HTTPException(400, f"the {label} file must be a GeoTIFF (.tif/.tiff)")

    before_raw = await before.read()
    after_raw = await after.read()
    for raw, label in [(before_raw, "'before'"), (after_raw, "'after'")]:
        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(400, f"the {label} file is too large (max {MAX_UPLOAD_BYTES // (1024*1024)} MB for this demo)")

    before_scene, before_transform, before_crs = _read_geotiff_bytes(before_raw, "the 'before' file")
    after_scene, _, _ = _read_geotiff_bytes(after_raw, "the 'after' file")

    if before_scene.shape[0] != 4 or after_scene.shape[0] != 4:
        raise HTTPException(400, "both files must have 4 bands (R,G,B,NIR)")
    if before_scene.shape != after_scene.shape:
        raise HTTPException(
            400,
            f"'before' ({list(before_scene.shape)}) and 'after' ({list(after_scene.shape)}) must be the same "
            "shape -- same AOI/crop, just a different acquisition date. This demo does not align mismatched extents.",
        )

    before_sr, _ = run_sr_inference(
        _state["model"], before_scene, TILE_SIZE, OVERLAP, DEVICE, _state["lr_ranges"], _state["hr_ranges"], uncertainty=False,
    )
    after_sr, _ = run_sr_inference(
        _state["model"], after_scene, TILE_SIZE, OVERLAP, DEVICE, _state["lr_ranges"], _state["hr_ranges"], uncertainty=False,
    )

    before_norm = _normalize(before_sr, _state["hr_ranges"])
    after_norm = _normalize(after_sr, _state["hr_ranges"])
    change_map = np.abs(after_norm - before_norm).mean(axis=0)

    return {
        "before_preview_png": _png_base64(to_rgb_display(before_sr)),
        "after_preview_png": _png_base64(to_rgb_display(after_sr)),
        "change_preview_png": _change_png_base64(change_map),
        "output_shape": list(before_sr.shape),
        "output_resolution_m": 10.0 / SCALE_FACTOR,
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": "model" in _state,
        "uncertainty_model_loaded": "uncertainty_model" in _state,
        "device": DEVICE,
    }
