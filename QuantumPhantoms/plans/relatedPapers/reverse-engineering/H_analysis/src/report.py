"""Cohort manifest -> contract-valid validation_report.json (VICTRE-shaped validation harness).

    python -m H_analysis.src.report --cohort H_analysis/cohorts/stub.json --lidc-ref <run dir|none> \
        [--readers 30] [--sections all|realism,radiomics,utility,drift,certificate_stats,baseline]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import timezone
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from H_analysis.src import baseline, certstats, drift, manifest, radiomics_cmp, realism, utility  # noqa: E402
from shared import runrecord, seedhash, validate  # noqa: E402

SECTIONS = ["realism", "radiomics", "utility", "drift", "certificate_stats", "baseline"]
CONTRACT_BY_KIND = {"hybrids": "hybrid_volume", "draws": "tumor_draw", "rulebook": "rulebook",
                    "compiled_circuit": "compiled_circuit", "job_records": "quantum_job_record",
                    "certificates": "certificate", "witness": "witness_record", "memory": "memory_advantage_record",
                    "simulability": "simulability_report", "trajectories": "growth_trajectory",
                    "receipts": "receipt", "ledger": "ledger_entry"}
INSUFFICIENT = {"status": "insufficient input", "n": 0}


def _load_ref(ref_dir: str):
    if ref_dir == "none":
        return None
    d = Path(ref_dir)
    return json.loads((d / "lidc_ref.json").read_text()), np.load(d / "rois.npz")


def _split_real(ref: dict, seed_hex: str):
    """Real patients -> train / test halves (patient-disjoint)."""
    pats = sorted(ref["real_patients"])
    rng = seedhash.rng(seed_hex, "H.split")
    perm = list(rng.permutation(pats))
    return set(perm[: len(perm) // 2]), set(perm[len(perm) // 2:])


def build(cohort: dict, ref, readers: int, sections: list[str], tag_notes: str, rng_seed: str):
    """Compute all requested sections. Returns (sections dict, detail dict, figure data)."""
    hy = [manifest.load_hybrid(cohort, i) for i in range(len(cohort["obj"]["hybrids"]))]
    syn_m = [{"type": h["type"], "patient": h["host_scan_id"], "seed_source": h["seed_source"], "d_eq_mm": h["d_eq_mm"],
              **realism.lesion_metrics(h["hybrid"], h["mask"], h["host"])} for h in hy]
    real_m, real_f, syn_f = [], [], []
    real_items = []
    if ref:
        meta, arr = ref
        for it in meta["items"]:
            if it["kind"] == "nodule" and it["role"] == "real":
                img, mask = arr[it["key"] + "_roi"], arr[it["key"] + "_mask"]
                real_m.append({"type": it["type"], "patient": it["patient_id"], **realism.lesion_metrics(img, mask)})
                real_items.append(it)
                real_f.append({"type": it["type"], "patient": it["patient_id"],
                               "features": radiomics_cmp.extract(img, mask)})
    for h in hy:
        syn_f.append({"type": h["type"], "patient": h["host_scan_id"], "features": radiomics_cmp.extract(h["hybrid"], h["mask"])})
    out, detail = {}, {"per_lesion": syn_m, "real_per_lesion": real_m}
    want = set(SECTIONS if sections == ["all"] else sections)
    if "realism" in want:
        out["realism"] = realism.run(syn_m, real_m) if syn_m else dict(INSUFFICIENT)
    if "radiomics" in want:
        out["radiomics"] = radiomics_cmp.run(syn_f, real_f, cohort["seed"]) if syn_f else dict(INSUFFICIENT)
        detail["radiomics_per_feature"] = out["radiomics"].pop("per_feature", None)
        out["radiomics"]["per_feature_ref"] = "report_detail.json#/radiomics_per_feature"
    if "utility" in want:
        if ref and hy:
            meta, arr = ref
            train_p, test_p = _split_real(meta, cohort["seed"])
            rp = [(arr[i["key"] + "_roi"], i) for i in real_items]
            tr_pos = np.array([a for a, i in rp if i["patient_id"] in train_p])
            te_pos = np.array([a for a, i in rp if i["patient_id"] in test_p])
            te_types = [i["type"] for a, i in rp if i["patient_id"] in test_p]
            negs = [(arr[i["key"] + "_roi"], i) for i in meta["items"] if i["kind"] == "negative" and i["role"] == "real"]
            tr_neg = np.array([a for a, i in negs if i["patient_id"] in train_p])
            te_neg = np.array([a for a, i in negs if i["patient_id"] in test_p])
            if min(len(tr_pos), len(te_pos), len(tr_neg), len(te_neg)) == 0:
                out["utility"] = {**INSUFFICIENT, "needs": "real train/test positives and negatives"}
            else:
                u = utility.run(np.array([h["hybrid"] for h in hy]), np.array([h["host"] for h in hy]), tr_pos, tr_neg,
                                te_pos, te_neg, te_types, float(np.median([h["d_eq_mm"] for h in hy])),
                                cohort["seed"], readers)
                detail["utility_roc_scores"] = u.pop("_roc_scores", None)
                u["split"] = {"train_patients": len(train_p), "test_patients": len(test_p), "disjoint": True}
                out["utility"] = u
        else:
            out["utility"] = {**INSUFFICIENT, "needs": "LIDC reference run (--lidc-ref) and >= 1 hybrid"}
    if "drift" in want:
        out["drift"] = drift.run(cohort)
    if "certificate_stats" in want:
        out["certificate_stats"] = certstats.run(cohort)
    if "baseline" in want:
        out["baseline"] = baseline.run(cohort, out.get("drift", {}), out.get("certificate_stats", {}), syn_m, tag_notes)
    return out, detail


def make_figures(sec: dict, detail: dict, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    pt = sec.get("realism", {}).get("per_type", {})
    if pt:
        fig, axs = plt.subplots(1, 4, figsize=(11, 2.8))
        for ax, m in zip(axs, realism.METRICS):
            for k, (t, d) in enumerate(pt.items()):
                rs = d[m].get("real_summary", {})
                if rs.get("n"):
                    ax.plot([k, k], [rs["p5"], rs["p95"]], "k-", lw=3, alpha=0.3)
                    ax.plot(k, rs["p50"], "k_", ms=12)
                ax.plot([k] * len(d[m]["syn"]), d[m]["syn"], "o", ms=4)
            ax.set_xticks(range(len(pt)), list(pt), fontsize=7)
            ax.set_title(m, fontsize=8)
        fig.tight_layout(); fig.savefig(outdir / "h_realism.png", dpi=110); plt.close(fig)
    u = sec.get("utility", {})
    if "auc_train_syn" in u and detail.get("utility_roc_scores"):
        fig, ax = plt.subplots(figsize=(3.8, 3.4))
        for a, lab in (("S", "train synthetic"), ("R", "train real")):
            pos, neg = detail["utility_roc_scores"][a]
            thr = np.sort(np.r_[pos, neg])[::-1]
            ax.plot([np.mean(np.array(neg) >= t) for t in thr], [np.mean(np.array(pos) >= t) for t in thr], label=lab)
        ax.plot([0, 1], [0, 1], "k:", lw=0.7); ax.legend(fontsize=7); fig.tight_layout()
        fig.savefig(outdir / "h_utility_roc.png", dpi=110); plt.close(fig)
    d = sec.get("drift", {}).get("by_sim_label", {})
    if isinstance(d, dict) and d and "status" not in d:
        fig, ax = plt.subplots(figsize=(4, 3))
        for lab, v in d.items():
            ax.bar([f"{n}\n{lab[-8:]}" for n in v["per_node"]], [m["tvd"] for m in v["per_node"].values()])
        ax.set_ylabel("TVD vs rulebook"); fig.tight_layout(); fig.savefig(outdir / "h_drift.png", dpi=110); plt.close(fig)
    c = sec.get("certificate_stats", {}).get("certificates", {}).get("by_sim_label", {})
    if c:
        fig, ax = plt.subplots(figsize=(3.8, 3))
        ax.bar(range(len(c)), [v["chsh_S"]["mean"] for v in c.values()], yerr=[v["chsh_S"]["std"] for v in c.values()])
        ax.axhline(2, ls="--", c="k"); ax.axhline(2 * np.sqrt(2), ls=":", c="k")
        ax.set_xticks(range(len(c)), [k[-12:] for k in c], fontsize=7); ax.set_ylabel("CHSH S")
        fig.tight_layout(); fig.savefig(outdir / "h_certstats.png", dpi=110); plt.close(fig)
    r = sec.get("radiomics", {})
    if "c2st" in r and "auc" in r["c2st"]:
        fig, ax = plt.subplots(figsize=(3.4, 3))
        ax.bar(["C2ST", "null"], [r["c2st"]["auc"], r["null"].get("c2st_auc") or 0.5]); ax.axhline(0.5, ls=":", c="k")
        ax.set_ylabel("AUC"); fig.tight_layout(); fig.savefig(outdir / "h_radiomics.png", dpi=110); plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cohort", required=True)
    ap.add_argument("--lidc-ref", default="none")
    ap.add_argument("--readers", type=int, default=30)
    ap.add_argument("--sections", default="all")
    ap.add_argument("--notes", default="")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--figures", default=None, help="figure dir (default: run dir)")
    a = ap.parse_args(argv)
    cohort = manifest.load(a.cohort)  # aborts (SystemExit) on any shared.validate error, nothing written
    ref = _load_ref(a.lidc_ref)
    tag = a.tag or Path(a.cohort).stem
    notes = (f"H validation report, cohort '{tag}'. Classical analysis only; quantum numbers are reported with "
             f"their simulation labels, classical baselines and simulability numbers. hardware=null; "
             f"certification-ready, not certified (simulated). {a.notes}").strip()
    run = runrecord.start_run("H_analysis", f"report-{tag}", seed_hex=cohort["seed"], tool="H_analysis.src.report")
    secs, detail = build(cohort, ref, a.readers, a.sections.split(","), notes, cohort["seed"])
    for s in SECTIONS:
        secs.setdefault(s, {"status": "insufficient input", "n": 0, "note": "section not requested"})
    for kind, paths in cohort["files"].items():
        for p in paths:
            run.add_input(p, CONTRACT_BY_KIND[kind])
    if ref:
        pass
    hyb = [r for r, k in zip(run.inputs, [k for k, ps in cohort["files"].items() for _ in ps]) if k == "hybrids"]
    report = {
        "contract": "validation_report", "contract_version": "1.0.0",
        "produced_by": {"letter": "H", "tool": "H_analysis.src.report", "run_id": run.path.name,
                        "code_hash": run.code_hash},
        "created_utc": run.created.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stub": all(o.get("stub", False) for k in cohort["obj"] for o in cohort["obj"][k] if isinstance(o, dict)),
        "upstream": run.inputs,
        "hybrid_refs": [{"path": r["path"], "sha256": r["sha256"]} for r in hyb],
        **secs, "notes": notes}
    out = run.path / "validation_report.json"
    out.write_text(json.dumps(report, indent=1, default=float) + "\n")
    (run.path / "report_detail.json").write_text(json.dumps(detail, indent=1, default=float) + "\n")
    make_figures(secs, detail, Path(a.figures) if a.figures else run.path)
    _, errs = validate.validate_file(out)
    if errs:
        print("validation_report FAILED shared.validate:\n  " + "\n  ".join(errs))
        return 1
    if not secs["baseline"].get("honesty", {"ok": True})["ok"]:
        print("honesty gate FAILED:", secs["baseline"]["honesty"])
        return 1
    run.add_output(out, "validation_report")
    run.finish(notes=notes)
    for s in SECTIONS:
        v = secs[s]
        print(f"  {s:18s} n={v.get('n', '-')} {v.get('status', 'ok')}")
    print(f"OK {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
