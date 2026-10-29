"""`baseline` section: classical counterpart of every quantum number, seed-source arm, honesty gates."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from scipy import stats

from H_analysis.src import drift
from shared import seedhash

H = Path(__file__).resolve().parents[1]
FORBIDDEN = [r"more realistic because quantum", r"quantum biology", r"classically impossible"]


def ancestral_cohort(rulebook: dict, context: dict, n: int, seed_hex: str) -> dict:
    """Classical ancestral sampling of the BN, n samples -> per-node state-count vectors."""
    rng = seedhash.rng(seed_hex, "H.ancestral")
    nodes = rulebook["nodes"]
    names = [x["name"] for x in nodes]
    cnt = {nm: np.zeros(len(x["states"])) for nm, x in zip(names, nodes)}
    for _ in range(n):
        s = {}
        for x in nodes:
            t = drift._table(x, context)
            for pa in x["parents"]:
                t = t[s[pa]]
            s[x["name"]] = int(rng.choice(len(t), p=t))
            cnt[x["name"]][s[x["name"]]] += 1
    return cnt


def seed_source_arm(cohort: dict, per_lesion: list[dict]) -> dict:
    """KS per realism metric between hybrids seeded from certificates vs PRNG."""
    arms = {"certified": [], "prng": []}
    for m in per_lesion:
        if m.get("seed_source") in arms:
            arms[m["seed_source"]].append(m)
    n = {k: len(v) for k, v in arms.items()}
    if min(n.values()) < 5:
        return {"status": "insufficient input", "n": n}
    out = {"n": n, "per_metric": {}}
    for k in ("hu_mean", "hu_std", "edge_width_mm", "shell_sigma_ratio"):
        a = [m[k] for m in arms["certified"] if np.isfinite(m.get(k, np.nan))]
        b = [m[k] for m in arms["prng"] if np.isfinite(m.get(k, np.nan))]
        if len(a) >= 3 and len(b) >= 3:
            r = stats.ks_2samp(a, b)
            out["per_metric"][k] = {"ks_D": float(r.statistic), "ks_p": float(r.pvalue)}
    out["any_significant_p<0.05"] = any(v["ks_p"] < 0.05 for v in out["per_metric"].values())
    out["expectation"] = "no difference: the quantum stage supplies provenance (L0) and evidence, not realism"
    return out


def honesty(cohort: dict, report_sections: dict, notes: str) -> dict:
    texts = [notes]
    readme = H / "README.md"
    if readme.exists():  # lines that list the forbidden phrases themselves are marked "forbidden" and skipped
        texts.append("\n".join(l for l in readme.read_text().splitlines() if "forbidden" not in l.lower()))
    hits = [pat for pat in FORBIDDEN for t in texts if re.search(pat, t, re.I)]
    o = cohort["obj"]
    claim_levels = sorted({r["claim_level"] for k in ("certificates", "witness", "memory") for r in o[k]
                           if "claim_level" in r})
    labelled = all("sim_label" in r for k in ("certificates", "witness", "memory", "job_records", "simulability")
                   for r in o[k])
    no_hw = all(r.get("hardware") is None for k in ("certificates", "witness", "memory", "job_records", "simulability")
                for r in o[k])
    ok = not hits and labelled and no_hw and not any(l in ("L2", "L3") for l in claim_levels)
    return {"ok": ok, "claim_levels_present": claim_levels, "every_quantum_number_sim_labelled": labelled,
            "no_hardware_fields_set": no_hw, "forbidden_phrase_hits": hits}


def run(cohort: dict, drift_sec: dict, cert_sec: dict, per_lesion: list[dict], notes: str) -> dict:
    o = cohort["obj"]
    pairs = []
    for lab, d in cert_sec.get("certificates", {}).get("by_sim_label", {}).items():
        pairs.append({"quantity": "CHSH S (mean)", "quantum_value": d["chsh_S"]["mean"], "classical_value": 2.0,
                      "note": "classical local-hidden-variable bound", "sim_label": lab})
    cls_runs = [c for c in o["certificates"] if c["status"] != "pass"]
    for c in cls_runs:
        pairs.append({"quantity": "CHSH S, classical settings run", "quantum_value": c["chsh_S"],
                      "classical_value": 2.0, "note": "status=" + c["status"], "sim_label": c["sim_label"]})
    for e, d in cert_sec.get("witnesses", {}).items() if isinstance(cert_sec.get("witnesses"), dict) else []:
            pass
    for e, d in cert_sec.get("witnesses", {}).items():
        if isinstance(d, dict) and "threshold" in d:
            pairs.append({"quantity": f"witness {e}", "quantum_value": d["observable_means"],
                          "classical_value": d["threshold"], "note": "separable bound = threshold",
                          "sim_label": d["sim_label"]})
    for m in o["memory"]:
        pairs.append({"quantity": "memory: C_q vs C_mu (bits)", "quantum_value": m["C_q_bits"],
                      "classical_value": m["C_mu_bits"], "note": "C_q <= C_mu expected; passed=" + str(m["passed"]),
                      "sim_label": m["sim_label"]})
    for h, s in cert_sec.get("simulability", {}).items():
        if isinstance(s, dict) and "fidelity_vs_sim" in s:
            pairs.append({"quantity": "BP simulation fidelity", "quantum_value": s["fidelity_vs_sim"],
                          "classical_value": s["fidelity_vs_sim"], "note": f"bond_dim={s['bond_dim']}: circuit is "
                          "classically simulable", "sim_label": s["sim_label"]})
    anc = None
    if o["rulebook"] and o["compiled_circuit"] and isinstance(drift_sec.get("by_sim_label"), dict):
        rb, cc = o["rulebook"][0], o["compiled_circuit"][0]
        exact = {k: np.array(v) for k, v in drift_sec["exact_marginals"].items()}
        for lab, d in drift_sec["by_sim_label"].items():
            if not isinstance(d, dict) or "per_node" not in d or not d["n"]:
                continue
            cnt = ancestral_cohort(rb, cc["context"], d["n"], cohort["seed"])
            for nm, m in d["per_node"].items():
                v = cnt[nm]
                pairs.append({"quantity": f"drift TVD node {nm}", "quantum_value": m["tvd"],
                              "classical_value": drift.tvd(exact[nm], v / v.sum()),
                              "note": f"classical ancestral cohort, same size n={d['n']}", "sim_label": lab})
    out = {"pairs": pairs, "seed_source_arm": seed_source_arm(cohort, per_lesion), "n": len(pairs)}
    out["honesty"] = honesty(cohort, {}, notes)
    return out
