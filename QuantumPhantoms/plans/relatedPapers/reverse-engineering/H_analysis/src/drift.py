"""`drift` section: cohort / shot marginals vs the exact rulebook Bayesian network.

Own NumPy enumeration of the BN (no pyAgrum). Count decoding assumption (Q8 / CCR-H2): the state index of a node
is little-endian over its `qubit_map` list, i.e. bit k of the state = qubit qubit_map[node][k]; in a counts
bitstring qubit q is the character at position -1-q. Codes >= the node's state count are invalid shots.
"""
from __future__ import annotations

import itertools

import numpy as np
from scipy import stats


def _table(node: dict, context: dict):
    if "cpt_by_context" in node:
        key = "|".join(str(context[k]) for k in node["context_keys"])
        return np.asarray(node["cpt_by_context"][key], float)
    return np.asarray(node["cpt"], float)


def enumerate_bn(rulebook: dict, context: dict) -> tuple[list[str], np.ndarray]:
    """Return (node names, joint array with one axis per node in rulebook order)."""
    nodes = rulebook["nodes"]
    names = [n["name"] for n in nodes]
    sizes = [len(n["states"]) for n in nodes]
    joint = np.ones(sizes)
    for idx in itertools.product(*[range(s) for s in sizes]):
        p = 1.0
        for i, n in enumerate(nodes):
            t = _table(n, context)
            for pa in n["parents"]:
                t = t[idx[names.index(pa)]]
            p *= t[idx[i]]
        joint[idx] = p
    return names, joint


def marginals(names, joint) -> dict[str, np.ndarray]:
    return {n: joint.sum(axis=tuple(j for j in range(joint.ndim) if j != i)) for i, n in enumerate(names)}


def tvd(p, q) -> float:
    return float(0.5 * np.abs(np.asarray(p) - np.asarray(q)).sum())


def rmspe_pct(p_exact, p_emp) -> float:
    m = np.asarray(p_exact) > 0
    return float(np.sqrt((((np.asarray(p_emp)[m] - np.asarray(p_exact)[m]) / np.asarray(p_exact)[m] * 100) ** 2).mean()))


def chi2_p(p_exact, counts) -> float:
    counts = np.asarray(counts, float)
    n = counts.sum()
    if n == 0:
        return float("nan")
    p = np.asarray(p_exact, float)
    if counts[p == 0].sum() > 0:
        return 0.0
    m = p > 0
    return float(stats.chisquare(counts[m], p[m] * n).pvalue) if m.sum() > 1 else float("nan")


def decode_counts(counts: dict, qubit_map: dict, state_counts: dict) -> dict:
    """-> {node: state-count vector}, joint counts array (valid shots only), n_shots, n_invalid."""
    names = list(qubit_map)
    per_node = {n: np.zeros(state_counts[n]) for n in names}
    joint = np.zeros([state_counts[n] for n in names])
    n_tot = n_inv = 0
    for bits, c in counts.items():
        n_tot += c
        states, bad = [], False
        for n in names:
            code = sum(int(bits[-1 - q]) << k for k, q in enumerate(qubit_map[n]))
            if code >= state_counts[n]:
                bad = True
            states.append(code)
        for n, s in zip(names, states):
            if s < state_counts[n]:
                per_node[n][s] += c
        if bad:
            n_inv += c
        else:
            joint[tuple(states)] += c
    return {"per_node": per_node, "joint": joint, "n": n_tot, "n_invalid": n_inv}


def _node_metrics(exact, vec):
    n = vec.sum()
    emp = vec / n if n else np.full_like(vec, np.nan)
    return {"tvd": tvd(exact, emp) if n else None, "rmspe_pct": rmspe_pct(exact, emp) if n else None,
            "chi2_p": chi2_p(exact, vec), "n": int(n)}


def cohort_vectors(rulebook: dict, draws: list[dict]) -> dict:
    """Map TumorDraw fields onto binary rulebook nodes: node == tumor type or node == margin."""
    out = {}
    for node in rulebook["nodes"]:
        if len(node["states"]) != 2:
            continue
        name = node["name"]
        vals = [(d["type"] == name) if name in ("solid", "part-solid", "ground-glass") else (d.get("margin") == name)
                for d in draws]
        if name not in ("solid", "part-solid", "ground-glass") and not any(d.get("margin") == name for d in draws) \
                and not draws:
            continue
        out[name] = np.array([len(vals) - sum(vals), sum(vals)], float)  # states [no, yes]
    return out


def run(cohort: dict) -> dict:
    o = cohort["obj"]
    if not o["rulebook"] or not o["compiled_circuit"]:
        return {"status": "insufficient input", "n": 0, "needs": "rulebook + compiled_circuit"}
    rb, cc = o["rulebook"][0], o["compiled_circuit"][0]
    names, joint = enumerate_bn(rb, cc["context"])
    exact = marginals(names, joint)
    state_counts = {n["name"]: len(n["states"]) for n in rb["nodes"]}
    out: dict = {"decoding": "little-endian over qubit_map list (Q8 / CCR-H2 assumption)",
                 "context": cc["context"], "by_sim_label": {}, "cohort": {"status": "insufficient input", "n": 0}}
    agg: dict = {}
    for jr in o["job_records"]:
        dec = decode_counts(jr["counts"], cc["qubit_map"], state_counts)
        a = agg.setdefault(jr["sim_label"], {"per_node": {n: np.zeros(state_counts[n]) for n in names},
                                               "joint": np.zeros(joint.shape), "n": 0, "n_invalid": 0})
        for n in names:
            if n in dec["per_node"]:
                a["per_node"][n] += dec["per_node"][n]
        a["joint"] += dec["joint"] if dec["joint"].shape == joint.shape else 0
        a["n"] += dec["n"]
        a["n_invalid"] += dec["n_invalid"]
    for label, a in agg.items():
        jt = a["joint"].sum()
        out["by_sim_label"][label] = {
            "per_node": {n: _node_metrics(exact[n], a["per_node"][n]) for n in names},
            "joint_tvd": tvd(joint, a["joint"] / jt) if jt else None,
            "invalid_shot_fraction": a["n_invalid"] / a["n"] if a["n"] else None, "n": int(a["n"])}
    if not agg:
        out["by_sim_label"] = {"status": "insufficient input", "n": 0}
    if o["draws"]:
        vecs = cohort_vectors(rb, o["draws"])
        out["cohort"] = {"per_node": {n: _node_metrics(exact[n], v) for n, v in vecs.items()},
                         "n": len(o["draws"]),
                         "note": "cohort-level compare maps TumorDraw type/margin onto binary rulebook nodes; "
                                 "draws are context-mixed so this is indicative only"}
    out["exact_marginals"] = {n: [float(x) for x in v] for n, v in exact.items()}
    out["n"] = sum(v["n"] for v in out["by_sim_label"].values() if isinstance(v, dict) and "n" in v)
    return out
