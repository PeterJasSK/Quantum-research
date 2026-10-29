"""Pilot cohort planner (pre-INT). H never imports F or C: it writes input variants plus a shell script that runs their CLIs.

    python -m H_analysis.src.pilot plan --hosts 20 --per-host 3
    bash H_analysis/runs/<ts>-pilot/commands.sh                 # developer runs this (F ~hours, C certify minutes)
    python -m H_analysis.src.report --cohort H_analysis/runs/<ts>-pilot/cohort.json --lidc-ref <lidc-ref run>

Half the members are seeded from a certificate (seed_source certified), half from os.urandom (prng).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from shared import STUBS, RE_ROOT, runrecord, seedhash

TYPES = ["solid", "part-solid", "ground-glass"]
LIDC_ROOT = Path(os.environ.get("LIDC_ROOT", "~/data/LIDC-IDRI")).expanduser()
N_CERT_QUANTUM = {"ideal": 5, "heron": 5}
N_CERT_CLASSICAL = 2


def _rebase(obj, src_dir: Path, dst_dir: Path):
    """Rewrite relative `path` values (file refs / upstream) so a copied contract file still points at its inputs."""
    if isinstance(obj, dict):
        return {k: (os.path.relpath((src_dir / v).resolve(), dst_dir.resolve())
                    if k == "path" and isinstance(v, str) and not os.path.isabs(v) else _rebase(v, src_dir, dst_dir))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [_rebase(x, src_dir, dst_dir) for x in obj]
    return obj


def _variant(stub_name: str, filename: str, dst: Path, patch: dict) -> Path:
    src = STUBS / stub_name / filename
    obj = _rebase(json.loads(src.read_text()), src.parent, dst.parent)
    obj.update(patch)
    obj["stub"] = True
    obj["produced_by"] = {**obj["produced_by"], "letter": "H", "tool": "H_analysis.src.pilot"}
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(obj, indent=1) + "\n")
    return dst


def plan(hosts: int, per_host: int) -> Path:
    sel = json.loads((LIDC_ROOT / "f_render_selection.json").read_text())[:hosts]
    seed = seedhash.sha256_bytes(b"H.pilot")
    run = runrecord.start_run("H_analysis", "pilot", seed_hex=seed, tool="H_analysis.src.pilot")
    root = run.path
    rel = lambda p: os.path.relpath(p, RE_ROOT)  # noqa: E731
    lines = ["#!/usr/bin/env bash", "# Pilot cohort (pre-INT, under-powered). cwd must be reverse-engineering/.",
             "# NOTE: --sites must be A's site_candidates.json for each host; the stub sites will NOT fall in a real",
             "#       host's lungs. Set SITES_<patient> or replace the SITES default below before running.",
             "set -euo pipefail", f'PILOT="{rel(root)}"', 'SITES_DEFAULT="shared/stubs/site_candidates/sites.json"', ""]
    hybrids, n = [], 0
    for hi, host in enumerate(sel):
        pid = host["patient_id"]
        hdir = root / "members" / pid
        lines += [f"# ---- host {pid}",
                  f'python -m F_render.src.host_masks --lidc {pid} --out "$PILOT/members/{pid}/host"',
                  f'python -m F_render.src.fingerprint --masks "$PILOT/members/{pid}/host/anatomy_masks.json" '
                  f'--slice-thickness {host["slice_thickness"]} --out "$PILOT/members/{pid}/fingerprint"']
        for k in range(per_host):
            src_kind = "certified" if (n % 2 == 0) else "prng"
            typ = TYPES[n % 3]
            r = seedhash.rng(seed, f"H.pilot.{pid}.{k}")
            shape_seed = r.bytes(8).hex()
            ext_seed = (r.bytes(32).hex() if src_kind == "certified" else os.urandom(32).hex())
            mid = f"{pid}-{k}"
            draw = _variant("tumor_draw", "tumor_draw.json", hdir / f"draw_{k}.json",
                            {"draw_id": f"P{mid}", "shape_seed_hex": shape_seed, "type": typ})
            cert = _variant("certificate", "certificate.json", hdir / f"cert_{k}.json",
                            {"extracted_seed_hex": ext_seed})
            lines.append(
                f'python -m F_render.src.render --draw "$PILOT/members/{pid}/{draw.name}" '
                f'--certificate "$PILOT/members/{pid}/{cert.name}" --masks "$PILOT/members/{pid}/host/anatomy_masks.json" '
                f'--sites "${{SITES_{pid.replace("-", "_")}:-$SITES_DEFAULT}}" '
                f'--fingerprint "$PILOT/members/{pid}/fingerprint/scanner_fingerprint.json" '
                f'--out "$PILOT/members/{pid}/render_{k}" --tag pilot')
            hybrids.append({"path": f"members/{pid}/render_{k}/hybrid_volume.json", "seed_source": src_kind,
                            "_draw": f"members/{pid}/{draw.name}"})
            n += 1
        lines.append("")
    certs = []
    lines.append("# ---- C certificates; each run dir is copied next to the pilot cohort so paths are predictable")
    jobs = ([("ideal", "quantum", i) for i in range(N_CERT_QUANTUM["ideal"])]
            + [("heron", "quantum", i) for i in range(N_CERT_QUANTUM["heron"])]
            + [("ideal", "classical", i) for i in range(N_CERT_CLASSICAL)])
    for mode, settings, i in jobs:
        name = f"{mode}_{settings}_{i}"
        lines += [f"python -m C_certificate.src.certify --mode {mode} --settings {settings}",
                  f'LAST=$(ls -dt C_certificate/runs/*/ | head -1); mkdir -p "$PILOT/certs/{name}"',
                  f'cp "$LAST"certificate.json "$LAST"quantum_job_record.json "$PILOT/certs/{name}/"']
        certs.append(f"certs/{name}/certificate.json")
    cohort = {"seed_note": "PILOT, pre-INT, under-powered: H-local stub-flagged input variants rendered by F on LIDC "
                           "hosts; B/D/G-side files are stubs. Half of the hybrids are seeded from a certificate, "
                           "half from os.urandom.",
              "hybrids": [{k: v for k, v in h.items() if not k.startswith("_")} for h in hybrids],
              "draws": [h["_draw"] for h in hybrids],
              "rulebook": os.path.relpath(STUBS / "rulebook/rulebook.json", root),
              "compiled_circuit": os.path.relpath(STUBS / "compiled_circuit/compiled_circuit.json", root),
              "job_records": [os.path.relpath(STUBS / "quantum_job_record/quantum_job_record.json", root)],
              "certificates": certs,
              "witness": [os.path.relpath(STUBS / "witness_record/witness_record.json", root)],
              "memory": [os.path.relpath(STUBS / "memory_advantage_record/memory_advantage_record.json", root)],
              "simulability": [os.path.relpath(STUBS / "simulability_report/simulability_report.json", root)],
              "trajectories": [os.path.relpath(STUBS / "growth_trajectory/growth_trajectory.json", root)],
              "receipts": [os.path.relpath(STUBS / "receipt/receipt.json", root)],
              "ledger": os.path.relpath(STUBS / "ledger_entry/ledger.jsonl", root)}
    (root / "commands.sh").write_text("\n".join(lines) + "\n")
    (root / "cohort.json").write_text(json.dumps(cohort, indent=1) + "\n")
    run.finish(notes="pilot plan")
    print(f"{len(hybrids)} members over {len(sel)} hosts, {len(certs)} certificates\n-> {root}")
    return root


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--hosts", type=int, default=20)
    p.add_argument("--per-host", type=int, default=3)
    a = ap.parse_args(argv)
    plan(a.hosts, a.per_host)
    return 0


if __name__ == "__main__":
    sys.exit(main())
