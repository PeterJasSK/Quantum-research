"""Write H's cohort manifest (format: H_analysis/cohorts/stub.json) from the chain's real contract files.

Paths in the manifest are relative to the manifest file, as H_analysis.src.manifest expects.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from INT_integration.src.stages import LEDGER, RE_ROOT, rel

LISTS = {"draws": ["B.draw"], "job_records": ["C.qjr", "B.qjr", "D.qjr_lineage", "D.qjr_qmachine", "D.qjr_qca"],
         "certificates": ["C.certificate"], "witness": ["D.witness_lineage", "D.witness_qca"], "memory": ["D.memory"],
         "simulability": ["D.simulability", "D.bp_b"], "trajectories": ["E.trajectory"], "receipts": ["G.receipt"]}


def write(ctx: dict, chain_dir: Path) -> dict:
    out = chain_dir / "cohort.json"

    def p(key_or_path) -> str:
        target = RE_ROOT / (ctx[key_or_path] if key_or_path in ctx else key_or_path)
        return Path(os.path.relpath(target, out.parent)).as_posix()

    manifest = {"seed_note": f"INT chain {chain_dir.name}: one tumour, n = 1 (not powered); seeds descend from "
                             f"certificate {ctx.get('C.certificate')}",
                "hybrids": [{"path": p("F.hybrid"), "seed_source": "certified"}]}
    for name, keys in LISTS.items():
        manifest[name] = [p(k) for k in keys if k in ctx]
    manifest.update({"rulebook": p("B.rulebook"), "compiled_circuit": p("B.circuit"), "ledger": p(rel(LEDGER))})
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    return {"INT.cohort": rel(out)}
