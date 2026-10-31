"""D-SCALE target registry (AC-1): every simulation target as one calibration record.

    python -m dscale.targets --show

Targets (Q4): `marrakesh` (FakeMarrakesh, Heron r2, the default noisy mode), `kingston` (FakeKingston, Heron r2,
back-test against the QALife hardware data), `boston` (FakeBoston, Heron r3, 40/100 proxy), `nighthawk`
(FakeNighthawk, 120 q square lattice), `helios-class` (generic all-to-all 98 q from the Quantinuum Helios datasheet;
no fake backend exists, so there is no ISA: it is used by the Pauli model only).

`get(name)` returns a `Target` with the coupling graph, per-qubit / per-edge errors, readout p01 = p(1|0) and
p10 = p(0|1), T1/T2, durations, a calibration snapshot (props sha256, last_update_date, runtime version) and a label.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as md
import json
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import networkx as nx
import numpy as np

FAKES = {"marrakesh": "FakeMarrakesh", "kingston": "FakeKingston", "boston": "FakeBoston",
         "nighthawk": "FakeNighthawk"}
NAMES = ("marrakesh", "kingston", "boston", "nighthawk", "helios-class")
TITLES = {"marrakesh": "Marrakesh", "kingston": "Kingston", "boston": "Boston", "nighthawk": "Nighthawk",
          "helios-class": "Helios-class"}

# Quantinuum Helios datasheet (98 q, all-to-all): 2q 7.9e-4, 1q 2.5e-5, readout p(1|0) 8.1e-4 / p(0|1) 1.6e-4,
# memory error 1e-3 per layer. Durations are not on the datasheet; trapped-ion gates are ~100 us (illustrative,
# only used for QPU-time estimates, never for the noise, which uses the per-layer memory error).
HELIOS = {"n": 98, "e2q": 7.9e-4, "e1q": 2.5e-5, "p01": 8.1e-4, "p10": 1.6e-4, "memory_per_layer": 1e-3,
          "dur_1q": 10e-6, "dur_2q": 100e-6, "dur_meas": 150e-6,
          "source": "Quantinuum Helios datasheet (98 q, 2025): 2q 99.921 %, 1q 99.9975 %, SPAM p(1|0) 8.1e-4 / "
                    "p(0|1) 1.6e-4, memory error 1e-3 per layer"}


@dataclass
class Target:
    name: str
    label: str                                    # e.g. "Nighthawk (FakeNighthawk, 120 q square lattice)"
    n_qubits: int
    graph: nx.Graph                               # undirected coupling graph
    e2q: dict[tuple[int, int], float]             # sorted edge -> 2q gate error
    e1q: dict[int, float]                         # qubit -> sx error
    p01: dict[int, float]                         # p(1|0)
    p10: dict[int, float]                         # p(0|1)
    t1: dict[int, float]
    t2: dict[int, float]
    durations: dict[str, float]                   # median seconds: "1q", "2q", "meas"
    calibration: dict
    gate_2q: str = "cz"
    backend: object | None = None                 # the fake backend (None for helios-class)
    memory_per_layer: float | None = None         # helios-class idle model
    meta: dict = field(default_factory=dict)

    def ro(self, q: int) -> float:
        """Symmetric readout error (p01 + p10) / 2."""
        return 0.5 * (self.p01[q] + self.p10[q])

    def edge_err(self, i: int, j: int) -> float:
        return self.e2q[(i, j) if i < j else (j, i)]


def _fake(name: str):
    from qiskit_ibm_runtime import fake_provider as fp
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")                           # FakeNighthawk warns its values are not typical
        return getattr(fp, FAKES[name])()


def calibration_snapshot(backend) -> dict:
    props = Path(backend.dirname) / backend.props_filename
    return {"fake_backend": type(backend).__name__,
            "qiskit_ibm_runtime_version": md.version("qiskit-ibm-runtime"),
            "props_sha256": hashlib.sha256(props.read_bytes()).hexdigest(),
            "last_update_date": json.loads(props.read_text())["last_update_date"]}


def get(name: str) -> Target:
    if name in LIVE:
        return LIVE[name]
    return _get(name)


@lru_cache(maxsize=8)
def _get(name: str) -> Target:
    if name not in NAMES:
        raise SystemExit(f"unknown target {name!r}; choose from {', '.join(NAMES)}")
    if name == "helios-class":
        n = HELIOS["n"]
        g = nx.complete_graph(n)
        q = range(n)
        return Target(
            name=name, label=f"Helios-class (generic all-to-all {n} q, datasheet values)", n_qubits=n, graph=g,
            e2q={tuple(sorted(e)): HELIOS["e2q"] for e in g.edges}, e1q={k: HELIOS["e1q"] for k in q},
            p01={k: HELIOS["p01"] for k in q}, p10={k: HELIOS["p10"] for k in q},
            t1={k: float("inf") for k in q}, t2={k: float("inf") for k in q},
            durations={"1q": HELIOS["dur_1q"], "2q": HELIOS["dur_2q"], "meas": HELIOS["dur_meas"]},
            calibration={"fake_backend": None, "source": HELIOS["source"],
                         "qiskit_ibm_runtime_version": md.version("qiskit-ibm-runtime"),
                         "props_sha256": hashlib.sha256(json.dumps(HELIOS, sort_keys=True).encode()).hexdigest(),
                         "last_update_date": "datasheet"},
            gate_2q="rzz", backend=None, memory_per_layer=HELIOS["memory_per_layer"], meta={"all_to_all": True})
    b = _fake(name)
    lat = "square lattice" if name == "nighthawk" else "heavy-hex"
    fam = {"marrakesh": "Heron r2", "kingston": "Heron r2", "boston": "Heron r3", "nighthawk": "Nighthawk"}[name]
    return from_backend(name, b, f"{TITLES[name]} ({FAKES[name]}, {fam}, {b.num_qubits} q {lat})",
                        calibration_snapshot(b), {"lattice": lat, "family": fam})


def _prop(props, q: int, key: str, fallback: float) -> float:
    try:
        return float(props.qubit_property(q, key)[0])
    except Exception:
        return fallback


def from_backend(name: str, b, label: str, calibration: dict, meta: dict | None = None) -> Target:
    """Calibration record of any IBM backend object (fake or live): coupling graph from its 2q gate, sx error,
    asymmetric readout (properties, falling back to the symmetric measure error), T1/T2, median durations."""
    t = b.target
    try:
        props = b.properties()
    except Exception:
        props = None
    g2 = next(op for op in ("cz", "ecr", "cx") if op in t.operation_names)
    g = nx.Graph()
    g.add_nodes_from(range(b.num_qubits))
    e2q, d2 = {}, []
    for (i, j), ip in t[g2].items():
        e = (min(i, j), max(i, j))
        g.add_edge(*e)
        err = float(ip.error) if ip is not None and ip.error is not None else 1.0
        e2q[e] = max(e2q.get(e, 0.0), err)                       # directed pairs: keep the worse
        if ip is not None and ip.duration:
            d2.append(ip.duration)

    def ierr(op, q, default=1.0):
        ip = t[op].get((q,)) if op in t.operation_names else None
        return float(ip.error) if ip is not None and ip.error is not None else default

    e1q = {q: ierr("sx", q) for q in range(b.num_qubits)}
    meas = {q: ierr("measure", q, 0.5) for q in range(b.num_qubits)}
    p01 = {q: _prop(props, q, "prob_meas1_prep0", meas[q]) if props else meas[q] for q in range(b.num_qubits)}
    p10 = {q: _prop(props, q, "prob_meas0_prep1", meas[q]) if props else meas[q] for q in range(b.num_qubits)}
    qp = t.qubit_properties or [None] * b.num_qubits
    t1 = {q: float(getattr(qp[q], "t1", None) or np.inf) for q in range(b.num_qubits)}
    t2 = {q: float(getattr(qp[q], "t2", None) or np.inf) for q in range(b.num_qubits)}

    def med(op):
        v = [ip.duration for ip in t[op].values() if ip is not None and ip.duration] if op in t.operation_names else []
        return float(np.median(v)) if v else float("nan")

    dur = {"1q": med("sx"), "2q": float(np.median(d2)) if d2 else float("nan"), "meas": med("measure")}
    return Target(name=name, label=label, n_qubits=b.num_qubits, graph=g, e2q=e2q, e1q=e1q, p01=p01, p10=p10,
                  t1=t1, t2=t2, durations=dur, calibration=calibration, gate_2q=g2, backend=b, meta=meta or {})


LIVE: dict[str, Target] = {}


def register(tg: Target) -> Target:
    """Make a live (or local-test) backend visible to get(name) for the rest of the process."""
    LIVE[tg.name] = tg
    return tg


def sim_label(mode: str) -> str:
    """Honesty labels (plan §4 Labels)."""
    if mode == "ideal":
        return "simulated: ideal"
    if mode == "heron":
        return "simulated: Heron-class noise (FakeMarrakesh)"
    kind, _, tname = mode.partition(":")
    if kind == "pauli":
        return f"simulated: Pauli-twirled {TITLES[tname]} noise (stabilizer)"
    if kind == "twin":
        return f"predicted (Clifford twin, Pauli-twirled {TITLES[tname]})"
    raise ValueError(f"unknown mode {mode!r}")


def summary(tg: Target) -> dict:
    deg = Counter(dict(tg.graph.degree()).values())
    ro = [tg.ro(q) for q in range(tg.n_qubits)]
    e2 = list(tg.e2q.values())
    bad = sum(1 for v in e2 if v >= 0.99)
    bad_dir = (sum(1 for _, ip in tg.backend.target[tg.gate_2q].items() if ip.error is not None and ip.error >= 0.99)
               if tg.backend is not None else 0)
    return {"name": tg.name, "label": tg.label, "n_qubits": tg.n_qubits, "edges": tg.graph.number_of_edges(),
            "degree_histogram": dict(sorted(deg.items())) if tg.name != "helios-class" else {tg.n_qubits - 1: tg.n_qubits},
            "median_2q": float(np.median(e2)), "p90_2q": float(np.percentile(e2, 90)),
            "median_readout": float(np.median(ro)), "p90_readout": float(np.percentile(ro, 90)),
            "couplers_err_ge_0.99": bad, "couplers_err_ge_0.99_directed": bad_dir, "durations": tg.durations,
            "calibration": {k: tg.calibration.get(k) for k in ("fake_backend", "last_update_date")}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--show", action="store_true", help="print every target")
    ap.add_argument("--target", nargs="*", default=list(NAMES))
    a = ap.parse_args()
    if not a.show:
        ap.print_help()
        return 0
    for name in a.target:
        s = summary(get(name))
        print(f"{s['name']:13s} {s['label']}")
        print(f"   n_qubits={s['n_qubits']}  edges={s['edges']}  degrees={s['degree_histogram']}")
        print(f"   2q median={s['median_2q']:.4f} p90={s['p90_2q']:.4f}   readout median={s['median_readout']:.4f} "
              f"p90={s['p90_readout']:.4f}   couplers with error >= 0.99: {s['couplers_err_ge_0.99']} "
              f"({s['couplers_err_ge_0.99_directed']} directed)")
        d = s["durations"]
        print(f"   durations: 1q {d['1q'] * 1e9:.0f} ns, 2q {d['2q'] * 1e9:.0f} ns, meas {d['meas'] * 1e6:.2f} us;"
              f"  calibration {s['calibration']['fake_backend']} @ {s['calibration']['last_update_date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
