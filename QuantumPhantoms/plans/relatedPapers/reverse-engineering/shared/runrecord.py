"""Run-record writer (epic §3 Logging): one directory + run.json per run.

    run = start_run("C_certificate", "chsh-heron", seed_hex=seed, sim_mode="heron")
    counts, thash, job_id = run_counts(circ, "heron", 4000, seed=7)
    run.add_job(job_id, thash, 4000, counts)
    run.add_output("C_certificate/runs/.../certificate.json", "certificate")
    run.finish("first heron CHSH")

run.json is validated against contracts/run_record.schema.json before it is written.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from shared import CONTRACT_VERSION, RE_ROOT, SHARED
from shared.seedhash import code_hash, git_state, sha256_file


def _letter_of(letter_dir: Path) -> str:
    m = re.match(r"^([A-H])_", letter_dir.name)
    return m.group(1) if m else "stub"


def _utc(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


class Run:
    def __init__(self, path: Path, letter: str, tag: str, created: datetime, seed_hex: str | None,
                 sim_mode: str | None, code_paths: list[Path], include_git: bool, tool: str):
        self.path = path
        self.letter = letter
        self.tag = tag
        self.created = created
        self.seed_hex = seed_hex
        self.sim_mode = sim_mode
        self.code_hash = code_hash(code_paths)
        self.git = git_state() if include_git else None
        self.tool = tool
        self.jobs: list[dict] = []
        self.inputs: list[dict] = []
        self.outputs: list[dict] = []

    def _ref(self, p: str | Path, contract: str) -> dict:
        """Relative paths: run-dir-relative if the file exists there, else relative to the RE root."""
        p = Path(p)
        if not p.is_absolute():
            p = self.path / p if (self.path / p).exists() else RE_ROOT / p
        rel = p.resolve().relative_to(self.path.resolve(), walk_up=True).as_posix()
        return {"contract": contract, "path": rel, "sha256": sha256_file(p)}

    def add_job(self, job_id: str, transpiled_hash: str, shots: int, counts: dict) -> Path:
        f = self.path / f"counts_{job_id}.json"
        f.write_text(json.dumps(dict(sorted(counts.items())), indent=1) + "\n")
        self.jobs.append({"job_id": job_id, "transpiled_hash": transpiled_hash, "shots": shots,
                          "counts_file": {"path": f.name, "sha256": sha256_file(f)}})
        return f

    def add_input(self, path: str | Path, contract: str) -> None:
        self.inputs.append(self._ref(path, contract))

    def add_output(self, path: str | Path, contract: str) -> None:
        self.outputs.append(self._ref(path, contract))

    def record(self, notes: str = "") -> dict:
        sim = None
        if self.sim_mode:
            from shared.simbackend import REFERENCE_FAKE, calibration_snapshot, sim_label
            sim = {"mode": self.sim_mode, "sim_label": sim_label(self.sim_mode), "fake_backend": REFERENCE_FAKE,
                   "calibration_snapshot": calibration_snapshot()}
        return {
            "contract": "run_record",
            "contract_version": CONTRACT_VERSION,
            "produced_by": {"letter": self.letter, "tool": self.tool, "run_id": self.path.name,
                            "code_hash": self.code_hash},
            "created_utc": _utc(self.created),
            "stub": self.letter == "stub",
            "upstream": self.inputs,
            "run_id": self.path.name,
            "letter": self.letter,
            "tag": self.tag,
            "code_hash": self.code_hash,
            "git": self.git,
            "seed_hex": self.seed_hex,
            "sim": sim,
            "jobs": self.jobs,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "notes": notes,
        }

    def finish(self, notes: str = "") -> Path:
        from shared.validate import validate_file

        f = self.path / "run.json"
        f.write_text(json.dumps(self.record(notes), indent=2, ensure_ascii=False) + "\n")
        _, errs = validate_file(f)
        if errs:
            raise ValueError(f"{f} violates run_record contract:\n  " + "\n  ".join(errs))
        return f


def start_run(letter_dir: str | Path, tag: str, *, seed_hex: str | None = None, sim_mode: str | None = None,
              tool: str = "", created: datetime | None = None, run_id: str | None = None,
              include_git: bool = True) -> Run:
    """Create <letter_dir>/runs/<YYYYmmdd-HHMMSS>-<tag>/ and return a Run.

    code_hash covers the letter's .py files plus shared/. `created`, `run_id` and
    include_git=False exist only so stubs regenerate byte-identically.
    """
    letter_dir = Path(letter_dir)
    if not letter_dir.is_absolute():
        letter_dir = RE_ROOT / letter_dir
    created = created or datetime.now(timezone.utc)
    run_id = run_id or f"{created.strftime('%Y%m%d-%H%M%S')}-{tag}"
    path = letter_dir / "runs" / run_id
    path.mkdir(parents=True, exist_ok=True)
    code_paths = [SHARED] if letter_dir.resolve() == SHARED.resolve() else [letter_dir, SHARED]
    return Run(path, _letter_of(letter_dir), tag, created, seed_hex, sim_mode, code_paths, include_git,
               tool or f"{letter_dir.name}:{tag}")
