#!/usr/bin/env python3
"""P3 spike (AC-1, AC-2): manual check, no test suite (project directive).

Runs standalone without scapy/root -- imports only `hash_core`/`types` plus
the dependency-free attacker modules. Non-zero exit means one of:
  1. a crafted "collision" doesn't actually hash to the target link (the
     crafter has drifted from the real hash);
  2. the blind fallback concentrates on one link instead of spreading
     ~uniformly;
  3. the partial attacker fails to recover a known seed.
"""
from __future__ import annotations

import sys

sys.path.insert(0, __file__.rsplit("/testbed/", 1)[0])

from testbed.attacker.collision import CollisionCrafter  # noqa: E402
from testbed.attacker.oracle import LocalOracle  # noqa: E402
from testbed.attacker.reconstruct import SeedBruteForcer  # noqa: E402
from testbed.attacker.flows import random_five_tuples  # noqa: E402
from testbed.config import N_LINKS  # noqa: E402
from testbed.types import FiveTuple  # noqa: E402

_SALT = b"collision-check-fixed-salt-0000000000000"
_TARGET_LINK = 1
_DST_IP = "10.0.0.2"
_CRAFT_COUNT = 500


def _check_collision_crafter() -> bool:
    crafter = CollisionCrafter(salt=_SALT, target_link=_TARGET_LINK, n_links=N_LINKS)
    tuples = crafter.craft(
        _CRAFT_COUNT,
        dst_ip=_DST_IP,
        proto=6,
        src_ip_pool=[f"10.0.0.{i}" for i in range(100, 200)],
        src_port_range=range(1024, 65535),
        dst_port=80,
    )
    if len(tuples) < _CRAFT_COUNT:
        print(f"FAIL: only crafted {len(tuples)}/{_CRAFT_COUNT} collisions", file=sys.stderr)
        return False
    for ft in tuples:
        if not crafter.is_collision(ft):
            print(f"FAIL: {ft} does not collide onto link {_TARGET_LINK}", file=sys.stderr)
            return False
    flows = {(ft.src_ip, ft.src_port) for ft in tuples}
    if len(flows) != len(tuples):
        print("FAIL: crafted tuples are not individually distinct", file=sys.stderr)
        return False
    print(f"PASS: {len(tuples)} crafted tuples all collide onto link {_TARGET_LINK}, all distinct")
    return True


def _check_blind_spread() -> bool:
    tuples = random_five_tuples(2000, dst_ip=_DST_IP)
    oracle = LocalOracle(_SALT, N_LINKS)
    counts = [0] * N_LINKS
    for ft in tuples:
        counts[oracle.link_for(ft)] += 1
    expected = len(tuples) / N_LINKS
    for link, count in enumerate(counts):
        if abs(count - expected) > expected:  # generous: within 2x expected
            print(f"FAIL: blind traffic concentrated on link {link}: {counts}", file=sys.stderr)
            return False
    print(f"PASS: blind traffic spreads ~uniformly across {N_LINKS} links: {counts}")
    return True


def _check_partial_reconstruction() -> bool:
    import random as random_module

    known_seed = 42
    salt_size = 32
    salt = random_module.Random(known_seed).randbytes(salt_size)
    oracle = LocalOracle(salt, N_LINKS)
    # 6 probes at N_LINKS=4 gives a false-positive rate of ~4^-6 per
    # candidate seed -- low enough that the 8-bit check space below
    # shouldn't collide before reaching the known seed.
    probes = [
        FiveTuple(src_ip="10.0.0.1", dst_ip=_DST_IP, src_port=port, dst_port=80, proto=6)
        for port in (50000, 50001, 50002, 50003, 50004, 50005)
    ]
    forcer = SeedBruteForcer(seed_space_bits=8, draw_window=1, salt_size=salt_size, n_links=N_LINKS)
    result = forcer.search(oracle, probes)
    if not result.found or result.seed != known_seed or result.salt != salt:
        print(f"FAIL: brute force did not recover seed {known_seed}: {result}", file=sys.stderr)
        return False
    print(
        f"PASS: recovered seed {result.seed} in {result.attempts} attempts, "
        f"{result.elapsed_seconds:.4f}s"
    )
    return True


def main() -> int:
    checks = (_check_collision_crafter(), _check_blind_spread(), _check_partial_reconstruction())
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
