"""Manual-evidence tamper check (AC-12): copy the signed series, flip one voxel in one slice, run G's verify.

Expected: `TAMPER DETECTED` with the flipped slice index in the voxels check. Not the 20-case R19 repro.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pydicom

from INT_integration.src.stages import G_RUNS, RE_ROOT, StageFail, rel


def run(ctx: dict, chain_dir: Path) -> dict:
    src = RE_ROOT / ctx["G.series"]
    dst = chain_dir / "tamper" / "series"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    files = sorted(dst.glob("*.dcm"))
    if not files:
        raise StageFail(f"no .dcm files in {src}")
    f = files[len(files) // 2]
    ds = pydicom.dcmread(f)
    arr = ds.pixel_array.copy()
    y, x = arr.shape[0] // 2, arr.shape[1] // 2
    arr[y, x] = arr[y, x] + 1
    ds.PixelData = np.ascontiguousarray(arr, dtype=arr.dtype).tobytes()
    ds.save_as(f, enforce_file_format=True)

    before = {p.name for p in G_RUNS.iterdir()} if G_RUNS.is_dir() else set()
    argv = [ctx["python"], "-m", "G_provenance.src.verify", rel(dst), "--trusted",
            "G_provenance/runs/keys/trusted_keys.json"]
    r = subprocess.run(argv, cwd=RE_ROOT, capture_output=True, text=True)
    new = sorted(p for p in G_RUNS.iterdir() if p.name not in before and p.is_dir())
    report = json.loads((new[-1] / "verify_report.json").read_text()) if new else {}
    where = next((c["where"] for c in report.get("checks", []) if c["name"] == "voxels"), None)
    ctx["tamper_check"] = {"file": f.name, "voxel_yx": [y, x], "argv": argv, "exit_code": r.returncode,
                           "verdict": report.get("verdict", r.stdout.strip()), "voxels_check": where,
                           "detected": r.returncode != 0 and "TAMPER" in report.get("verdict", "")}
    return {"INT.tamper_report": rel(new[-1] / "verify_report.json")} if new else {}
