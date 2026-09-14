#!/usr/bin/env python3
"""
_common.py  —  shared helpers for the QuantumAlgorithmsExplained lessons.

DEFAULT = LOCAL SIMULATOR. Every lesson calls run_and_save(...) which runs on
qiskit's built-in StatevectorSampler: no cost, no queue, no account, and
perfectly reproducible (we pin a random seed).

GO LIVE without editing any lesson file — just set an env var:
    QAE_LIVE=1 python 01_coin_flip.py
When QAE_LIVE is set, run_and_save automatically routes to REAL IBM Quantum
hardware and picks the MOST FREE machine (least pending jobs) for you via
QiskitRuntimeService.least_busy(...). Optional overrides:
    QAE_BACKEND=ibm_torino   # force a specific backend, skip auto-pick
    QAE_SHOTS=2048           # override shot count
    QAE_INSTANCE=...         # IBM Quantum instance/CRN if your account needs it

One-time IBM setup (saves a token to ~/.qiskit):
    from qiskit_ibm_runtime import QiskitRuntimeService
    QiskitRuntimeService.save_account(channel="ibm_quantum_platform",
                                      token="YOUR_TOKEN", overwrite=True)

Each run writes:
  1. a JSON file to  ../result/<name>.json   (numbers + metadata),
  2. a bar chart to  ../graph/<name>.png     (measurement histogram),
  3. a short human-readable summary to stdout.

The .md explanation file for each lesson links to that JSON + PNG.
"""

import json
import os
import sys
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")                     # no display needed, just write PNGs
import matplotlib.pyplot as plt

from qiskit.primitives import StatevectorSampler

# All lessons share one seed so every re-run gives the same numbers.
SEED = 1234

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT_DIR = os.path.join(HERE, "..", "result")
GRAPH_DIR = os.path.join(HERE, "..", "graph")


def _counts(qc, shots):
    """Sample the circuit on the local statevector simulator."""
    sampler = StatevectorSampler(seed=SEED)
    result = sampler.run([qc], shots=shots).result()
    # the classical register is called "c" unless the circuit named it otherwise
    creg = qc.cregs[0].name
    data = getattr(result[0].data, creg)
    return data.get_counts()


def _draw_circuit(qc, name):
    """Print the ASCII circuit diagram and save it to ../result/<name>_circuit.txt."""
    diagram = qc.draw(output="text", fold=-1).__str__()
    os.makedirs(RESULT_DIR, exist_ok=True)
    txt_path = os.path.join(RESULT_DIR, name + "_circuit.txt")
    with open(txt_path, "w") as f:
        f.write(diagram + "\n")
    print("\n--- circuit ---")
    print(diagram)
    print(f"  circuit -> {os.path.relpath(txt_path, HERE)}")


def _emit(name, title, counts, shots, note, backend, extra=None):
    """Write result JSON + histogram PNG and print a summary. Shared by the
    local and the live-hardware runners."""
    total = sum(counts.values())
    ordered = dict(sorted(counts.items()))
    probs = {k: v / total for k, v in ordered.items()}

    os.makedirs(RESULT_DIR, exist_ok=True)
    os.makedirs(GRAPH_DIR, exist_ok=True)

    payload = {
        "algorithm": title,
        "file": name,
        "backend": backend,
        "seed": SEED,
        "shots": shots,
        "num_qubits": None,     # filled by caller via `extra` if wanted
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "note": note,
        "counts": ordered,
        "probabilities": {k: round(v, 5) for k, v in probs.items()},
    }
    if extra:
        payload.update(extra)
    json_path = os.path.join(RESULT_DIR, name + ".json")
    with open(json_path, "w") as f:
        json.dump(payload, f, indent=2)

    # ---- histogram ----------------------------------------------------
    labels = list(ordered.keys())
    values = list(ordered.values())
    plt.figure(figsize=(max(5, 0.6 * len(labels) + 2), 4))
    bars = plt.bar(labels, values, color="#4C72B0")
    for b, v in zip(bars, values):
        plt.text(b.get_x() + b.get_width() / 2, v, f"{v/total:.2%}",
                 ha="center", va="bottom", fontsize=8)
    plt.title(title)
    plt.xlabel("measured bitstring")
    plt.ylabel(f"counts (of {shots} shots)")
    plt.xticks(rotation=45 if len(labels) > 4 else 0, ha="right" if len(labels) > 4 else "center")
    plt.tight_layout()
    png_path = os.path.join(GRAPH_DIR, name + ".png")
    plt.savefig(png_path, dpi=110)
    plt.close()

    # ---- console summary ---------------------------------------------
    print(f"\n=== {title} ===")
    for k in labels:
        print(f"  {k} : {counts[k]:>6}  ({probs[k]:6.2%})")
    if note:
        print(f"  note: {note}")
    print(f"  backend: {backend}")
    print(f"  result -> {os.path.relpath(json_path, HERE)}")
    print(f"  graph  -> {os.path.relpath(png_path, HERE)}")
    return counts


