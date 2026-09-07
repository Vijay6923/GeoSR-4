"""Sanity check: split by tile, load one batch, print shapes/stats. Not a
formal unit test — run manually while the preprocessing pipeline is new."""

import sys
from torch.utils.data import DataLoader

sys.path.insert(0, ".")
from ml.datasets.sen2naip import SEN2NAIPCrossSensor, tile_disjoint_split

ROOT = "ml/datasets/raw/sen2naip/cross-sensor/extracted/cross-sensor"

splits = tile_disjoint_split(ROOT)
for name, rois in splits.items():
    print(f"{name}: {len(rois)} pairs")

train_ds = SEN2NAIPCrossSensor(splits["train"])
loader = DataLoader(train_ds, batch_size=4, shuffle=True)
batch = next(iter(loader))

print("lr batch:", batch["lr"].shape, batch["lr"].dtype, "min/max:", batch["lr"].min().item(), batch["lr"].max().item())
print("hr batch:", batch["hr"].shape, batch["hr"].dtype, "min/max:", batch["hr"].min().item(), batch["hr"].max().item())
print("roi_ids:", batch["roi_id"])
print("tile_ids:", batch["tile_id"])
