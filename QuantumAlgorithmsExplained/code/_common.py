#!/usr/bin/env python3
"""
_common.py  —  shared helpers for the QuantumAlgorithmsExplained lessons.

Every lesson runs on a LOCAL simulator (qiskit's built-in StatevectorSampler),
so there is no cost, no queue and no IBM account needed. Results are perfectly
reproducible because we pin a random seed.

Each lesson calls run_and_save(...) which:
  1. runs the circuit on the local simulator,
  2. writes a JSON file to  ../result/<name>.json   (numbers + metadata),
  3. draws a bar chart to    ../graph/<name>.png    (measurement histogram),
  4. prints a short human-readable summary.

The .md explanation file for each lesson links to that JSON + PNG.
"""

import json
import os
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


def run_and_save(qc, name, title, shots=4096, note=""):
    """Run a circuit on the LOCAL ideal simulator, save result JSON + histogram
    PNG, print a summary.

    qc     : a QuantumCircuit that already contains measurements
    name   : file stem, e.g. "01_coin_flip"
    title  : human title used in the chart and JSON
    shots  : how many times to run/measure the circuit
    note   : optional one-line interpretation stored in the JSON
    """
    counts = _counts(qc, shots)
    return _emit(name, title, counts, shots, note,
                 backend="qiskit StatevectorSampler (local, ideal, no noise)",
                 extra={"num_qubits": qc.num_qubits})


def run_live_and_save(qc, name, title, shots=4096, note="", backend_name=None):
    """Run a circuit on a REAL IBM Quantum computer (Open plan, free), then save
    result JSON + histogram PNG and print a summary — same outputs as
    run_and_save so the .md lessons render identically.

    Requires IBM credentials saved once (see ../../credentialsApi.py):
        QiskitRuntimeService.save_account(channel="ibm_quantum_platform",
                                          token="...", instance="...")

    qc           : a QuantumCircuit that already contains measurements
    name         : base file stem (e.g. "01_coin_flip"). Live output is saved as
                   "<name>_live_<backend>_<UTC timestamp>" so every run is kept
                   and never overwrites the clean sim files the lessons link.
    title        : human title used in the chart and JSON
    shots        : number of shots to request on hardware
    note         : optional one-line interpretation stored in the JSON
    backend_name : force a specific backend; if None, auto-pick the LEAST BUSY
                   operational real device you have access to (free Open plan).

    NOTE: real hardware has noise, so histograms will show extra states and the
    ideal 0%/100% peaks become slightly smeared — that difference is the whole
    point of running live.
    """
    # imported lazily so the local-only lessons don't need qiskit_ibm_runtime
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    service = QiskitRuntimeService()
    if backend_name:
        backend = service.backend(backend_name)
    else:
        # least busy real device you can access on the Open plan
        backend = service.least_busy(operational=True, simulator=False,
                                     min_num_qubits=qc.num_qubits)
    print(f"Live backend: {backend.name}  ({backend.num_qubits} qubits) — queueing ...")

    # transpile to the device's native gates + qubit layout (ISA circuit)
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    isa = pm.run(qc)

    sampler = Sampler(mode=backend)
    job = sampler.run([isa], shots=shots)
    print(f"  job {job.job_id()} submitted; waiting for result ...")
    result = job.result()

    creg = qc.cregs[0].name
    counts = getattr(result[0].data, creg).get_counts()

    # best-effort quantum-time metric (varies by runtime version)
    try:
        qseconds = float(job.metrics()["usage"]["quantum_seconds"])
    except Exception:
        qseconds = None

    # unique, timestamped stem so every live run is kept, never overwritten
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    stem = f"{name}_live_{backend.name}_{stamp}"

    return _emit(stem, title, counts, shots, note,
                 backend=f"IBM Quantum {backend.name} (real hardware, has noise)",
                 extra={"num_qubits": qc.num_qubits,
                        "base_name": name,
                        "job_id": job.job_id(),
                        "quantum_seconds": qseconds})
