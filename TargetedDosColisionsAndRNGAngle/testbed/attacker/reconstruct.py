"""AC-2 partial-knowledge attacker: brute-force the weak-PRNG seed space.

Mirrors `testbed.salt.sources._prng_source` exactly -- `random.Random(seed)
.randbytes(size)`, drawn sequentially per `draw_index` (OQ-2) -- and
validates each candidate against a `PlacementOracle` on a handful of probe
5-tuples. `elapsed_seconds`/`attempts` are the Exp 5 timing anchor P5 reads
(the epic's rotation-frequency curve), not debug output.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass

from testbed.config import N_LINKS, SALT_SIZE
from testbed.hash_core import ecmp_link
from testbed.types import FiveTuple

from .oracle import PlacementOracle


@dataclass(frozen=True)
class BruteForceResult:
    found: bool
    seed: int | None
    draw_index: int | None
    salt: bytes | None
    attempts: int
    elapsed_seconds: float


@dataclass(frozen=True)
class SeedBruteForcer:
    """Searches `2**seed_space_bits` seeds, each mirroring `_prng_source`'s
    sequential draws up to `draw_window` draw indices, validating candidate
    salts against `oracle` on `probes`."""

    seed_space_bits: int = 32
    draw_window: int = 1
    salt_size: int = SALT_SIZE
    n_links: int = N_LINKS

    def search(self, oracle: PlacementOracle, probes: list[FiveTuple]) -> BruteForceResult:
        if not probes:
            raise ValueError("search requires at least one probe 5-tuple")

        expected_links = [oracle.link_for(probe) for probe in probes]
        start = time.perf_counter()
        attempts = 0

        for seed in range(2**self.seed_space_bits):
            rng = random.Random(seed)
            for draw_index in range(self.draw_window):
                candidate_salt = rng.randbytes(self.salt_size)
                attempts += 1
                candidate_links = [
                    ecmp_link(probe, candidate_salt, self.n_links) for probe in probes
                ]
                if candidate_links == expected_links:
                    return BruteForceResult(
                        found=True,
                        seed=seed,
                        draw_index=draw_index,
                        salt=candidate_salt,
                        attempts=attempts,
                        elapsed_seconds=time.perf_counter() - start,
                    )

        return BruteForceResult(
            found=False,
            seed=None,
            draw_index=None,
            salt=None,
            attempts=attempts,
            elapsed_seconds=time.perf_counter() - start,
        )
