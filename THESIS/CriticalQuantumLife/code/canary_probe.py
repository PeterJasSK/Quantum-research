#!/usr/bin/env python3
"""Critical Quantum Life — F7: the Quantum Canary probe loop (AC-F7.1, AC-F7.5).

An entanglement-native, always-on QPU health probe. It runs the F0 closed-loop engine at
small W, one short circuit per cycle, and emits a per-cycle health record: the entanglement
witness margin above the classical null (the load-bearing signal), the surprise/anomaly
readout, the branching set-point sigma, the closed-minus-yoked adaptation gap, the avalanche
rate, and the reported chain-quality numbers. Its homeostasis IS the health signal — the
witness sagging below the null means the device can no longer make + inherit real entanglement,
a fault no gate-fidelity dashboard reports.

Runs on the quantum gate that already PASSED (F3): no unmet gate is required. Reuses, not
reimplements, the whole F0/F3 stack — witness, surprise, null band, branching sigma.

Scope (see plan §1 honest note): this monitors the ENTANGLEMENT-WITNESS heartbeat. Dynamic-
circuit health (mid-circuit measure / feed-forward / reset) needs machinery the F0 engine does
not have; that coverage is deferred to F8 (Sandpile). The probe exposes the `fault` hook so
that coverage can be added later without changing this loop.
"""
from __future__ import annotations

import functools
import math
from typing import Any, Callable

from qiskit import transpile
from qiskit_aer import AerSimulator

import closed_loop as cl
import fault_injection as fi
from criticality import collect_avalanches

print = functools.partial(print, flush=True)

WINDOW = 30              # rolling window (cycles) for adaptation gap + avalanche rate
K_BAND = 3.0            # analytic null band k/sqrt(shots) (matches F3 K_BAND)
MARGIN_ALERT_N = 3      # consecutive cycles of witness_margin < 0 before firing (AC-F7.5)
SURPRISE_ALERT_K = 3.0  # surprise > yoked_mean + k*yoked_std fires the anomaly alert (AC-F7.5)


