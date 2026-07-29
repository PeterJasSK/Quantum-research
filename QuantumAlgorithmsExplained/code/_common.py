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


def run_live_and_save(qc, name, title, shots=4096, note="",
                      backend_name="QX emulator"):
    """Run a circuit on QUANTUM INSPIRE 2 (cloud), then save result JSON +
    histogram PNG and print a summary — same outputs as run_and_save so the
    .md lessons render identically.

    Requires a one-time login (no token to paste; OAuth browser flow):
        qi login                      # see ../../quantumCredentialsApi.py
    and the Qiskit plugin installed:
        pip install qiskit-quantuminspire

    qc           : a QuantumCircuit that already contains measurements
    name         : base file stem (e.g. "01_coin_flip"). Live output is saved as
                   "<name>_live_<backend>_<UTC timestamp>" so every run is kept
                   and never overwrites the clean sim files the lessons link.
    title        : human title used in the chart and JSON
    shots        : number of shots to request
    note         : optional one-line interpretation stored in the JSON
    backend_name : which QI backend to target:
                     "QX emulator" -> QI CLOUD simulator (no queue, safe default)
                     "Starmon-7"   -> superconducting REAL hardware (has noise)
                     "Spin-2+"     -> spin-qubit REAL hardware (has noise)

    NOTE: on real hardware (Starmon-7 / Spin-2+) noise adds extra states and
    smears the ideal 0%/100% peaks — that difference is the point of going live.
    Max 3 queued jobs per hardware backend on the free plan.
    """
    # imported lazily so the local-only lessons don't need the QI plugin
    from qiskit import transpile
    from qiskit_quantuminspire.qi_provider import QIProvider

    provider = QIProvider()
    backend = provider.get_backend(backend_name)
    print(f"QI backend: {backend_name} — transpiling + submitting ...")

    # transpile to the backend's native gate set / qubit layout
    isa = transpile(qc, backend)

    # if your qiskit-quantuminspire version rejects the shots kwarg, drop it
    # (the platform default is 1024 shots) and set shots below to match.
    job = backend.run(isa, shots=shots)
    result = job.result()
    counts = result.get_counts()

    # unique, timestamped stem so every live run is kept, never overwritten
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    stem = f"{name}_live_{backend_name.replace(' ', '_')}_{stamp}"

    return _emit(stem, title, counts, shots, note,
                 backend=f"Quantum Inspire 2 {backend_name} (cloud)",
                 extra={"num_qubits": qc.num_qubits,
                        "base_name": name})
