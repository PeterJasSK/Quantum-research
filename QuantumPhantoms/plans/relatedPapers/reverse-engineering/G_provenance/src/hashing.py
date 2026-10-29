"""Canonical hashes for the provenance receipt (AC-1). qiskit-free: shared.seedhash / shared.volumes only.

voxel_sha256 is taken over the int16 (z, y, x) array in the LPS frame plus its grid, so the NIfTI
and the DICOM series written from it hash identically.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from shared import LETTERS, RE_ROOT, SHARED
from shared.seedhash import canonical_json, code_hash, hash_json, sha256_bytes
from shared.volumes import read_volume

PRODUCERS = "ABCDEF"
ROUND = 4  # mm; DICOM decimal strings and NIfTI floats agree to well below this


def grid_of(meta: dict) -> dict:
    """{shape, spacing_mm_xyz, origin_mm_lps} with a fixed rounding, from a read_volume meta."""
    shape = meta.get("shape") or meta["size_xyz"]
    return {"shape": [int(v) for v in shape],
            "spacing_mm_xyz": [round(float(v), ROUND) for v in meta["spacing_mm_xyz"]],
            "origin_mm_lps": [round(float(v), ROUND) for v in meta["origin_mm_lps"]]}


def _int16_bytes(array_zyx: np.ndarray) -> bytes:
    return np.ascontiguousarray(array_zyx, dtype="<i2").tobytes()


def voxel_sha256(array_zyx: np.ndarray, meta: dict) -> str:
    head = canonical_json({**grid_of(meta), "dtype": "int16"})
    return sha256_bytes(head + _int16_bytes(array_zyx))


def slice_sha256s(array_zyx: np.ndarray) -> list[str]:
    return [sha256_bytes(_int16_bytes(s)) for s in array_zyx]


def voxel_hashes_of_file(path: str | Path) -> tuple[str, list[str], dict]:
    arr, meta = read_volume(path)
    return voxel_sha256(arr, meta), slice_sha256s(arr), grid_of(meta)


def producer_code_hashes(letters: str = PRODUCERS, base: Path = RE_ROOT) -> dict[str, str]:
    """{letter: code_hash([letter dir, shared])} for every producing letter folder that exists."""
    out = {}
    for letter in letters:
        folder = base / LETTERS[letter]
        if folder.is_dir():
            out[letter] = code_hash([folder, SHARED], base=base)
    return out


def commit_code_hash(code_hashes: dict[str, str]) -> str:
    return hash_json(code_hashes)
