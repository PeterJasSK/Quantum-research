#!/usr/bin/env python3
"""Plan-8 offline gate (AC-3): manual check, no test suite (project directive).

Runs standalone without Mininet/OVS/root -- imports only `hash_core`/`types`
plus the dependency-free `testbed.topology.fabric` model. Mirrors
`testbed/attacker/collision_check.py`'s structure. Non-zero exit means one of:
  1. weak-PRNG salt (identical fabric-wide) does NOT polarize the k=4
     fat-tree's link load (the honest-mechanism claim would be false);
  2. csprng/qrng (independent per-switch salt) do NOT spread evenly;
  3. the single-switch control shows prng and csprng spreading differently
     (the false-claim guard from D8-seed fact 1 -- a single stage must
     always be uniform regardless of salt entropy).

This is what stops the `/load-balancing` page lying.
"""
from __future__ import annotations

import sys

sys.path.insert(0, __file__.rsplit("/testbed/", 1)[0])

from testbed.hash_core import ecmp_link  # noqa: E402
from testbed.metrics.fairness import jains_index, polarization_index  # noqa: E402
from testbed.salt.sources import salt_source  # noqa: E402
from testbed.topology.fabric import build_fattree, fabric_salts, link_load  # noqa: E402
from testbed.types import FiveTuple  # noqa: E402

_K = 4
_JAINS_EVEN_THRESHOLD = 0.95
_JAINS_POLARIZED_CEILING = 0.85
_POLARIZATION_EVEN_CEILING = 1.3
_POLARIZATION_FLOOR = 1.5


def _uniform_flow_set(fabric) -> list[FiveTuple]:
    flows = []
    for src in fabric.hosts:
        for dst in fabric.hosts:
            if src == dst:
                continue
            flows.append(
                FiveTuple(
                    src_ip=fabric.host_to_ip[src],
                    dst_ip=fabric.host_to_ip[dst],
                    src_port=40000,
                    dst_port=80,
                    proto=6,
                )
            )
    return flows


def _check_prng_polarizes() -> bool:
    fabric = build_fattree(_K)
    flows = _uniform_flow_set(fabric)
    ok = True
    for _ in range(3):  # deterministic, no passing seed (OQ8-2) -- every run must fail the bar
        salts = fabric_salts("prng", fabric)
        loads = link_load(fabric, salts, flows)
        jains = jains_index(loads)
        polarization = polarization_index(loads)
        if jains > _JAINS_POLARIZED_CEILING or polarization < _POLARIZATION_FLOOR:
            print(
                f"FAIL: prng did not polarize (jains={jains:.4f}, polarization={polarization:.4f})",
                file=sys.stderr,
            )
            ok = False
    if ok:
        print(f"PASS: prng polarizes on every run (last: jains={jains:.4f}, polarization={polarization:.4f})")
    return ok


def _check_csprng_qrng_even() -> bool:
    fabric = build_fattree(_K)
    flows = _uniform_flow_set(fabric)
    ok = True
    for kind in ("csprng", "qrng"):
        try:
            salts = fabric_salts(kind, fabric)
        except (RuntimeError, OSError) as exc:
            if kind == "qrng":
                # No QEAAS_API_KEY / no network in this environment -- qrng is
                # the null-result twin of csprng (epic s3.2); csprng alone
                # already proves the mechanism. Skip, don't fail the gate.
                print(f"SKIP: qrng unavailable ({exc}) -- csprng already covers the mechanism")
                continue
            raise
        loads = link_load(fabric, salts, flows)
        jains = jains_index(loads)
        polarization = polarization_index(loads)
        if jains < _JAINS_EVEN_THRESHOLD or polarization > _POLARIZATION_EVEN_CEILING:
            print(
                f"FAIL: {kind} did not spread evenly (jains={jains:.4f}, polarization={polarization:.4f})",
                file=sys.stderr,
            )
            ok = False
        else:
            print(f"PASS: {kind} spreads evenly (jains={jains:.4f}, polarization={polarization:.4f})")
    return ok


def _check_single_switch_control() -> bool:
    """False-claim guard (D8-seed fact 1): one switch always spreads
    uniformly for *any* salt -- entropy quality is invisible at one stage."""
    fanout = 8
    flows = [
        FiveTuple(src_ip=f"10.0.0.{i % 250 + 1}", dst_ip="10.0.0.200", src_port=1000 + i, dst_port=80, proto=6)
        for i in range(2000)
    ]
    jains_by_kind = {}
    for kind in ("prng", "csprng"):
        salt = salt_source(kind).salt
        counts = [0] * fanout
        for ft in flows:
            counts[ecmp_link(ft, salt, fanout)] += 1
        jains_by_kind[kind] = jains_index(counts)
        if jains_by_kind[kind] < _JAINS_EVEN_THRESHOLD:
            print(
                f"FAIL: single-switch {kind} concentrated instead of spreading "
                f"(jains={jains_by_kind[kind]:.4f}) -- false-claim guard tripped",
                file=sys.stderr,
            )
            return False
    print(
        "PASS: single-switch control -- prng and csprng spread equally "
        f"(jains: prng={jains_by_kind['prng']:.4f}, csprng={jains_by_kind['csprng']:.4f})"
    )
    return True


def main() -> int:
    checks = (
        _check_prng_polarizes(),
        _check_csprng_qrng_even(),
        _check_single_switch_control(),
    )
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