def _live_requested():
    """True when the caller asked to go live (env var or CLI flag)."""
    if os.environ.get("QAE_LIVE", "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    return "--live" in sys.argv


def run_and_save(qc, name, title, shots=4096, note=""):
    """Run a circuit and save result JSON + histogram PNG + summary.

    DEFAULT: LOCAL ideal simulator (free, offline, reproducible).
    If QAE_LIVE=1 (or `--live` on the command line) is set, this transparently
    routes to REAL IBM Quantum hardware and picks the MOST FREE machine — the
    lesson files do not change at all.

    qc     : a QuantumCircuit that already contains measurements
    name   : file stem, e.g. "01_coin_flip"
    title  : human title used in the chart and JSON
    shots  : how many times to run/measure the circuit
    note   : optional one-line interpretation stored in the JSON
    """
    if _live_requested():
        env_shots = os.environ.get("QAE_SHOTS", "").strip()
        if env_shots:
            shots = int(env_shots)
        return run_live_and_save(qc, name, title, shots=shots, note=note)

    _draw_circuit(qc, name)
    counts = _counts(qc, shots)
    return _emit(name, title, counts, shots, note,
                 backend="qiskit StatevectorSampler (local, ideal, no noise)",
                 extra={"num_qubits": qc.num_qubits})


def _pick_least_busy_backend(service, min_qubits):
    """Return the MOST FREE operational IBM Quantum hardware backend (fewest
    pending jobs). Honors QAE_BACKEND to force a specific machine."""
    forced = os.environ.get("QAE_BACKEND", "").strip()
    if forced:
        backend = service.backend(forced)
        print(f"IBM backend forced via QAE_BACKEND: {backend.name}")
        return backend

    backend = service.least_busy(operational=True, simulator=False,
                                 min_num_qubits=min_qubits)
    try:
        pending = backend.status().pending_jobs
        print(f"IBM least-busy backend: {backend.name} "
              f"({backend.num_qubits} qubits, {pending} jobs queued)")
    except Exception:
        print(f"IBM least-busy backend: {backend.name}")
    return backend


def run_live_and_save(qc, name, title, shots=4096, note=""):
    """Run a circuit on REAL IBM Quantum hardware, auto-selecting the MOST FREE
    (least-busy) machine, then save result JSON + histogram PNG + summary —
    same outputs as run_and_save so the .md lessons render identically.

    One-time account setup (token saved to ~/.qiskit, no re-paste):
        from qiskit_ibm_runtime import QiskitRuntimeService
        QiskitRuntimeService.save_account(channel="ibm_quantum_platform",
                                          token="YOUR_TOKEN", overwrite=True)

    Env overrides:
        QAE_BACKEND   force a specific backend (skip least-busy auto-pick)
        QAE_INSTANCE  IBM instance / CRN if your account needs an explicit one

    Live output is saved as "<name>_live_<backend>_<UTC timestamp>" so every run
    is kept and never overwrites the clean sim files the lessons link.

    NOTE: real hardware has noise — it adds extra states and smears the ideal
    0%/100% peaks. That difference is the whole point of going live.
    """
    # imported lazily so the local-only lessons don't need the IBM plugin
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    instance = os.environ.get("QAE_INSTANCE", "").strip() or None
    service = QiskitRuntimeService(instance=instance) if instance \
        else QiskitRuntimeService()

    backend = _pick_least_busy_backend(service, min_qubits=qc.num_qubits)
    print(f"Transpiling for {backend.name} + submitting {shots} shots ...")

    # transpile to the backend's native gate set / qubit layout (ISA circuit)
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    isa = pm.run(qc)

    sampler = SamplerV2(mode=backend)
    job = sampler.run([isa], shots=shots)
    print(f"  job id: {job.job_id()} — waiting for result ...")
    result = job.result()

    # classical register keeps its name through transpilation
    creg = qc.cregs[0].name
    counts = getattr(result[0].data, creg).get_counts()

    # unique, timestamped stem so every live run is kept, never overwritten
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    stem = f"{name}_live_{backend.name}_{stamp}"

    _draw_circuit(qc, stem)
    return _emit(stem, title, counts, shots, note,
                 backend=f"IBM Quantum {backend.name} (real hardware, cloud)",
                 extra={"num_qubits": qc.num_qubits,
                        "base_name": name,
                        "ibm_backend": backend.name})
