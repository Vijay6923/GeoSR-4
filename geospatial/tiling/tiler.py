"""Overlapping-tile extraction and Hann-window blended reassembly (PRD
section 25-26: split large scenes into tiles, blend to avoid visible tile
boundaries). Needed because a trained model only knows how to process
patches at its training size, but real Sentinel-2 scenes are much larger."""

import numpy as np


def extract_tiles(array: np.ndarray, tile_size: int, overlap: int):
    """array: (C, H, W). Edge-pads to a whole number of strided tiles, then
    slices them out. Returns (tiles, padded_shape, original_shape), where
    tiles is a list of (tile_array, row_offset, col_offset)."""
    C, H, W = array.shape
    stride = tile_size - overlap

    n_rows = max(1, int(np.ceil((H - overlap) / stride)))
    n_cols = max(1, int(np.ceil((W - overlap) / stride)))
    padded_h = (n_rows - 1) * stride + tile_size
    padded_w = (n_cols - 1) * stride + tile_size

    padded = np.pad(array, ((0, 0), (0, padded_h - H), (0, padded_w - W)), mode="edge")

    tiles = []
    for r in range(n_rows):
        for c in range(n_cols):
            row, col = r * stride, c * stride
            tiles.append((padded[:, row:row + tile_size, col:col + tile_size], row, col))

    return tiles, (padded_h, padded_w), (H, W)


def _hann_window_2d(size: int) -> np.ndarray:
    w = np.hanning(size) if size > 1 else np.ones(1)
    w2d = np.outer(w, w)
    return np.clip(w2d, 1e-3, None)  # avoid exact-zero weight at tile borders


def blend_tiles(predictions, padded_shape, tile_size: int, scale_factor: int, out_shape):
    """predictions: list of (pred_tile (C, tile_size*scale, tile_size*scale),
    row, col) in INPUT-space coordinates (same row/col that extract_tiles
    returned). Reassembles into (C, out_H, out_W) via Hann-window weighted
    averaging in overlap regions."""
    C = predictions[0][0].shape[0]
    padded_h, padded_w = padded_shape
    out_padded_h, out_padded_w = padded_h * scale_factor, padded_w * scale_factor
    out_tile_size = tile_size * scale_factor

    acc = np.zeros((C, out_padded_h, out_padded_w), dtype=np.float32)
    weight = np.zeros((out_padded_h, out_padded_w), dtype=np.float32)
    win = _hann_window_2d(out_tile_size)

    for pred, row, col in predictions:
        out_row, out_col = row * scale_factor, col * scale_factor
        acc[:, out_row:out_row + out_tile_size, out_col:out_col + out_tile_size] += pred * win
        weight[out_row:out_row + out_tile_size, out_col:out_col + out_tile_size] += win

    blended = acc / np.clip(weight, 1e-8, None)
    out_H, out_W = out_shape[0] * scale_factor, out_shape[1] * scale_factor
    return blended[:, :out_H, :out_W]
