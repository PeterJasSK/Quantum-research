"""B-2: site register in superposition, phenotype registers controlled on the site's placement class."""
import numpy as np

from B_mapping.src.compiler import finish, load_dist, n_qubits, node_ops
from B_mapping.src.rulebook import CLASSES, joint_table, node_table, order
from shared.seedhash import rng


def pick_sites(sites: list, k: int, cert_seed: str) -> list:
    """Seeded pick of up to k sites; every class present in `sites` is represented."""
    g = rng(cert_seed, "B.site_pick")
    k = min(k, len(sites))
    chosen = []
    for cls in CLASSES:
        pool = [s for s in sites if s["context"]["placement_class"] == cls]
        if pool and len(chosen) < k:
            chosen.append(pool[int(g.integers(len(pool)))])
    rest = [s for s in sites if s not in chosen]
    g.shuffle(rest)
    chosen += rest[: k - len(chosen)]
    return sorted(chosen, key=lambda s: s["site_id"])


def site_weights(subset: list, prior: dict) -> list:
    """w_site = P(class) / n_class-in-subset, renormalised over classes present."""
    n = {c: sum(s["context"]["placement_class"] == c for s in subset) for c in CLASSES}
    present = sum(prior[c] for c in CLASSES if n[c])
    return [prior[s["context"]["placement_class"]] / n[s["context"]["placement_class"]] / present for s in subset]


def compile_joint(rulebook: dict, subset: list, prior: dict, *, multi_control: str = "mcry"):
    nodes = order(rulebook)
    kq = n_qubits(len(subset))
    qubits, nxt = {"site": list(range(kq))}, kq
    for n in nodes:
        k = n_qubits(len(n["states"]))
        qubits[n["name"]] = list(range(nxt, nxt + k))
        nxt += k
    ops = []
    load_dist(ops, qubits["site"], site_weights(subset, prior), [])
    site_ctrl = lambda code: [(q, (code >> i) & 1) for i, q in enumerate(qubits["site"])]
    for n in nodes:
        if "cpt_by_context" not in n:
            ops += node_ops(n, node_table(n, {}), qubits)
            continue
        # one controlled tree per site code (sites of one class share identical rows)
        for code, s in enumerate(subset):
            ctx = {"placement_class": s["context"]["placement_class"]}
            ops += node_ops(n, node_table(n, ctx), qubits, site_ctrl(code))
    names = ["site"] + [n["name"] for n in nodes]
    states = [[s["site_id"] for s in subset]] + [n["states"] for n in nodes]
    return finish(ops, qubits, names, states, nxt, multi_control,
                  extra={"sites": [s["site_id"] for s in subset]})


def joint_reference(rulebook: dict, subset: list, prior: dict) -> dict:
    """Classical joint (site, phenotype...) = w_site * P(phenotype | class of site)."""
    out = {}
    for code, (s, w) in enumerate(zip(subset, site_weights(subset, prior))):
        for combo, p in joint_table(rulebook, {"placement_class": s["context"]["placement_class"]}).items():
            out[(code,) + combo] = w * p
    return out


def ancestral_joint(rulebook: dict, subset: list, prior: dict, shots: int, g) -> dict:
    """Classical baseline: draw site, then ancestral-sample the phenotype for its class."""
    from B_mapping.src.rulebook import ancestral_sample
    w = np.asarray(site_weights(subset, prior))
    per_site = g.multinomial(shots, w / w.sum())
    out = {}
    for code, (s, n) in enumerate(zip(subset, per_site)):
        if n:
            for combo, c in ancestral_sample(rulebook, {"placement_class": s["context"]["placement_class"]}, int(n), g).items():
                out[(code,) + combo] = c
    return out
