"""Section C: certificate. The CHSH gate on the roll -> certificate.json.

The four CHSH settings ride in section B's job: one job-level S, never a per-tumour value.
    S <= 2        fail: no seed, the draw is rejected and logged, no retry; the run stops
    S > 2, dry    "certification-ready, not certified (simulated)"
    S > 2, live   a job-level Bell violation on that backend, with Pironio's analytic min-entropy per round f(S) at the
                  point estimate (no finite-statistics bound, no hidden test rounds: not device-independent)
"""
from __future__ import annotations

import math

from common import runio
from common.runio import Ctx


def f_hmin(S: float) -> float:
    """Pironio et al. 2010: min-entropy per round f(S) = 1 - log2(1 + sqrt(2 - S^2 / 4)), 0 for S <= 2."""
    if S <= 2.0:
        return 0.0
    S = min(S, 2.0 * math.sqrt(2.0))
    return 1.0 - math.log2(1.0 + math.sqrt(max(0.0, 2.0 - S * S / 4.0)))


def run(ctx: Ctx) -> None:
    qr = runio.load_json(ctx.run_dir / "quantum_run.json")
    S = float(qr["chsh_value"])
    doc = {"chsh_S": S, "classical_bound": 2.0, "tsirelson_bound": 2.0 * math.sqrt(2.0), "backend": qr["backend_name"],
           "job_id": qr["job_id"], "scope": "job-level (one Bell test over 4 settings), not per tumour"}
    if S <= 2.0:
        doc |= {"passed": False, "status": "FAILED: S <= 2, draw rejected, no seed, no retry"}
    else:
        doc |= {"passed": True, "hmin_per_round_analytic": f_hmin(S),
                "status": (f"Bell violation on hardware: {qr['backend_name']}, job {qr['job_id']} (job-level; not "
                           f"device-independent)") if ctx.live else "certification-ready, not certified (simulated)"}
    runio.save_json(ctx.path("certificate.json"), doc)
    print(f"  CHSH S = {S:.3f} (bound 2) -> {doc['status']}")
    if S <= 2.0:
        raise SystemExit(7)
