"""Wraps opensr-degradation's NAIP->Sentinel-2-like degradation model into a
single function: real HR-only NAIP tile in, synthetic (LR, HR) pair out.
Used to build a synthetic pretraining corpus much larger than the 2283 real
SEN2NAIP train pairs (D048) -- real NAIP HR is abundant (fetch_naip_hr.py),
paired real Sentinel-2 LR for the same exact footprint is not.

Two real bugs in opensr-degradation v1.0.1 worked around here (see
decisions.md D048):
  1. Its `reflectance_method` param defaults to a bare string
     ("gamma_multivariate_normal"); the library's own code does
     `for method in methods`, which iterates a string character-by-character
     and crashes (KeyError: 'g'). Passing it as a list avoids the bug.
  2. `full_forward`'s internal 4x downsample rounds to 122x122 for a 484px
     input, not the exact 121x121 this project's LR tiles use everywhere
     else -- cropped to 121x121 (center crop) here so synthetic pairs are
     shape-compatible with the real dataset's tensors.

The `vae_histogram_matching` reflectance method (the package's own default
in `get_s2like`) was tried and produced near-zero, degenerate output in
this environment (verified: no NaNs, but all values within +/-0.01) --
not debugged further (third-party model weights issue, out of scope);
`gamma_multivariate_normal` (a non-learned statistical method) was verified
visually to produce plausible-looking blur/degradation instead.
"""

import torch
from opensr_degradation.main import pipe

TARGET_LR_SIZE = 121

_pipe = None


def _get_pipe():
    global _pipe
    if _pipe is None:
        _pipe = pipe(sensor="naip_d", params={"reflectance_method": ["gamma_multivariate_normal"]})
    return _pipe


def degrade_hr_to_pair(hr: torch.Tensor) -> tuple:
    """hr: (4,484,484) float tensor, raw NAIP DN scale (0-255ish, matches
    fetch_naip_hr.py's output -- NOT pre-normalized). Returns
    (lr, hr_harmonized): lr is (4,121,121), hr_harmonized is (4,484,484),
    both in the package's own harmonized-reflectance scale (roughly [0,1],
    not the same raw scale as the input -- this is intentional, it's the
    "as if imaged by Sentinel-2-like sensor" scale)."""
    p = _get_pipe()
    lr_122, hr_out = p.full_forward(hr)
    lr_122 = lr_122[0]  # full_forward adds a batch dim
    hr_out = hr_out[0]

    # center-crop 122 -> 121
    lr = lr_122[:, :TARGET_LR_SIZE, :TARGET_LR_SIZE]
    return lr, hr_out
