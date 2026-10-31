"""D-SCALE survival lints (AC-3): every job passes these before it is simulated or packed.

    python -m dscale.lint --selftest

`lint(circuits, regions, family, graph=None)` takes one job (a list of logical circuits whose `metadata["layout"]`
maps circuit qubit k -> physical qubit), the allocation's `regions` and the family name. A violation raises
`LintError` (CLIs exit 5), unless the circuit declares `metadata["control_arm"] = True` (a declared A/B control arm,
e.g. the mid-circuit q-machine of pmd-bank); control-arm hits are reported as `ok (control arm)`.
"""
from __future__ import annotations

import argparse
from collections import Counter

import networkx as nx
import numpy as np
from qiskit import QuantumCircuit

EXIT_LINT = 5
RULES = {
    1: "no mid-circuit measure / reset / feed-forward",
    2: "quantum claims use >= 2 measurement bases",
    3: "no 2q gate across regions; a buffer (distance >= 2) separates them",
    4: "founder / root starts on the equator",
    5: "spine rotations |theta| <= 0.1",
    6: "<= 2 two-qubit gates per certified spine qubit (amortised)",
    7: "0 routing SWAPs on ch-qca / kicked-ising",
}
CONTROL_FLOW = {"if_else", "switch_case", "while_loop", "for_loop"}
BASIS_CHANGE = {"h", "s", "sdg", "sx", "sxdg", "barrier", "measure", "x"}
ROT = {"rx", "ry", "rz", "p", "u", "u1", "u2", "u3", "rxx", "ryy", "rzz", "crx", "cry", "crz"}
NATIVE_FAMILIES = {"ch-qca", "kicked-ising"}


class LintError(Exception):
    def __init__(self, results: list[dict]):
        bad = [r for r in results if not r["ok"]]
        super().__init__("; ".join(f"rule {r['rule']} ({RULES[r['rule']]}): {r['detail']}" for r in bad))
        self.results = results


def _phys(qc: QuantumCircuit) -> list[int]:
    lay = qc.metadata.get("layout") if qc.metadata else None
    return list(lay) if lay is not None else list(range(qc.num_qubits))


def _ops(qc: QuantumCircuit):
    lay = _phys(qc)
    idx = {q: k for k, q in enumerate(qc.qubits)}
    for ins in qc.data:
        yield ins.operation, [lay[idx[q]] for q in ins.qubits]


def _region_maps(regions: dict) -> tuple[dict[int, str], dict[int, str]]:
    group, role = {}, {}
    for name, r in regions.items():
        if r["role"] == "buffer":
            continue
        for q in r["qubits"]:
            group[q] = r.get("group", name)
            role[q] = r["role"]
    return group, role


def _rule1(qc) -> str | None:
    done: set[int] = set()
    for op, qs in _ops(qc):
        if op.name in CONTROL_FLOW:
            return f"{op.name} in {qc.name}"
        if op.name == "reset":
            return f"reset on q{qs[0]} in {qc.name}"
        if op.name == "measure":
            done.add(qs[0])
            continue
        if op.name == "barrier":
            continue
        hit = done.intersection(qs)
        if hit:
            return f"{op.name} on q{sorted(hit)[0]} after its measure in {qc.name}"
    return None


