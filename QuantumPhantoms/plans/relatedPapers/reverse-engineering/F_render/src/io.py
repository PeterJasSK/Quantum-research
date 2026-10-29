"""Contract-checked input loading for F, and the manifest envelope for F outputs.

Every input is validated with `shared.validate.validate_file` before use; refs are resolved
relative to the file that holds them (W convention).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from shared import CONTRACT_VERSION, RE_ROOT, STUBS
from shared.seedhash import sha256_file
from shared.validate import validate_file
from shared.volumes import load_npz, read_volume

F_DIR = RE_ROOT / "F_render"
STUB = {
    "trajectory": STUBS / "growth_trajectory" / "growth_trajectory.json",
    "masks": STUBS / "anatomy_masks" / "anatomy_masks.json",
    "sites": STUBS / "site_candidates" / "sites.json",
    "draw": STUBS / "tumor_draw" / "tumor_draw.json",
    "certificate": STUBS / "certificate" / "certificate.json",
    "library": STUBS / "lesion_model_library" / "lesion_model_library.json",
    "fingerprint": STUBS / "scanner_fingerprint" / "scanner_fingerprint.json",
}
FITTED_LIBRARY = F_DIR / "library" / "lesion_model_library.json"


class RejectedDraw(RuntimeError):
    """Certificate status fail: the draw is rejected and nothing is rendered (epic decision 6)."""


def load(path: str | Path, contract: str) -> tuple[dict, Path]:
    path = Path(path).resolve()
    got, errs = validate_file(path)
    if got != contract:
        raise ValueError(f"{path}: expected contract {contract!r}, got {got!r}")
    if errs:
        raise ValueError(f"{path} violates {contract}:\n  " + "\n  ".join(errs))
    return json.loads(path.read_text()), path


def ref(doc_path: Path, file_ref: dict) -> Path:
    return (doc_path.parent / file_ref["path"]).resolve()


def seed_from_certificate(path: str | Path) -> tuple[str, dict, Path]:
    cert, p = load(path, "certificate")
    if cert["status"] != "pass" or not cert["extracted_seed_hex"]:
        raise RejectedDraw(f"certificate status {cert['status']}: draw rejected (epic decision 6)")
    return cert["extracted_seed_hex"], cert, p


def snapshot(traj: dict, traj_path: Path, step: int | None) -> tuple[np.ndarray, dict]:
    snaps = {s["step"]: s for s in traj["snapshots"]}
    if step is None:
        step = max(snaps)
    if step not in snaps:
        raise ValueError(f"step {step} not in trajectory (have {sorted(snaps)})")
    data = load_npz(ref(traj_path, snaps[step]["npz"]), required={"state": ("uint8", 3)})
    return data["state"], snaps[step]


def host_volumes(masks: dict, masks_path: Path) -> dict:
    """host_ct + every mask on the host grid, as numpy (z, y, x) arrays; plus the grid meta."""
    out = {}
    for key, fr in masks["files"].items():
        if fr is None:
            continue
        arr, meta = read_volume(ref(masks_path, fr))
        out[key] = arr
        out["meta"] = meta
    return out


def site_by_id(sites: dict, site_id: str) -> dict:
    for s in sites["sites"]:
        if s["site_id"] == site_id:
            return s
    raise ValueError(f"site {site_id} not in sites.json")


def file_ref(target: Path, frm: Path) -> dict:
    return {"path": Path(target).resolve().relative_to(Path(frm).resolve().parent, walk_up=True).as_posix(),
            "sha256": sha256_file(target)}


def up_ref(contract: str, target: Path, frm: Path) -> dict:
    return {"contract": contract, **file_ref(target, frm)}


def envelope(contract: str, tool: str, code_hash: str, run_id: str | None, upstream: list[dict]) -> dict:
    return {
        "contract": contract,
        "contract_version": CONTRACT_VERSION,
        "produced_by": {"letter": "F", "tool": tool, "run_id": run_id, "code_hash": code_hash},
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stub": False,
        "upstream": upstream,
    }


def write_manifest(path: Path, doc: dict) -> Path:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    _, errs = validate_file(path)
    if errs:
        raise ValueError(f"{path} violates {doc['contract']}:\n  " + "\n  ".join(errs))
    return path
