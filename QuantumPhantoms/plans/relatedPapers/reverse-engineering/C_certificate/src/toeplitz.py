"""GF(2) Toeplitz two-universal extractor (target #4). qiskit-free.

T is out_len × m with T[i, j] = s[i + m − 1 − j], built from m + out_len − 1 seed bits s.
The seed is public (strong extractor): SHAKE-256 of the beacon pulse output value.
"""
from __future__ import annotations

import hashlib

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

TOEPLITZ_LABEL = b"C.toeplitz"
_ROW_CHUNK = 32


def expand_seed_bits(data: bytes, n: int) -> np.ndarray:
    """n pseudo-random bits (uint8 0/1) from SHAKE-256(data)."""
    raw = hashlib.shake_256(data).digest((n + 7) // 8)
    return np.unpackbits(np.frombuffer(raw, dtype=np.uint8))[:n]


def toeplitz_extract(bits: np.ndarray, out_len: int, seed_bits: np.ndarray) -> np.ndarray:
    """out = T · bits over GF(2). Row i of T is s[i : i + m] reversed, so out_i = s[i:i+m] · bits[::-1]."""
    bits = np.asarray(bits, dtype=np.uint8)
    m = bits.size
    if seed_bits.size != m + out_len - 1:
        raise ValueError(f"need {m + out_len - 1} seed bits, got {seed_bits.size}")
    windows = sliding_window_view(np.asarray(seed_bits, dtype=np.uint8), m)  # (out_len, m) view
    rev = bits[::-1].astype(np.int32)
    out = np.empty(out_len, dtype=np.uint8)
    for i in range(0, out_len, _ROW_CHUNK):
        out[i:i + _ROW_CHUNK] = (windows[i:i + _ROW_CHUNK].astype(np.int32) @ rev) % 2
    return out


def bits_to_hex(bits: np.ndarray) -> str:
    return np.packbits(np.asarray(bits, dtype=np.uint8)).tobytes().hex()