def lint(circuits: list[QuantumCircuit] | QuantumCircuit, regions: dict, family: str,
         graph: nx.Graph | None = None, claim: bool = True) -> list[dict]:
    circuits = [circuits] if isinstance(circuits, QuantumCircuit) else list(circuits)
    group, role = _region_maps(regions)
    res: list[dict] = []

    def add(rule: int, detail: str | None, arm: bool = False, na: bool = False):
        ok = detail is None or arm
        txt = "n/a" if na else ("ok" if detail is None else (f"ok (control arm): {detail}" if arm else detail))
        res.append({"rule": rule, "ok": ok, "detail": txt})

    # 1. Deferred readout c(1) ~ 0.84 vs per-generation readout ~ 0.10 (artificial-life RUNLOG_MONTH3:69,89,119,139);
    #    dynamic routing lost 3 of 4 live comparisons on Heron r2 (readout >> 2q error).
    hits = [(qc, _rule1(qc)) for qc in circuits]
    main = [h for qc, h in hits if h and not (qc.metadata or {}).get("control_arm")]
    arm = [h for qc, h in hits if h and (qc.metadata or {}).get("control_arm")]
    add(1, main[0] if main else (arm[0] if arm else None), arm=not main and bool(arm))

    # 2. A single-qubit dial read in Z is a classical biased coin; interference claims need >= 2 bases (CLAUDE.md).
    bases = {(qc.metadata or {}).get("basis") for qc in circuits if not (qc.metadata or {}).get("control_arm")}
    bases.discard(None)
    if claim:
        add(2, None if len(bases) >= 2 else f"job measures only {sorted(bases) or ['?']}")
    else:
        add(2, None, na=True)

    # 3. Separable soma +0.899 vs entangled cx(g,p) +0.120; idle body +0.732 vs active body -0.058 next to a W = 12
    #    germ (PJ0_CONCLUSION.html:194-197; feature-PJ2.1-gradual-biology.md:22-27).
    cross = None
    for qc in circuits:
        for op, qs in _ops(qc):
            if len(qs) == 2 and op.name != "barrier":
                ga, gb = group.get(qs[0]), group.get(qs[1])
                if ga is None or gb is None:
                    cross = cross or f"{op.name}({qs[0]},{qs[1]}) touches an unallocated qubit"
                elif ga != gb:
                    cross = cross or f"{op.name}({qs[0]},{qs[1]}) links region {ga} to {gb}"
    complete = graph is not None and graph.number_of_edges() == graph.number_of_nodes() * (graph.number_of_nodes() - 1) // 2
    if cross is None and graph is not None and not complete:            # all-to-all: no coupler buffer exists
        used = sorted({q for qc in circuits for q in _phys(qc)})
        groups = {}
        for q in used:
            groups.setdefault(group.get(q, "?"), []).append(q)
        if len(groups) > 1:
            dmin = 10 ** 9
            for gname, src in groups.items():
                dist = nx.multi_source_dijkstra_path_length(graph, src)
                for q in used:
                    if group.get(q) != gname and q in dist:
                        dmin = min(dmin, dist[q])
            if dmin < 2:
                cross = f"regions at graph distance {dmin} (< 2: no buffer qubit)"
    add(3, cross)

    # 4. Without an equator founder C(g >= 1) ~ 0 (artificial-life RUNLOG_MONTH2/3, memory qdep-setup-bug-fix).
    roots = {(qc.metadata or {}).get("root") for qc in circuits} - {None}
    if not roots:
        add(4, None, na=True)
    else:
        bad = None
        for qc in circuits:
            r = (qc.metadata or {}).get("root")
            if r is None:
                continue
            first = next(((op, qs) for op, qs in _ops(qc) if r in qs and op.name != "barrier"), None)
            if first is None:
                bad = f"root q{r} has no gate in {qc.name}"
                break
            op = first[0]
            eq = op.name == "h" or (op.name in ("ry", "rx") and np.isclose(abs(float(op.params[0])) % np.pi, np.pi / 2))
            if not eq:
                bad = f"root q{r} starts with {op.name} in {qc.name}"
                break
        add(4, bad)

    # 5. Unitary aging, not damping: unitary W* = 24 vs damping W* = 9 (P2_CONCLUSION.html:145-148); PJ0 lean
    #    spine used mutation 0 (PJ0_CONCLUSION.html:163-169). Small rotations only on certified qubits.
    cert = {q for q, r in role.items() if r == "certified"}
    bad5 = None
    for qc in circuits:
        r = (qc.metadata or {}).get("root")
        seen_root = False
        for op, qs in _ops(qc):
            if op.name in ROT and cert.intersection(qs):
                if qs[0] == r and not seen_root:
                    seen_root = True
                    continue
                for th in op.params:
                    try:
                        v = float(th)
                    except TypeError:
                        continue
                    m = v % (np.pi / 2)
                    if op.name == "rz" and (np.isclose(m, 0) or np.isclose(m, np.pi / 2)):
                        continue                                # Clifford frame change (basis rotation)
                    if abs(v) > 0.1:
                        bad5 = bad5 or f"{op.name}({v:.3f}) on certified q{qs[0]} in {qc.name}"
            if r in qs:
                seen_root = True
    add(5, bad5, na=not cert)

    # 6. Lean spine survives to W = 50 (100 q), decay ~0.94 per GHZ qubit, vs 2018 biology ~0.861
    #    (PJ0_CONCLUSION.html:163-169; CONCLUSION_MONTH4.md:147-154). Amortised over the certified qubits, because a
    #    BFS tree (Big Cats, arXiv 2510.09520) has branching nodes by design.
    if cert:
        worst = None
        for qc in circuits:
            n2 = sum(1 for op, qs in _ops(qc) if len(qs) == 2 and op.name != "barrier" and cert.intersection(qs))
            per = Counter(q for op, qs in _ops(qc) if len(qs) == 2 and op.name != "barrier" for q in qs if q in cert)
            ratio = n2 / len(cert)
            if worst is None or ratio > worst[0]:
                worst = (ratio, max(per.values(), default=0), qc.name)
        add(6, None if worst[0] <= 2 else f"{worst[0]:.2f} 2q gates per certified qubit in {worst[2]} "
                                            f"(max on one qubit {worst[1]})")
    else:
        add(6, None, na=True)

    # 7. RE D-3 exact rule needed C^3-H = 376 routing SWAPs; Jones T6 is two CH per site (D14 Fig. 1c).
    if family in NATIVE_FAMILIES:
        off = 0
        for qc in circuits:
            for op, qs in _ops(qc):
                if op.name == "swap" or (len(qs) == 2 and op.name != "barrier" and graph is not None
                                         and not graph.has_edge(*qs)):
                    off += 1
        add(7, None if off == 0 else f"{off} 2q gates off the coupling graph (would need routing SWAPs)")
    else:
        add(7, None, na=True)
    return res


