"""D-SCALE circuit families (AC-8): one plug-and-play interface, a registry and three budget presets per family.

    python -m dscale.families --list

Every family module exposes:
  NAME, CLAIM, WITNESS, HARDNESS            catalogue strings (plan §4)
  PRESETS = {40: {...}, 100: {...}, 120: {...}}   (Q2: all three versions)
  PARAM_GRID                                fixed sweep grid, hashed into scale_detail.json before any run
  region_request(budget, target) -> [allocation request]
  build(alloc, params, draw) -> [QuantumCircuit]       one job; metadata: layout, basis, root, control_arm
  clifford_twin(circuits) -> [QuantumCircuit]          same CZ skeleton, Clifford stand-ins
  witness(...) / run_cell(...)                         metrics + claim entries
  bp_circuits(alloc, params) -> [{name, qc, nodes, edges}]

Circuits are compact (qubit k of the circuit = physical qubit metadata["layout"][k]) and measure into one register.
`execute` runs one job in any mode: ideal | heron | pauli:<target> | twin:<target>.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import warnings
from functools import lru_cache

from qiskit import QuantumCircuit, qasm3, transpile
from qiskit_aer import AerSimulator

from dscale import pauli_noise as PN, targets as T, witness_scale as WS

FAMILIES = {"ghz-spine": "ghz_spine", "ch-qca": "ch_qca", "pmd-bank": "pmd_bank", "kicked-ising": "kicked_ising"}
RECIPES = {"composite": "spine + QCA + PMD on one chip with physical buffers (dscale.allocate.composite)"}
BUDGETS = (40, 100, 120)


def get(name: str):
    if name not in FAMILIES:
        raise SystemExit(f"unknown family {name!r}; choose from {', '.join(FAMILIES)}")
    return importlib.import_module(f"dscale.families.{FAMILIES[name]}")


# ---------------------------------------------------------------------------------------------- draws / seeds
DEFAULT_DRAW = {"tile_id": "cli", "size_mm": 12.0, "type": "solid", "margin": "lobulated",
                "seed_hex": hashlib.sha256(b"dscale-cli-default-draw").hexdigest()}


def default_draw() -> dict:
    return dict(DEFAULT_DRAW)


def sim_seed(seed_hex: str, label: str) -> int:
    from imaging.seedhash import derive_seed

    return derive_seed(seed_hex, label) % (2 ** 31)


# ---------------------------------------------------------------------------------------------- execution
def circuit_hash(qc: QuantumCircuit) -> str:
    """sha256 of the OpenQASM 3 text."""
    return hashlib.sha256(qasm3.dumps(qc).encode()).hexdigest()


@lru_cache(maxsize=2)
def _heron_sim(method: str) -> AerSimulator:
    return AerSimulator.from_backend(T.get("marrakesh").backend, method=method)


def ideal_method(qc: QuantumCircuit) -> str:
    if PN.is_clifford(qc):
        return "stabilizer"
    return "statevector" if qc.num_qubits <= 28 else "matrix_product_state"


def transpile_to(qc: QuantumCircuit, target: str, seed: int, dd: bool = False) -> QuantumCircuit:
    """ISA circuit on the target's physical layout (the hashed / packed form)."""
    return PN.isa(qc, target, seed, dd_qubits=(qc.metadata or {}).get("dd_qubits") if dd else None)


def restrict(qc: QuantumCircuit, keep: list[int], name: str | None = None) -> QuantumCircuit:
    """Sub-circuit on the physical qubits `keep` (in the order of the parent layout). Valid only when no gate links
    a kept qubit to a dropped one (lint rule 3 guarantees it across regions); clbits follow their qubit's measure."""
    lay = qc.metadata["layout"]
    keep_set = set(keep)
    ks = [k for k, q in enumerate(lay) if q in keep_set]
    qmap = {qc.qubits[k]: i for i, k in enumerate(ks)}
    out = QuantumCircuit(len(ks), len(ks), name=name or qc.name)
    cmap = {}
    for ins in qc.data:
        qs = [qmap.get(q) for q in ins.qubits]
        if all(x is None for x in qs):
            continue
        if any(x is None for x in qs):
            raise ValueError(f"{ins.operation.name} links kept and dropped qubits in {qc.name}")
        if ins.operation.name == "measure":
            c = qc.clbits.index(ins.clbits[0])
            cmap[c] = qs[0]
            out.measure(qs[0], qs[0])
            continue
        out.append(ins.operation, qs)
    md = dict(qc.metadata)
    md["layout"] = [lay[k] for k in ks]
    md["clbit_from_parent"] = {int(cmap_k): int(v) for cmap_k, v in cmap.items()}
    if md.get("root") not in md["layout"]:
        md["root"] = None
    if md.get("dd_qubits"):
        md["dd_qubits"] = [q for q in md["dd_qubits"] if q in keep_set]
    out.metadata = md
    return out


