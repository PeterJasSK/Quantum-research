"""`certificate_stats` section: certificates, witnesses, memory advantage, simulability, receipts and ledger.

Every number carries the record's own `sim_label`. No hardware numbers exist (hardware is null throughout).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from shared import validate

CERT_STATUS = "certification-ready, not certified (simulated)"


def _summary(vals):
    a = np.asarray(vals, float)
    return {"mean": float(a.mean()), "std": float(a.std()), "min": float(a.min()), "max": float(a.max())}


def _jobref_label(c: dict, i: int, kind: str, rec: dict, files: dict):
    """sim_label cross-check against the linked job record (when present)."""
    ref = rec.get("job_record_ref")
    if not ref:
        return None
    jp = (files[kind][i].parent / ref["path"]).resolve()
    return json.loads(jp.read_text())["sim_label"] if jp.exists() else None


def run(cohort: dict) -> dict:
    o, f = cohort["obj"], cohort["files"]
    out: dict = {"hardware": None, "certification_status": CERT_STATUS}
    certs = o["certificates"]
    by: dict = {}
    for i, c in enumerate(certs):
        lab = c["sim_label"]
        link = _jobref_label(cohort, i, "certificates", c, f)
        by.setdefault(lab, []).append((c, link))
    out["certificates"] = {"n": len(certs), "by_sim_label": {}}
    for lab, lst in by.items():
        cs = [c for c, _ in lst]
        passed = [c for c in cs if c["status"] == "pass"]
        out["certificates"]["by_sim_label"][lab] = {
            "n": len(cs), "pass_rate": len(passed) / len(cs),
            "chsh_S": _summary([c["chsh_S"] for c in cs]),
            "h_min_per_round": _summary([c["h_min_per_round"] for c in cs]),
            "certified_bits": _summary([c["certified_bits"] for c in cs]),
            "extractor_output_bits": _summary([c["extractor"]["output_bits"] for c in cs]),
            "sim_label_matches_job_record": all(l is None or l == lab for _, l in lst),
            "failed_runs": [{"chsh_S": c["chsh_S"], "status": c["status"]} for c in cs if c["status"] != "pass"]}
    if not certs:
        out["certificates"]["status"] = "insufficient input"
    wit: dict = {}
    for w in o["witness"]:
        e = w["witness_expression"]
        d = wit.setdefault(e, {"n": 0, "values": [], "threshold": w["threshold"], "passed": 0, "bases": set(),
                               "sim_label": w["sim_label"]})
        d["n"] += 1
        d["passed"] += bool(w["passed"])
        d["bases"] |= set(w["bases"])
        d["values"].append({k: v["value"] for k, v in w["observables"].items()})
    out["witnesses"] = {}
    for e, d in wit.items():
        keys = sorted({k for v in d["values"] for k in v})
        out["witnesses"][e] = {"n": d["n"], "pass_rate": d["passed"] / d["n"], "threshold": d["threshold"],
                               "observable_means": {k: float(np.mean([v[k] for v in d["values"] if k in v])) for k in keys},
                               "bases": sorted(d["bases"]), "sim_label": d["sim_label"],
                               "flag_single_basis": len(d["bases"]) < 2}
    if not wit:
        out["witnesses"] = {"status": "insufficient input", "n": 0}
    mem = o["memory"]
    out["memory"] = ([{"process": m["process_description"], "C_mu_bits": m["C_mu_bits"], "C_q_bits": m["C_q_bits"],
                       "C_q_measured": m["C_q_measured"], "passed": m["passed"], "sim_label": m["sim_label"]}
                      for m in mem] if mem else {"status": "insufficient input", "n": 0})
    sims = {}
    for s in o["simulability"]:
        for c in s["circuits"]:
            sims[c["circuit_hash"]] = {"method": c["method"], "bond_dim": c["bond_dim"],
                                       "fidelity_vs_sim": c["fidelity_vs_sim"], "sim_label": s["sim_label"]}
    out["simulability"] = sims if sims else {"status": "insufficient input", "n": 0}
    circuit_hashes = {j["transpiled_hash"] for j in o["job_records"]}
    out["bp_simulability_join"] = {
        h: sims.get(h, "not provided") for h in sorted(circuit_hashes)} if circuit_hashes else {}
    rec = {"n": len(f["receipts"]), "validation": []}
    for p in f["receipts"]:
        _, errs = validate.validate_file(p)
        rec["validation"].append({"file": p.name, "result": "OK" if not errs else errs})
    if f["ledger"]:
        _, errs = validate.validate_file(f["ledger"][0])
        rec["ledger"] = {"result": "OK" if not errs else errs, "entries": len(o["ledger"][0]) if o["ledger"] else 0}
    out["receipts"] = rec if (f["receipts"] or f["ledger"]) else {"status": "insufficient input", "n": 0}
    out["n"] = len(certs) + len(o["witness"]) + len(mem) + len(f["receipts"])
    return out
