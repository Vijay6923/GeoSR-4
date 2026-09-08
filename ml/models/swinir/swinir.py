"""Lightweight SwinIR (PRD section 27-30, Stage 3) -- windowed self-attention
SR transformer. window_size=11 divides our 121x121 LR input exactly
(121 = 11*11), so no input padding is needed for this dataset's patch size.
If this model is later run on arbitrary-size Sentinel-2 tiles (Phase 7
tiling), input padding to a window_size multiple will be needed then.

No clamp() inside forward -- see decisions.md D009 for why that kills
gradients during training.
"""

import torch
import torch.nn as nn


def window_partition(x, window_size):
    B, H, W, C = x.shape
    x = x.view(B, H // window_size, window_size, W // window_size, window_size, C)
    return x.permute(0, 1, 3, 2, 4, 5).contiguous().view(-1, window_size, window_size, C)


def window_reverse(windows, window_size, H, W):
    B = int(windows.shape[0] / (H * W / window_size / window_size))
    x = windows.view(B, H // window_size, W // window_size, window_size, window_size, -1)
    return x.permute(0, 1, 3, 2, 4, 5).contiguous().view(B, H, W, -1)


class WindowAttention(nn.Module):
    def __init__(self, dim, window_size, num_heads):
        super().__init__()
        self.window_size = window_size
        self.num_heads = num_heads
        head_dim = dim // num_heads
        self.scale = head_dim ** -0.5

        self.relative_position_bias_table = nn.Parameter(
            torch.zeros((2 * window_size - 1) * (2 * window_size - 1), num_heads)
        )
        coords = torch.stack(torch.meshgrid(
            torch.arange(window_size), torch.arange(window_size), indexing="ij"))
        coords_flatten = torch.flatten(coords, 1)
        relative_coords = coords_flatten[:, :, None] - coords_flatten[:, None, :]
        relative_coords = relative_coords.permute(1, 2, 0).contiguous()
        relative_coords[:, :, 0] += window_size - 1
        relative_coords[:, :, 1] += window_size - 1
        relative_coords[:, :, 0] *= 2 * window_size - 1
        self.register_buffer("relative_position_index", relative_coords.sum(-1))

        nn.init.trunc_normal_(self.relative_position_bias_table, std=0.02)

        self.qkv = nn.Linear(dim, dim * 3, bias=True)
        self.proj = nn.Linear(dim, dim)
        self.softmax = nn.Softmax(dim=-1)

    def forward(self, x, mask=None):
        B_, N, C = x.shape
        qkv = self.qkv(x).reshape(B_, N, 3, self.num_heads, C // self.num_heads).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]

        attn = (q * self.scale) @ k.transpose(-2, -1)

        bias = self.relative_position_bias_table[self.relative_position_index.view(-1)]
        bias = bias.view(self.window_size ** 2, self.window_size ** 2, -1).permute(2, 0, 1).contiguous()
        attn = attn + bias.unsqueeze(0)

        if mask is not None:
            nW = mask.shape[0]
            attn = attn.view(B_ // nW, nW, self.num_heads, N, N) + mask.unsqueeze(1).unsqueeze(0)
            attn = attn.view(-1, self.num_heads, N, N)

        attn = self.softmax(attn)
        x = (attn @ v).transpose(1, 2).reshape(B_, N, C)
        return self.proj(x)


class SwinTransformerLayer(nn.Module):
    def __init__(self, dim, num_heads, window_size, shift_size, mlp_ratio=2.0):
        super().__init__()
        self.window_size = window_size
        self.shift_size = shift_size

        self.norm1 = nn.LayerNorm(dim)
        self.attn = WindowAttention(dim, window_size, num_heads)
        self.norm2 = nn.LayerNorm(dim)
        hidden = int(dim * mlp_ratio)
        self.mlp = nn.Sequential(nn.Linear(dim, hidden), nn.GELU(), nn.Linear(hidden, dim))

    def _attn_mask(self, H, W, device):
        if self.shift_size == 0:
            return None
        img_mask = torch.zeros((1, H, W, 1), device=device)
        slices = (slice(0, -self.window_size), slice(-self.window_size, -self.shift_size), slice(-self.shift_size, None))
        cnt = 0
        for h in slices:
            for w in slices:
                img_mask[:, h, w, :] = cnt
                cnt += 1
        mask_windows = window_partition(img_mask, self.window_size).view(-1, self.window_size ** 2)
        attn_mask = mask_windows.unsqueeze(1) - mask_windows.unsqueeze(2)
        return attn_mask.masked_fill(attn_mask != 0, -100.0).masked_fill(attn_mask == 0, 0.0)

    def forward(self, x, H, W):
        B, L, C = x.shape
        shortcut = x
        x = self.norm1(x).view(B, H, W, C)

        shifted_x = torch.roll(x, shifts=(-self.shift_size, -self.shift_size), dims=(1, 2)) \
            if self.shift_size > 0 else x

        x_windows = window_partition(shifted_x, self.window_size).view(-1, self.window_size ** 2, C)
        attn_windows = self.attn(x_windows, mask=self._attn_mask(H, W, x.device))
        attn_windows = attn_windows.view(-1, self.window_size, self.window_size, C)
        shifted_x = window_reverse(attn_windows, self.window_size, H, W)

        x = torch.roll(shifted_x, shifts=(self.shift_size, self.shift_size), dims=(1, 2)) \
            if self.shift_size > 0 else shifted_x

        x = shortcut + x.view(B, H * W, C)
        return x + self.mlp(self.norm2(x))


class RSTB(nn.Module):
    """Residual Swin Transformer Block: stacked Swin layers + conv + residual."""

    def __init__(self, dim, depth, num_heads, window_size):
        super().__init__()
        self.layers = nn.ModuleList([
            SwinTransformerLayer(dim, num_heads, window_size, shift_size=0 if i % 2 == 0 else window_size // 2)
            for i in range(depth)
        ])
        self.conv = nn.Conv2d(dim, dim, 3, padding=1)

    def forward(self, x, H, W):
        shortcut = x
        for layer in self.layers:
            x = layer(x, H, W)
        B, L, C = x.shape
        x = self.conv(x.transpose(1, 2).view(B, C, H, W)).flatten(2).transpose(1, 2)
        return shortcut + x


class UpsampleBlock(nn.Module):
    def __init__(self, n_channels):
        super().__init__()
        self.conv = nn.Conv2d(n_channels, n_channels * 4, 3, padding=1)
        self.shuffle = nn.PixelShuffle(2)

    def forward(self, x):
        return self.shuffle(self.conv(x))


class SwinIR(nn.Module):
    def __init__(self, in_channels=4, out_channels=4, embed_dim=60,
                 depths=(2, 2, 2, 2), num_heads=6, window_size=11, scale_factor=4):
        super().__init__()
        assert scale_factor in (2, 4)
        self.window_size = window_size

        self.conv_first = nn.Conv2d(in_channels, embed_dim, 3, padding=1)
        self.rstb_blocks = nn.ModuleList([RSTB(embed_dim, d, num_heads, window_size) for d in depths])
        self.norm = nn.LayerNorm(embed_dim)
        self.conv_after_body = nn.Conv2d(embed_dim, embed_dim, 3, padding=1)

        n_upsamples = 1 if scale_factor == 2 else 2
        self.upsample = nn.Sequential(*[UpsampleBlock(embed_dim) for _ in range(n_upsamples)])
        self.conv_last = nn.Conv2d(embed_dim, out_channels, 3, padding=1)

    def forward(self, x):
        B, C, H, W = x.shape
        assert H % self.window_size == 0 and W % self.window_size == 0, \
            f"input size {(H, W)} must be divisible by window_size {self.window_size}"

        feat = self.conv_first(x)
        seq = feat.flatten(2).transpose(1, 2)

        res = seq
        for block in self.rstb_blocks:
            res = block(res, H, W)
        res = self.norm(res)
        res = self.conv_after_body(res.transpose(1, 2).view(B, -1, H, W))

        feat = self.upsample(feat + res)
        return self.conv_last(feat)
