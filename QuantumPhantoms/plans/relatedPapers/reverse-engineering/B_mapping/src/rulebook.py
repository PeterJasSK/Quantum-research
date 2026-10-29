"""Lung rulebook builder plus exact joint table and ancestral sampler (classical reference)."""
import argparse
import itertools
import json
from datetime import datetime, timezone

import numpy as np

from shared import CONTRACT_VERSION, RE_ROOT
from shared.seedhash import code_hash, hash_json

LETTER_DIR = RE_ROOT / "B_mapping"
DATA = LETTER_DIR / "data"
RULEBOOK_PATH = DATA / "rulebook_lung.json"
PRIOR_PATH = DATA / "class_prior.json"
CLASSES = ["free", "juxtavascular", "juxtapleural"]
TYPES = ["solid", "part-solid", "ground-glass"]
SIZES = ["3-6", "6-10", "10-20", "20-30"]
MARGINS = ["smooth", "lobulated", "spiculated"]

# Placement-class prior: Ambrosini / Kostis [F01] (as in A's plan).
CLASS_PRIOR = {"free": 0.33, "juxtavascular": 0.45, "juxtapleural": 0.22}

# Context tilts (multiplicative, then renormalised). Direction from the perifissural / juxtapleural
# literature (Ahn 2010, de Hoop 2012): juxtapleural nodules are more often solid and smooth. (verify)
TYPE_TILT = {
    "free": {"solid": 0.9, "part-solid": 1.1, "ground-glass": 1.3},
    "juxtavascular": {"solid": 1.0, "part-solid": 1.0, "ground-glass": 1.0},
    "juxtapleural": {"solid": 1.3, "part-solid": 0.8, "ground-glass": 0.6},
}
MARGIN_TILT = {
    "free": {"smooth": 0.95, "lobulated": 1.0, "spiculated": 1.15},
    "juxtavascular": {"smooth": 1.0, "lobulated": 1.0, "spiculated": 1.0},
    "juxtapleural": {"smooth": 1.5, "lobulated": 0.9, "spiculated": 0.6},
}


# ---- building ------------------------------------------------------------------------------------

def _norm(v):
    v = np.asarray(v, float)
    return v / v.sum()


def _counts():
    doc = json.loads((DATA / "lidc_counts.json").read_text())
    c = np.zeros((3, 4, 3))
    for r in doc["counts"]:
        c[TYPES.index(r["type"]), SIZES.index(r["size_bin"]), MARGINS.index(r["margin"])] = r["n"]
    return c, doc


def build() -> dict:
    c, stats = _counts()
    alpha = 1.0
    p_type = _norm(c.sum((1, 2)) + alpha)
    p_size = np.array([_norm(c[t].sum(1) + alpha) for t in range(3)])
    p_margin = np.array([[_norm(c[t, s] + alpha) for s in range(4)] for t in range(3)])
    cite_lidc = f"LIDC-IDRI aggregate radiologist ratings via pylidc, n={stats['n_used']} nodules (B_mapping/data/lidc_counts.json)"
    type_ctx, margin_ctx = {}, {}
    for k in CLASSES:
        type_ctx[k] = _norm(p_type * [TYPE_TILT[k][t] for t in TYPES]).round(6).tolist()
        mt = p_margin * np.array([MARGIN_TILT[k][m] for m in MARGINS])
        margin_ctx[k] = (mt / mt.sum(-1, keepdims=True)).round(6).tolist()
    nodes = [
        {"name": "tumor_type", "states": TYPES, "parents": [], "context_keys": ["placement_class"],
         "cpt_by_context": {k: _fix(v) for k, v in type_ctx.items()},
         "sources": [cite_lidc + ", Laplace alpha=1; texture 1-2 GGN, 3 part-solid, 4-5 solid",
                     "context tilt (verify): Ahn 2010, de Hoop 2012 (perifissural / juxtapleural nodules mostly solid)"]},
        {"name": "size_bin", "states": SIZES, "parents": ["tumor_type"], "context_keys": [],
         "cpt": [_fix(r) for r in p_size.round(6).tolist()],
         "sources": [cite_lidc + ", diameter bins 3/6/10/20/30 mm"]},
        {"name": "margin", "states": MARGINS, "parents": ["tumor_type", "size_bin"], "context_keys": ["placement_class"],
         "cpt_by_context": {k: [[_fix(r) for r in tt] for tt in v] for k, v in margin_ctx.items()},
         "sources": [cite_lidc + ", spiculation>=3 spiculated else lobulation>=3 lobulated",
                     "context tilt (verify): Ahn 2010, de Hoop 2012 (juxtapleural more often smooth)"]},
    ]
    doc = {
        "contract": "rulebook", "contract_version": CONTRACT_VERSION,
        "produced_by": {"letter": "B", "tool": "B_mapping.src.rulebook", "run_id": None,
                        "code_hash": code_hash([LETTER_DIR / "src"])},
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stub": False, "upstream": [],
        "rulebook_id": "lung-v1", "nodes": nodes,
    }
    doc["rulebook_hash"] = hash_json(doc, exclude=["rulebook_hash", "created_utc", "produced_by"])
    return doc


