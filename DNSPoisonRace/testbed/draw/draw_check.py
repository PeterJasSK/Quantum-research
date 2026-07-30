#!/usr/bin/env python3
"""Offline correctness gate for `testbed/draw/` (project directive -- no
`pytest`). Mirrors the ECMP twin's `*_check.py` discipline (epic §3.6).

Network-free unless `QEAAS_API_KEY` is set (then the `qrng` check also runs).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from testbed import config  # noqa: E402
from testbed.draw import sources as sources_mod  # noqa: E402
from testbed.draw.qrng_client import QRNGUnavailable  # noqa: E402
from testbed.draw.sad_dns import sad_dns_leak  # noqa: E402
from testbed.draw.sources import draw_source  # noqa: E402
from testbed.types import Draw  # noqa: E402

_checks_run = 0
_checks_failed = 0


def _check(name: str, condition: bool) -> None:
    global _checks_run, _checks_failed
    _checks_run += 1
    if condition:
        print(f"PASS  {name}")
    else:
        _checks_failed += 1
        print(f"FAIL  {name}")


def main() -> int:
    offline_kinds = ("fixed", "prng", "csprng")
    draws: dict[str, Draw] = {kind: draw_source(kind) for kind in offline_kinds}

    for kind, draw in draws.items():
        _check(f"{kind}: shape is Draw", isinstance(draw, Draw))
        _check(f"{kind}: provenance.kind matches", draw.provenance.kind == kind)
        _check(f"{kind}: provenance.detail is non-empty", bool(draw.provenance.detail))

    # Reset the module-level PRNG state to simulate two fresh processes
    # reseeding on the same PRNG_SEED (manual-verification step 4).
    def _reset_prng_state() -> None:
        sources_mod._prng_rng = None
        sources_mod._prng_seed = None
        sources_mod._prng_draw_index = 0

    _reset_prng_state()
    first = draw_source("prng")
    _reset_prng_state()
    second = draw_source("prng")
    _check("prng: reproducible after reseed", first.to_dict() == second.to_dict())

    _check(
        "fixed: port pinned to config.FIXED_PORT",
        draws["fixed"].port == config.FIXED_PORT,
    )

    _check("sad_dns_leak(16, 4) == 12", sad_dns_leak(16, 4) == 12)
    _check("sad_dns_leak(8, 20) == 0 (clamped)", sad_dns_leak(8, 20) == 0)

    if config.QEAAS_API_KEY:
        try:
            qrng_draw = draw_source("qrng")
        except QRNGUnavailable as exc:
            _check(f"qrng: Q-EaaS unavailable ({exc})", False)
        else:
            _check("qrng: shape is Draw", isinstance(qrng_draw, Draw))
            _check("qrng: provenance.kind matches", qrng_draw.provenance.kind == "qrng")
            _check(
                "qrng: provenance.detail['receipt'] present",
                bool(qrng_draw.provenance.detail.get("receipt")),
            )
            print(
                f"note  qrng request_id={qrng_draw.provenance.detail.get('request_id')} "
                f"entropy_epoch={qrng_draw.provenance.detail.get('entropy_epoch')} "
                f"receipt={qrng_draw.provenance.detail.get('receipt')}"
            )
    else:
        print("note  qrng check skipped -- QEAAS_API_KEY unset, no network attempted")

    print(f"\n{_checks_run - _checks_failed}/{_checks_run} checks passed")
    if _checks_failed:
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