def execute(circuits: list[QuantumCircuit], mode: str, target: str, shots: int, seed: int,
            method: str | None = None, deadline=None) -> dict:
    """Run one job. Returns {bits: [array (shots, ncl)], isa: [circuit], hashes, sim_label, mode}.
    twin:<t> runs the circuits it is given (the caller passes the family's Clifford twins) under the Pauli model.
    With a `deadline`, circuits run one simulator call each and DeadlineHit is raised between them once it passes."""
    def tick(i: int) -> None:
        if deadline is not None:
            deadline.check(f"{mode} circuit {i + 1}/{len(circuits)} ({circuits[i].name})")

    kind, _, tname = mode.partition(":")
    if kind == "heron":
        tname = "marrakesh"
    tname = tname or target
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        isa = [transpile_to(qc, tname, seed, dd=(kind == "heron")) for qc in circuits] if T.get(tname).backend is not None or kind in (
            "pauli", "twin") else list(circuits)
        hashes = [circuit_hash(c) for c in isa]
        if kind == "ideal":
            res = []
            for i, qc in enumerate(circuits):
                tick(i)
                sim = AerSimulator(method=method or ideal_method(qc))
                res.append(sim.run(transpile(qc, sim, optimization_level=0), shots=shots, seed_simulator=seed,
                                   memory=True).result())
            bits = [WS.bits_of(r, 0) for r in res]
        elif kind == "heron":
            meth = method or "automatic"
            bits = []
            for i, c in enumerate(isa):
                tick(i)
                r = _heron_sim(meth).run(c, shots=shots, seed_simulator=seed, memory=True).result()
                bits.append(WS.bits_of(r, 0))
        elif kind in ("pauli", "twin"):
            bits = []
            for i, c in enumerate(isa):
                tick(i)
                r, _ = PN.run([PN.delays_to_pauli(c, tname)], tname, shots, seed, prepared=True, method=method)
                bits.append(WS.bits_of(r, 0))
        else:
            raise ValueError(f"unknown mode {mode!r}")
    return {"bits": bits, "isa": isa, "hashes": hashes, "sim_label": T.sim_label(mode if kind != "heron" else "heron"),
            "mode": mode}


def mode_target(mode: str, target: str) -> str:
    kind, _, tname = mode.partition(":")
    return "marrakesh" if kind == "heron" else (tname or target)


def grid_sha256(grid: dict) -> str:
    return hashlib.sha256(json.dumps(grid, sort_keys=True, default=str).encode()).hexdigest()


def width_ladder(ladder, cap: int) -> list[int]:
    out = [n for n in ladder if n <= cap]
    if cap not in out and cap > (out[-1] if out else 0):
        out.append(cap)
    return out


# ---------------------------------------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if not a.list:
        ap.print_help()
        return 0
    for name in FAMILIES:
        f = get(name)
        print(f"{name:13s} claim {f.CLAIM:4s} witness: {f.WITNESS}")
        print(f"{'':13s} hardness: {f.HARDNESS}")
        for b in BUDGETS:
            print(f"{'':13s} {b:3d} q: {f.preset_text(b)}")
    for name, txt in RECIPES.items():
        print(f"{name:13s} recipe: {txt}")
        print(f"{'':13s}  40 q: spine 14 + 2 checks, QCA 12, PMD 1 machine")
        print(f"{'':13s} 100 q: spine 48 + 4 checks, QCA 30, PMD 1 machine")
        print(f"{'':13s} 120 q: Nighthawk rows 0-3 spine, row 4 buffer, rows 5-9 QCA, row 10 buffer, row 11 PMD "
              f"(Heron: spine 60 + 4, QCA 40, PMD 1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
