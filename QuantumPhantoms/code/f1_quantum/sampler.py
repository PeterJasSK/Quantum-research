"""F1 Sampler seam — the one swappable interface (epic §3, plan §4, AC-7).

`Sampler.draw(rulebook) -> list[TumorParams]` is the contract F2/F3/F4 consume. Two
interchangeable implementations ship here:

  * PRNGSampler  — classical numpy baseline (deterministic given a seed).
  * QRNGSampler  — the quantum pipeline (circuit -> run -> decode) + a CHSH certificate.

Both return byte-identical `TumorParams` shapes, so swapping them changes only
provenance — F2 cannot tell which produced the cohort (that transparency is the point).
Each sampler also exposes `last_run: QuantumRun` after `draw()` for run.py to persist.

Mirrors the injectable-client contract of
THESIS/CriticalQuantumLife/code/closed_loop.py:109-125 (branch on sim vs real source).
"""

from __future__ import annotations

import math
from typing import Protocol

import numpy as np

from f1_quantum.backend import flatten_counts, run_counts
from f1_quantum.certify import CHSH_SETTINGS, chsh_value
from f1_quantum.circuit import (
    build_chsh_circuits,
    build_sibling_pair_circuit,
    build_tumor_circuit,
)
from common.datamodel import LOBES, MARGINS, TYPES, QuantumRun, TumorParams
from f1_quantum.decode import decode_memory
from f1_quantum.lineage import DEFAULT_THETA_MUT, decode_pairs
from f1_quantum.rulebook import Rulebook, angles_from_rulebook


class Sampler(Protocol):
    def draw(self, rulebook: Rulebook) -> list[TumorParams]: ...


class PRNGSampler:
    """Classical baseline: draws the cohort straight from the rulebook distributions.

    No circuit, no Bell test — `last_run.chsh_value` is NaN with a classical label.
    This is the "anyone could have chosen the seed" null the quantum claim improves on.
    """

    def __init__(self, n_tiles: int = 12, n_pairs: int = 2, seed: int = 0):
        self.n_tiles = n_tiles
        self.n_pairs = n_pairs
        self.rng = np.random.default_rng(seed)
        self.last_run: QuantumRun | None = None

    def _draw_one(self, rb: Rulebook):
        labels = rb.size_labels()
        si = self.rng.choice(len(labels), p=rb.size_probs())
        size_mm = rb.size_mm()[si]
        t = self.rng.choice(len(TYPES), p=list(rb.type_given_size[labels[si]]))
        nodule_type = TYPES[t]
        m = self.rng.choice(len(MARGINS), p=list(rb.margin_given_type[nodule_type]))
        lobe = self.rng.choice(LOBES, p=[rb.lobe_freqs[l] for l in LOBES])
        return size_mm, nodule_type, MARGINS[m], str(lobe)

    def draw(self, rulebook: Rulebook) -> list[TumorParams]:
        tiles: list[TumorParams] = []
        shot = 0
        n_indep = self.n_tiles - 2 * self.n_pairs
        for _ in range(n_indep):
            s, ty, mg, lb = self._draw_one(rulebook)
            tiles.append(TumorParams(s, ty, mg, lb, f"tile{shot}", 0, shot))
            shot += 1
        for _ in range(self.n_pairs):
            s, ty, mg, lb = self._draw_one(rulebook)
            lineage = f"pair{shot}"
            tiles.append(TumorParams(s, ty, mg, lb, lineage, 0, shot))
            # daughter: classical copy with a small independent re-draw ("mutation")
            if self.rng.random() < 0.2:
                s, ty, mg, lb = self._draw_one(rulebook)
            tiles.append(TumorParams(s, ty, mg, lb, lineage, 1, shot))
            shot += 1
        self.last_run = QuantumRun(
            backend_name="prng(classical)",
            job_id="",
            chsh_value=float("nan"),
            chsh_settings={},
            raw_bits=[],
            shot_indices=list(range(shot)),
        )
        return tiles


class QRNGSampler:
    """Quantum pipeline: encode rulebook -> run -> decode, + a job-level CHSH certificate.

    `backend` is None for Aer (the only path the implementer runs) or a live IBM backend
    object (human-run). Exposes the decoded cohort and sets `last_run` to the QuantumRun.
    """

    def __init__(
        self,
        n_tiles: int = 12,
        n_pairs: int = 2,
        shots: int = 4096,
        chsh_shots: int = 4096,
        backend=None,
        theta_mut: float = DEFAULT_THETA_MUT,
    ):
        self.n_tiles = n_tiles
        self.n_pairs = n_pairs
        self.shots = shots
        self.chsh_shots = chsh_shots
        self.backend = backend
        self.theta_mut = theta_mut
        self.last_run: QuantumRun | None = None

    def draw(self, rulebook: Rulebook) -> list[TumorParams]:
        angles = angles_from_rulebook(rulebook)
        n_indep = self.n_tiles - 2 * self.n_pairs
        if n_indep < 0:
            raise ValueError("n_pairs too large for n_tiles")

        tiles: list[TumorParams] = []
        raw_bits: list[str] = []

        # Independent single nodules: one shot per tile.
        if n_indep > 0:
            counts = run_counts(build_tumor_circuit(angles), n_indep, self.backend)
            words = flatten_counts(counts)[:n_indep]
            raw_bits.extend(words)
            tiles.extend(
                decode_memory(
                    words, rulebook,
                    generation=0, shot_start=0, lineage_prefix="tile", n_qubits=9,
                )
            )

        # Sibling pairs: one shot per pair, decoded to parent + daughter.
        if self.n_pairs > 0:
            sp_counts = run_counts(
                build_sibling_pair_circuit(angles, self.theta_mut),
                self.n_pairs, self.backend,
            )
            raw_bits.extend(flatten_counts(sp_counts)[: self.n_pairs])
            tiles.extend(
                decode_pairs(
                    sp_counts, rulebook,
                    n_pairs=self.n_pairs, shot_start=n_indep, lineage_prefix="pair",
                )
            )

        # CHSH certificate: 4 setting circuits, one job-level S.
        chsh_circuits = build_chsh_circuits()
        counts_by_pair = {
            pair: run_counts(qc, self.chsh_shots, self.backend)
            for pair, qc in chsh_circuits.items()
        }
        s = chsh_value(counts_by_pair)

        backend_name = "AerSimulator" if self.backend is None else self.backend.name
        self.last_run = QuantumRun(
            backend_name=backend_name,
            job_id="",  # Aer has none; the human captures the real job id on hardware.
            chsh_value=s,
            chsh_settings=dict(CHSH_SETTINGS),
            raw_bits=raw_bits,
            shot_indices=[t.shot_index for t in tiles],
        )
        return tiles