class CanaryProbe:
    """One long-lived probe over a spare qubit chain. `fault` (an fi.Fault) may be set at any
    time to drive the Aer path with an injected fault; in production it stays None and the probe
    reads the backend's live calibration instead."""

    def __init__(self, width: int = 6, shots: int = 4096, seed: int = 100, nbins: int = 10,
                 mut_scale: float = cl.DEFAULT_MUT, death: str = "unitary",
                 interaction: str = "nn", delta: float | None = None,
                 gamma: float | None = None, backend: Any = None) -> None:
        import stage4_qalife as q4
        self.width = width
        self.shots = shots
        self.seed = seed
        self.nbins = nbins
        self.base_mut = mut_scale
        self.mut_scale = mut_scale          # closed arm adapts this contingently
        self.death = death
        self.interaction = interaction
        self.delta = q4.AGING_DELTA if delta is None else delta
        self.gamma = q4.DAMP_GAMMA if gamma is None else gamma
        self.backend = backend              # None = Aer (default); a hardware backend streams counts
        self.fault: fi.Fault | None = None  # coverage study sets this; None in production
        # rolling closed-arm state (mirrors F0's dist/recent/active_hist)
        self.t = 0
        self.dist: dict[str, float] = {}
        self.recent: list[float] = []
        self.active_hist: list[bool] = []
        self.rows: list[dict[str, Any]] = []
        self.closed_surprise: list[float] = []
        # rolling yoked-shadow state (non-contingent baseline)
        self.ydist: dict[str, float] = {}
        self.yoked_surprise: list[float] = []
        # alert bookkeeping
        self._below_run = 0
        self._sims: dict[int, AerSimulator] = {}

    # -- circuit execution -------------------------------------------------
    def _sim_for(self, nm: Any) -> AerSimulator:
        key = id(nm)
        if key not in self._sims:
            self._sims[key] = AerSimulator(method="density_matrix", noise_model=nm)
        return self._sims[key]

    def _run(self, qc: Any) -> dict[str, int]:
        if self.backend is not None:
            return cl.run_counts(qc, self.shots, self.backend)
        nm = fi.noise_model(self.fault) if self.fault else None
        sim = self._sim_for(nm)
        return sim.run(transpile(qc, sim), shots=self.shots).result().get_counts()

    def _witness(self, mut: float, repeat: int) -> tuple[float, float]:
        """Build + run one generation at mutation `mut`; return (witness_signal, surprise-key-signal)."""
        thetas = cl.draw_thetas(None, self.width, mut, repeat, [], self.seed)
        qc, geno = cl.build_generation(self.width, self.width, thetas, False, self.death,
                                       self.interaction, self.delta, self.gamma)
        counts = self._run(qc)
        joint, sep, _ = cl.witness_gen(counts, geno, self.shots)
        return joint - sep, joint - sep

    # -- one probe cycle ---------------------------------------------------
    def cycle(self) -> dict[str, Any]:
        """Run one closed cycle + one yoked-shadow cycle; return the health record (AC-F7.1)."""
        self.t += 1
        band = K_BAND / math.sqrt(max(1, self.shots))

        # closed (contingent) arm — the monitored organism
        signal, _ = self._witness(self.mut_scale, self.t)
        key = cl.outcome_key(signal, self.nbins)
        cl.update_running_dist(self.dist, key, cl.DECAY)
        surprise = cl.surprise_nll(self.dist, key, self.nbins)
        surprising = cl.is_surprising(surprise, self.recent)
        self.active_hist.append(surprising)
        sigma = cl.running_sigma(self.active_hist)
        self.recent.append(surprise)
        self.closed_surprise.append(surprise)
        self.rows.append({"surprise": surprise, "active": surprising, "sigma": sigma})
        # contingent feedback for the next cycle (F0 rule)
        self.mut_scale = (self.base_mut if surprising
                          else max(self.mut_scale * 0.7, cl.MUT_FLOOR))

        # yoked shadow — same engine, feedback DECOUPLED (mut fixed at base): the drift baseline
        ysignal, _ = self._witness(self.base_mut, self.t + 100_000)
        ykey = cl.outcome_key(ysignal, self.nbins)
        cl.update_running_dist(self.ydist, ykey, cl.DECAY)
        ysurprise = cl.surprise_nll(self.ydist, ykey, self.nbins)
        self.yoked_surprise.append(ysurprise)

        # derived metrics
        margin = signal - band
        cwin = self.closed_surprise[-WINDOW:]
        ywin = self.yoked_surprise[-WINDOW:]
        adaptation_gap = (sum(ywin) / len(ywin)) - (sum(cwin) / len(cwin))
        av = collect_avalanches(self.rows[-WINDOW:])
        avalanche_rate = len(av) / min(len(self.rows), WINDOW)

        alert = self._check_alerts(margin, surprise)
        return {
            "cycle": self.t,
            "witness_signal": signal,
            "null_band": band,
            "witness_margin": margin,
            "surprise": surprise,
            "sigma": sigma,
            "adaptation_gap": adaptation_gap,
            "avalanche_rate": avalanche_rate,
            "twoq_err": fi.chain_quality(self.fault)["twoq_err"],
            "readout_err": fi.chain_quality(self.fault)["readout_err"],
            "fault": (self.fault.id if self.fault and self.fault.kind != "none" else None),
            "alert": alert,
        }

    def _check_alerts(self, margin: float, surprise: float) -> dict[str, Any] | None:
        """AC-F7.5 alert rules: witness below the null band for N cycles, or a surprise spike
        above the yoked baseline by k*sigma."""
        self._below_run = self._below_run + 1 if margin < 0.0 else 0
        if self._below_run >= MARGIN_ALERT_N:
            return {"id": "entanglement_below_null",
                    "reason": f"witness_margin<0 for {self._below_run} cycles"}
        ywin = self.yoked_surprise[-WINDOW:]
        if len(ywin) >= 5:
            ymean = sum(ywin) / len(ywin)
            yvar = sum((v - ymean) ** 2 for v in ywin) / len(ywin)
            ystd = math.sqrt(yvar)
            if ystd > 0 and surprise > ymean + SURPRISE_ALERT_K * ystd:
                return {"id": "surprise_spike",
                        "reason": f"surprise {surprise:.2f} > yoked {ymean:.2f}+{SURPRISE_ALERT_K}σ"}
        return None

    # -- always-on driver --------------------------------------------------
    def run(self, cycles: int | None, on_record: Callable[[dict[str, Any]], None]) -> None:
        """Loop `cycles` times (None = forever) calling `on_record` with each health record."""
        i = 0
        while cycles is None or i < cycles:
            on_record(self.cycle())
            i += 1