def enforce(circuits, regions: dict, family: str, graph: nx.Graph | None = None, claim: bool = True) -> list[dict]:
    """lint + raise LintError on any violation."""
    res = lint(circuits, regions, family, graph, claim)
    if not all(r["ok"] for r in res):
        raise LintError(res)
    return res


def show(res: list[dict]) -> None:
    for r in res:
        print(f"  rule {r['rule']}  {'ok  ' if r['ok'] else 'FAIL'}  {RULES[r['rule']]:58s} {r['detail']}")


def selftest() -> int:
    from dscale import allocate as A, families as F, targets as T

    tg = T.get("marrakesh")
    fam = F.get("ghz-spine")
    alloc = A.allocate(fam.region_request(40, tg), tg)
    job = fam.build(alloc, fam.PRESETS[40] | {"N": 12}, draw=fam.default_draw())
    print("clean ghz-spine job (12-qubit spine, marrakesh):")
    res = lint(job, alloc["regions"], "ghz-spine", tg.graph)
    show(res)
    clean_ok = all(r["ok"] for r in res) and sum(r["detail"] == "ok" for r in res) >= 5

    bad = [qc.copy() for qc in job]
    qc = bad[0]
    lay = qc.metadata["layout"]
    spine = alloc["regions"]["spine"]["qubits"]
    soma = alloc["regions"]["soma"]["qubits"]
    k_sp, k_so = lay.index(spine[0]), lay.index(soma[0])
    inj = qc.copy_empty_like()
    for i, ins in enumerate(qc.data):
        inj.append(ins)
        if i == 3:                                        # injected mid-circuit measure
            inj.measure(k_sp, 0)
    inj.cx(k_sp, k_so)                                    # injected spine -> soma gate
    inj.metadata = dict(qc.metadata)
    bad[0] = inj
    print("injected: mid-circuit measure + spine->soma CX:")
    res_bad = lint(bad, alloc["regions"], "ghz-spine", tg.graph)
    show(res_bad)
    n_bad = sum(not r["ok"] for r in res_bad)
    print(f"violations: {n_bad} (expected 2); clean build all ok: {clean_ok}")
    if not clean_ok:
        return 1
    return EXIT_LINT if n_bad == 2 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