def _fix(row):
    """Make a row sum to exactly 1 after rounding."""
    row = list(row)
    row[int(np.argmax(row))] += round(1 - sum(row), 6)
    return [round(x, 6) for x in row]


# ---- exact reference -----------------------------------------------------------------------------

def ctx_key(node: dict, context: dict) -> str:
    return "|".join(str(context[k]) for k in node["context_keys"])


def node_table(node: dict, context: dict) -> np.ndarray:
    """CPT as array (parent state counts..., n_states) for this context."""
    raw = node["cpt_by_context"][ctx_key(node, context)] if "cpt_by_context" in node else node["cpt"]
    return np.asarray(raw, float)


def order(rulebook: dict) -> list:
    """Nodes in topological order (listed order is checked)."""
    seen, out = set(), []
    for n in rulebook["nodes"]:
        if any(p not in seen for p in n["parents"]):
            raise ValueError(f"node {n['name']} listed before its parents")
        seen.add(n["name"])
        out.append(n)
    return out


def joint_table(rulebook: dict, context: dict) -> dict:
    """Exact joint over all node states: {(state index per node in order): p}."""
    nodes = order(rulebook)
    idx = {n["name"]: i for i, n in enumerate(nodes)}
    tabs = [node_table(n, context) for n in nodes]
    out = {}
    for combo in itertools.product(*[range(len(n["states"])) for n in nodes]):
        p = 1.0
        for i, n in enumerate(nodes):
            row = tabs[i]
            for par in n["parents"]:
                row = row[combo[idx[par]]]
            p *= row[combo[i]]
            if p == 0:
                break
        if p > 0:
            out[combo] = float(p)
    return out


def ancestral_sample(rulebook: dict, context: dict, shots: int, rng) -> dict:
    """Classical baseline: forward sampling. Returns {combo: count}."""
    nodes = order(rulebook)
    idx = {n["name"]: i for i, n in enumerate(nodes)}
    tabs = [node_table(n, context) for n in nodes]
    draws = np.zeros((shots, len(nodes)), int)
    for i, n in enumerate(nodes):
        t = tabs[i]
        if not n["parents"]:
            draws[:, i] = rng.choice(len(n["states"]), size=shots, p=t)
            continue
        pidx = tuple(draws[:, idx[p]] for p in n["parents"])
        probs = t[pidx]  # (shots, n_states)
        u = rng.random(shots)[:, None]
        draws[:, i] = (u > np.cumsum(probs, 1)).sum(1).clip(max=len(n["states"]) - 1)
    out = {}
    for row in map(tuple, draws.tolist()):
        out[row] = out.get(row, 0) + 1
    return out


def contexts(rulebook: dict) -> list:
    """All context dicts the rulebook defines (product of context-key values seen in cpt_by_context)."""
    keys = sorted({k for n in rulebook["nodes"] for k in n["context_keys"]})
    if not keys:
        return [{}]
    vals = {k: set() for k in keys}
    for n in rulebook["nodes"]:
        for ck in n.get("cpt_by_context", {}):
            for k, v in zip(n["context_keys"], ck.split("|")):
                vals[k].add(v)
    return [dict(zip(keys, c)) for c in itertools.product(*[sorted(vals[k]) for k in keys])]


def tvd(p: dict, q: dict) -> float:
    return 0.5 * sum(abs(p.get(k, 0) - q.get(k, 0)) for k in set(p) | set(q))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="write data/rulebook_lung.json and class_prior.json")
    ap.add_argument("--joint", action="store_true")
    ap.add_argument("--context", default="free")
    args = ap.parse_args()
    if args.write:
        doc = build()
        RULEBOOK_PATH.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        PRIOR_PATH.write_text(json.dumps({
            "prior": CLASS_PRIOR, "source": "Ambrosini / Kostis [F01] (verify)",
            "note": "rulebook contract has no params/extra slot: sidecar, see CCR-B1"}, indent=2) + "\n")
        print("wrote", RULEBOOK_PATH.relative_to(RE_ROOT), PRIOR_PATH.relative_to(RE_ROOT))
    if args.joint:
        rb = json.loads(RULEBOOK_PATH.read_text())
        jt = joint_table(rb, {"placement_class": args.context})
        names = [n["name"] for n in rb["nodes"]]
        for combo, p in sorted(jt.items(), key=lambda kv: -kv[1])[:10]:
            print({nm: rb["nodes"][i]["states"][s] for i, (nm, s) in enumerate(zip(names, combo))}, round(p, 5))
        print("sum", round(sum(jt.values()), 12))
        shots = 10 ** 5
        emp = {k: v / shots for k, v in ancestral_sample(rb, {"placement_class": args.context}, shots,
                                                         np.random.default_rng(0)).items()}
        print("ancestral TVD @1e5:", round(tvd(jt, emp), 4))


if __name__ == "__main__":
    main()
