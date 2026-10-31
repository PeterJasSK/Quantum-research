"""F5 — seeding for the grown renderer: every PRNG draw is `rng(seed_hex, label)`.

The per-tile seeds are derived from the tile's certified-quantum shot bits (or the run name for a
PRNG run). Each shot carries only ~9 quantum bits, so these seeds are a replay key + provenance, not
a strong random seed (F5 plan §4). Geometry and appearance are separate streams (RE F seed split):
the same geometry seed always grows and shapes the same lesion.
"""
# copied from plans/relatedPapers/reverse-engineering/shared/seedhash.py @ 2609cbe (derive_seed, rng);
# added: tile_seeds.

from __future__ import annotations

import hashlib

import numpy as np


def derive_seed(seed_hex: str, label: str) -> int:
    """uint64 = first 8 bytes (big-endian) of sha256(seed || label)."""
    digest = hashlib.sha256(bytes.fromhex(seed_hex) + label.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def rng(seed_hex: str, label: str) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(derive_seed(seed_hex, label)))


def tile_seeds(run_key: str, shot_index: int, generation: int, raw_bits: list[str]) -> tuple[str, str, str]:
    """(seed_hex_geometry, seed_hex_appearance, morphology_source) for one tile.

    run_key is the job id (hardware) or the run dir name (Aer/PRNG). With no raw bits (PRNG run) the
    seeds are classical and morphology_source is "classical".
    """
    word = str(raw_bits[shot_index % len(raw_bits)]) if raw_bits else ""
    source = "quantum" if raw_bits else "classical"

    def h(tag: str) -> str:
        msg = f"{run_key}|{tag}|{shot_index}|{generation}|{word}".encode()
        return hashlib.sha256(msg).hexdigest()

    return h("geom"), h("app"), source
