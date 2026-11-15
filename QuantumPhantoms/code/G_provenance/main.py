"""Section G: lineage record. A replayable record of what produced the cohort -> lineage_record.json + ledger.jsonl.

The record holds the sha256 of every section file and image, the code hash of every section, the git state, the
backend and the job ids. Its own hash is appended to a hash-chained ledger in the run directory, so any later edit
to a file, to the record or to the ledger is visible:

    python -m G_provenance.main <run directory>          # prints every difference; exit 1 if any

Unsigned, and with no commit-before-draw ordering. Privacy rests on parameter-only construction (no patient voxels
enter a generator), not on this record.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import CODE_ROOT, PROJECT_ROOT, runio
from common.runio import Ctx

FILES = ("backend.json", "cohort_params.json", "quantum_run.json", "rulebook.json", "certificate.json", "claims.json",
         "dscale/dscale_run.json", "dscale/seed_shapes.npz", "dscale/seed_tiles.json", "dscale/plan.json", "sites.json",
         "growth.json", "tiles.json")
GLOBS = ("tiles/*.png", "qhard/**/*.json", "jobs/*.json")
ZERO = "0" * 64


def _hashes(run_dir: Path) -> dict[str, str]:
    files = [run_dir / n for n in FILES] + [f for pat in GLOBS for f in sorted(run_dir.glob(pat))]
    return {f.relative_to(run_dir).as_posix(): runio.sha256_file(f) for f in files if f.is_file()}


def _entry(index: int, prev: str, record_sha: str) -> dict:
    e = {"index": index, "prev_hash": prev, "record_sha256": record_sha,
         "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    return e | {"entry_hash": hashlib.sha256(runio.canonical_json(e)).hexdigest()}


def _ledger(run_dir: Path) -> list[dict]:
    f = run_dir / "ledger.jsonl"
    return [json.loads(x) for x in f.read_text().splitlines() if x.strip()] if f.is_file() else []


def run(ctx: Ctx) -> None:
    d = ctx.run_dir
    record = {"record": "run lineage", "run": d.name, "backend": runio.load_json(d / "backend.json"),
              "job_ids": {f.stem: runio.load_json(f)["job_id"] for f in sorted(d.glob("jobs/*.json"))},
              "files": _hashes(d),
              "code_hash": {p.name: runio.code_hash(p) for p in sorted(CODE_ROOT.iterdir()) if (p / "__init__.py").is_file()},
              "git": runio.git_state(PROJECT_ROOT)}
    runio.save_json(d / "lineage_record.json", record)
    sha = hashlib.sha256(runio.canonical_json(runio.load_json(d / "lineage_record.json"))).hexdigest()
    led = _ledger(d)
    led.append(_entry(len(led), led[-1]["entry_hash"] if led else ZERO, sha))
    (d / "ledger.jsonl").write_text("".join(json.dumps(e) + "\n" for e in led))
    print(f"  {len(record['files'])} files hashed; ledger entry {led[-1]['index']} ({led[-1]['entry_hash'][:12]}...)")


def verify(run_dir: Path) -> list[str]:
    rec = runio.load_json(run_dir / "lineage_record.json")
    if rec is None:
        return ["lineage_record.json missing"]
    now, errs = _hashes(run_dir), []
    errs += [f"{n}: file missing" for n in rec["files"] if n not in now]
    errs += [f"{n}: content changed since the record" for n, h in rec["files"].items() if n in now and now[n] != h]
    errs += [f"{n}: file not in the record" for n in now if n not in rec["files"]]
    led, prev = _ledger(run_dir), ZERO
    for i, e in enumerate(led):
        body = {k: v for k, v in e.items() if k != "entry_hash"}
        if e["index"] != i or e["prev_hash"] != prev or hashlib.sha256(runio.canonical_json(body)).hexdigest() != e["entry_hash"]:
            errs.append(f"ledger entry {i}: chain broken")
        prev = e["entry_hash"]
    sha = hashlib.sha256(runio.canonical_json(rec)).hexdigest()
    if not any(e["record_sha256"] == sha for e in led):
        errs.append("lineage_record.json: its hash is not in the ledger (record edited or ledger replaced)")
    return errs


if __name__ == "__main__":
    errors = verify(Path(sys.argv[1]).resolve())
    for err in errors:
        print("  CHANGED:", err)
    print("lineage record verifies: every file matches" if not errors else f"{len(errors)} difference(s)")
    sys.exit(1 if errors else 0)
