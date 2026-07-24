"""AC-2 knowledge-level entry point (frozen -- P5 imports `resolve_salt`
verbatim). Resolves the salt the crafter will use for each level and reports
the reconstruction cost (the Exp 5 anchor)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from testbed.config import N_LINKS, SALT_SIZE
from testbed.types import FiveTuple

from .oracle import PlacementOracle
from .reconstruct import SeedBruteForcer

KnowledgeLevel = Literal["full", "partial", "blind"]


@dataclass(frozen=True)
class Reconstruction:
    level: KnowledgeLevel
    salt: bytes | None
    attempts: int
    elapsed_seconds: float
    recovered_seed: int | None


def resolve_salt(
    level: KnowledgeLevel,
    *,
    known_salt: bytes | None = None,
    oracle: PlacementOracle | None = None,
    probes: list[FiveTuple] | None = None,
    seed_space_bits: int = 32,
    draw_window: int = 1,
    salt_size: int = SALT_SIZE,
    n_links: int = N_LINKS,
) -> Reconstruction:
    """Resolve the salt the crafter will use under `level`.

    - **full** -- `known_salt` returned verbatim, `attempts=0`.
    - **partial** -- brute-forces `seed_space_bits` seeds (+ `draw_window`
      draw indices per seed), validating each candidate against `oracle` on
      `probes`.
    - **blind** -- `salt=None`; the traffic layer falls back to random tuples.
    """
    if level == "full":
        if known_salt is None:
            raise ValueError("full knowledge level requires known_salt")
        return Reconstruction(
            level="full", salt=known_salt, attempts=0, elapsed_seconds=0.0, recovered_seed=None
        )

    if level == "blind":
        return Reconstruction(
            level="blind", salt=None, attempts=0, elapsed_seconds=0.0, recovered_seed=None
        )

    if level == "partial":
        if oracle is None or not probes:
            raise ValueError("partial knowledge level requires an oracle and probes")
        forcer = SeedBruteForcer(
            seed_space_bits=seed_space_bits,
            draw_window=draw_window,
            salt_size=salt_size,
            n_links=n_links,
        )
        result = forcer.search(oracle, probes)
        return Reconstruction(
            level="partial",
            salt=result.salt,
            attempts=result.attempts,
            elapsed_seconds=result.elapsed_seconds,
            recovered_seed=result.seed,
        )

    raise ValueError(f"unknown knowledge level: {level!r}")
