"""F4 QALifeSampler — the Mode-A loop behind the F1 `Sampler` seam (plan §4, AC-1/AC-6).

Third implementation of `f1_quantum.sampler.Sampler` (alongside PRNGSampler/QRNGSampler).
`draw(rulebook) -> list[TumorParams]` returns the evolved lineage in the exact shape F2/F3
already consume, so the render cannot tell an evolved cohort from a static one. After
`draw()`, `last_run` carries the job-level CHSH certificate + provenance (parity with F1)
and `generation_records` carries the per-generation entanglement witness.
"""

from __future__ import annotations

import math

from common.datamodel import GenerationRecord, QuantumRun, TumorParams
from f1_quantum.backend import run_counts
from f1_quantum.certify import CHSH_SETTINGS, chsh_value
from f1_quantum.circuit import build_chsh_circuits
from f1_quantum.lineage import DEFAULT_THETA_MUT
from f1_quantum.rulebook import Rulebook
from f4_qalife.loop import run_mode_a


class QALifeSampler:
    """Mode-A living-process sampler. Same contract as QRNGSampler; evolves the cohort."""

    def __init__(
        self,
        founders: int = 4,
        generations: int = 3,
        survivors: int = 1,
        offspring: int = 4,
        theta_mut: float = DEFAULT_THETA_MUT,
        phase: float = 0.0,
        shots: int = 4096,
        witness_shots: int = 4096,
        chsh_shots: int = 4096,
        backend=None,
    ):
        self.founders = founders
        self.generations = generations
        self.survivors = survivors
        self.offspring = offspring
        self.theta_mut = theta_mut
        self.phase = phase
        self.shots = shots
        self.witness_shots = witness_shots
        self.chsh_shots = chsh_shots
        self.backend = backend
        self.last_run: QuantumRun | None = None
        self.generation_records: list[GenerationRecord] = []

    def draw(self, rulebook: Rulebook) -> list[TumorParams]:
        cells, records, raw_bits = run_mode_a(
            rulebook,
            founders=self.founders,
            generations=self.generations,
            survivors=self.survivors,
            offspring=self.offspring,
            theta_mut=self.theta_mut,
            phase=self.phase,
            shots=self.shots,
            witness_shots=self.witness_shots,
            backend=self.backend,
        )
        self.generation_records = records

        # Job-level CHSH certificate — reused verbatim from F1 (provenance parity, AC-6).
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
            shot_indices=[t.shot_index for t in cells],
        )
        return cells
