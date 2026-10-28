"""Seed and hash utilities (no qiskit import: E/F/G/H stay qiskit-free).

`derive_seed` / `rng` are the single sanctioned way to seed any PRNG from C's extracted seed:
    gen = rng(certificate["extracted_seed_hex"], "E.growth")
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Iterable

import numpy as np

from shared import RE_ROOT


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(obj) -> bytes:
    """Sorted keys, compact separators, UTF-8. The byte form every hash and signature is taken over."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def hash_json(obj: dict, exclude: Iterable[str] = ()) -> str:
    excl = set(exclude)
    return sha256_bytes(canonical_json({k: v for k, v in obj.items() if k not in excl}))


def _py_files(paths: Iterable[str | Path]) -> list[Path]:
    out = []
    for p in map(Path, paths):
        p = p.resolve()
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out.extend(f for f in p.rglob("*.py") if "__pycache__" not in f.parts)
    return sorted(set(out))


def code_hash(paths: Iterable[str | Path], base: str | Path = RE_ROOT) -> str:
    """Tree hash over sorted (relative path, content) of the .py files under `paths`.

    Paths are taken relative to `base` (the reverse-engineering root), so the hash is identical
    in every worktree checkout.
    """
    base = Path(base).resolve()
    h = hashlib.sha256()
    for f in _py_files(paths):
        try:
            rel = f.relative_to(base).as_posix()
        except ValueError:
            rel = f.name
        h.update(rel.encode("utf-8") + b"\0")
        h.update(hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()


def git_state(path: str | Path = RE_ROOT) -> dict | None:
    """{commit, dirty} for the repo containing `path`; dirty is scoped to `path` only."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True,
                                text=True, check=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain", "--", "."], cwd=path,
                                capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return {"commit": commit, "dirty": bool(status.strip())}


def derive_seed(seed_hex: str, label: str) -> int:
    """uint64 = first 8 bytes (big-endian) of sha256(seed || label)."""
    digest = hashlib.sha256(bytes.fromhex(seed_hex) + label.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def rng(seed_hex: str, label: str) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(derive_seed(seed_hex, label)))
