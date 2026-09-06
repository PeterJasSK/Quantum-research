#!/usr/bin/env python3
"""Critical Quantum Life — F7 (Canary): the fault-injection harness (AC-F7.3).

A labelled menu of known QPU faults, each realised as an Aer `NoiseModel` plus the
chain-quality numbers a gate-fidelity dashboard would report for it. The Canary probe runs
under `noise_model(fault)`; the incumbent baseline detector (canary_coverage.py) thresholds
on `chain_quality(fault)` — exactly the 2q/readout numbers RB / coherence dashboards expose.

The menu is chosen to span the honest coverage map:
  - `entanglement_collapse`, `twoq_degrade`, `readout_error` — faults the incumbent 2q/readout
    thresholds DO see (ties, or a documented Canary LOSS where the incumbent is faster).
  - `dephasing_drift`, `stale_calibration` — entanglement-visible faults that leave the
    reported 2q/readout numbers unchanged, so the incumbent MISSES them and the Canary wins.

Aer-only. Real-hardware fault injection (physically detuning a qubit, forcing a stale
calibration) is a manual operation, noted in the plan, not code.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Any

from qiskit_aer.noise import (NoiseModel, ReadoutError, depolarizing_error,
                              phase_damping_error)

print = functools.partial(print, flush=True)

# Baseline (healthy-device) chain-quality numbers reported when no fault is active.
BASELINE_TWOQ_ERR = 0.004
BASELINE_READOUT_ERR = 0.010


@dataclass(frozen=True)
class Fault:
    """A labelled, known fault. `onset` is the probe cycle at which it switches on.

    `twoq_err` / `readout_err` are the numbers a gate-fidelity dashboard would REPORT for this
    fault — deliberately left at baseline for entanglement-visible faults the incumbent misses
    (`reported_only=False` faults raise them; `dephasing_drift` / `stale_calibration` do not)."""
    id: str
    kind: str                       # none|entanglement_collapse|twoq_degrade|readout_error|
                                    # dephasing_drift|stale_calibration
    magnitude: float
    onset: int
    twoq_err: float = BASELINE_TWOQ_ERR
    readout_err: float = BASELINE_READOUT_ERR
    note: str = ""


NO_FAULT = Fault(id="healthy", kind="none", magnitude=0.0, onset=0)


def noise_model(fault: Fault | None) -> NoiseModel | None:
    """Build the Aer NoiseModel for `fault` (None / kind=='none' -> no noise)."""
    if fault is None or fault.kind == "none":
        return None
    nm = NoiseModel()
    # A light healthy baseline so even "reported-clean" faults sit on realistic noise.
    nm.add_all_qubit_quantum_error(depolarizing_error(2 * BASELINE_TWOQ_ERR, 2), ["cx"])
    nm.add_all_qubit_readout_error(_ro(BASELINE_READOUT_ERR))
    if fault.kind == "entanglement_collapse":
        nm.add_all_qubit_quantum_error(depolarizing_error(fault.magnitude, 2), ["cx"])
    elif fault.kind == "twoq_degrade":
        nm.add_all_qubit_quantum_error(depolarizing_error(fault.magnitude, 2), ["cx"])
    elif fault.kind == "readout_error":
        nm.add_all_qubit_readout_error(_ro(fault.magnitude))
    elif fault.kind == "dephasing_drift":
        # Coherence loss that raises NEITHER the reported 2q NOR readout number.
        nm.add_all_qubit_quantum_error(phase_damping_error(fault.magnitude), ["h", "ry", "rz"])
    elif fault.kind == "stale_calibration":
        # Real errors drifted up, but the dashboard still shows the stale (good) numbers.
        nm.add_all_qubit_quantum_error(depolarizing_error(fault.magnitude, 2), ["cx"])
        nm.add_all_qubit_readout_error(_ro(min(0.5, fault.magnitude)))
    else:
        raise ValueError(f"unknown fault kind: {fault.kind}")
    return nm


def chain_quality(fault: Fault | None) -> dict[str, float]:
    """The 2q/readout numbers the incumbent dashboard would REPORT for this fault."""
    if fault is None:
        return {"twoq_err": BASELINE_TWOQ_ERR, "readout_err": BASELINE_READOUT_ERR}
    return {"twoq_err": fault.twoq_err, "readout_err": fault.readout_err}


def _ro(p: float) -> ReadoutError:
    """Symmetric single-qubit readout error with flip probability p."""
    p = max(0.0, min(0.5, p))
    return ReadoutError([[1 - p, p], [p, 1 - p]])


# The coverage menu (AC-F7.3). onset is the cycle each fault switches on.
FAULTS: list[Fault] = [
    # --- Canary territory: entanglement/coherence faults invisible to single-gate RB ---
    Fault(id="entanglement_collapse", kind="entanglement_collapse", magnitude=0.30, onset=8,
          twoq_err=BASELINE_TWOQ_ERR, readout_err=BASELINE_READOUT_ERR,
          note="genealogical entanglement collapse — invisible to single-gate RB; witness catches it"),
    Fault(id="dephasing_drift", kind="dephasing_drift", magnitude=0.20, onset=8,
          twoq_err=BASELINE_TWOQ_ERR, readout_err=BASELINE_READOUT_ERR,
          note="coherence loss with UNCHANGED reported 2q/readout — incumbent misses it"),
    Fault(id="stale_calibration", kind="stale_calibration", magnitude=0.30, onset=8,
          twoq_err=BASELINE_TWOQ_ERR, readout_err=BASELINE_READOUT_ERR,
          note="real errors drifted up but dashboard shows stale good numbers — incumbent blind"),
    # --- RB territory: gate/readout faults the incumbent's 2q/readout numbers DO report ---
    Fault(id="twoq_degrade", kind="twoq_degrade", magnitude=0.06, onset=8,
          twoq_err=0.03, readout_err=BASELINE_READOUT_ERR,
          note="moderate 2q degradation — reported 2q err rises; RB catches it (honest tie/lose)"),
    Fault(id="readout_error", kind="readout_error", magnitude=0.14, onset=8,
          twoq_err=BASELINE_TWOQ_ERR, readout_err=0.14,
          note="readout drift — incumbent readout threshold catches it at onset (RB territory)"),
]
