"""F1 backend seam — AerSimulator (dev) / ibm_heron (human-run demo) (plan §4, AC-3).

Mirrors THESIS/CriticalQuantumLife/proof_of_concept/quantum_life.py:80-104 and
THESIS/NPQuantumAdvantage/proof_of_concept/quantum_grover.py:106-120.

HARD RULE (plan header): the implementer never submits a hardware job. `--backend aer`
(the default, `get_backend("")` -> None) is the only path exercised during
development/verification. The `ibm`/`auto` path is wired for Peter to run himself; it
imports credentials only through a pre-existing saved account (`QiskitRuntimeService()`
with no args) — no token is ever read, embedded, or committed here.
"""

from __future__ import annotations

import functools
from typing import Any

# Unbuffered progress on long (human-run) hardware jobs — matches the repo idiom.
print = functools.partial(print, flush=True)


def get_backend(name: str, *, min_qubits: int = 0) -> Any:
    """Resolve a backend. "" / "aer" -> None (Aer sim). "auto" -> least_busy. else named.

    Returns None for the simulator path; returns a live IBM backend object otherwise.
    Only ever called with a real backend name by the human (never by /implement-feature).
    """
    if name in ("", "aer", "sim"):
        return None
    from qiskit_ibm_runtime import QiskitRuntimeService

    service = QiskitRuntimeService()
    if name == "auto":
        backend = service.least_busy(
            operational=True, simulator=False, min_num_qubits=min_qubits
        )
    else:
        backend = service.backend(name)
    print(f"backend : {backend.name} ({backend.num_qubits} qubits)")
    return backend


def run_counts(qc, shots: int, backend: Any) -> dict[str, int]:
    """Counts for one circuit. backend is None -> Aer; else transpile + SamplerV2.

    All F1 circuits name their classical register `c`, so the V2 result is read via
    `result[0].data.c.get_counts()` uniformly.
    """
    if backend is None:
        from qiskit_aer import AerSimulator

        return AerSimulator().run(qc, shots=shots).result().get_counts()

    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import SamplerV2

    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    isa = pm.run(qc)
    result = SamplerV2(mode=backend).run([isa], shots=shots).result()
    return result[0].data.c.get_counts()


def flatten_counts(counts: dict[str, int]) -> list[str]:
    """Expand a counts dict into a flat list of per-shot bitstrings.

    Lets F1 treat each shot as one independent draw (one tile / one pair) without
    depending on a per-shot memory API. Order is by key; length == total shots.
    """
    out: list[str] = []
    for key, n in counts.items():
        out.extend([key] * int(n))
    return out
