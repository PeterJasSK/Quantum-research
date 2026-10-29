"""Contract I/O for E: load + validate the five inputs, the certificate gate, write `growth_trajectory`.

Inputs (defaults = shared/stubs): anatomy_masks, site_candidates, tumor_draw, certificate, seed_shape.
Output: <run>/growth_trajectory/growth_trajectory.json + step_<NNNN>.npz (contract), plus two letter-local
sidecars that are not contracts: growth_summary.json (per-day measurements, checks) and environment.npz
(barrier/level maps for figures).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes, mesh_surface_area

from shared import CONTRACT_VERSION, STUBS
from shared.seedhash import sha256_file
from shared.validate import validate_file
from shared.volumes import load_npz, read_volume, save_npz

PARAMS = Path(__file__).resolve().parent / "params_lung.json"
DEFAULTS = {
    "anatomy_masks": STUBS / "anatomy_masks" / "anatomy_masks.json",
    "site_candidates": STUBS / "site_candidates" / "sites.json",
    "tumor_draw": STUBS / "tumor_draw" / "tumor_draw.json",
    "certificate": STUBS / "certificate" / "certificate.json",
    "seed_shape": STUBS / "seed_shape" / "seed_shape.json",
}
MASK_KEYS = ("host_ct", "lungs", "lobes", "vessels", "airway")
STATE_LABELS = {"0": "host", "1": "proliferating", "2": "dormant", "3": "necrotic"}


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def certificate_refusal(cert: dict) -> str | None:
    """Epic §5: a failed certificate rejects the draw — no retry, no fallback seed."""
    if cert.get("status") != "pass" or not cert.get("extracted_seed_hex"):
        return f"draw rejected: certificate status={cert.get('status')}"
    return None


def validate_inputs(paths: dict[str, Path]) -> list[str]:
    errs = []
    for contract, p in paths.items():
        got, e = validate_file(p)
        if got != contract:
            e = [f"expected contract '{contract}', file declares '{got}'"] + e
        errs += [f"{p}: {x}" for x in e]
    return errs


def load_masks(manifest: Path) -> tuple[dict, dict]:
    doc = read_json(manifest)
    vols, meta = {}, None
    for k in MASK_KEYS:
        vols[k], m = read_volume(manifest.parent / doc["files"][k]["path"])
        meta = meta or m
    return vols, meta


def load_seed_shape(manifest: Path) -> tuple[np.ndarray, float]:
    doc = read_json(manifest)
    z = load_npz(manifest.parent / doc["npz"]["path"], required={"occupancy": ("uint8", 3)})
    return z["occupancy"], float(z["spacing_mm_xyz"][0])


def _ref(target: Path, frm: Path) -> dict:
    return {"path": Path(target).resolve().relative_to(frm.parent.resolve(), walk_up=True).as_posix(),
            "sha256": sha256_file(target)}


def sphericity(state: np.ndarray, spacing: float, smooth_mm: float = 0.0) -> float:
    """Wadell sphericity π^(1/3)(6V)^(2/3)/A from a marching-cubes surface. smooth_mm > 0 first blurs the mask
    (Gaussian σ = smooth_mm, threshold 0.5): sub-voxel Eden roughness, invisible at CT resolution, otherwise
    dominates A at nodule sizes of ~20 lattice voxels."""
    m = state > 0
    if smooth_mm > 0:
        m = gaussian_filter(m.astype(np.float32), smooth_mm / spacing) > 0.5
    verts, faces, _, _ = marching_cubes(np.pad(m, 1).astype(np.float32), 0.5, spacing=(spacing,) * 3)
    area = mesh_surface_area(verts, faces)
    vol = float(m.sum()) * spacing ** 3
    return float(np.pi ** (1 / 3) * (6 * vol) ** (2 / 3) / area)


def inertia_ratio(state: np.ndarray) -> float:
    """Smallest / largest eigenvalue of the tumor's second-moment tensor (1 = isotropic)."""
    p = np.argwhere(state > 0).astype(float)
    p -= p.mean(axis=0)
    ev = np.linalg.eigvalsh(p.T @ p / len(p))
    return float(ev[0] / ev[-1])


def write_trajectory(out_dir: Path, *, run, inputs: dict[str, Path], stub: bool, site: dict, draw: dict,
                     seed_hex: str, env, snaps: list, per_day: list, vessel_entered_day, notes: list[str],
                     params_type: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    man_path = out_dir / "growth_trajectory.json"
    sp = env.spacing_mm
    snap_entries, snap_summ = [], []
    for day, role, state in snaps:
        f = save_npz(out_dir / f"step_{day:04d}.npz", state=state.astype(np.uint8),
                     spacing_mm_xyz=np.array([sp] * 3, dtype=np.float64))
        snap_entries.append({"step": int(day), "day": float(day), "role": role, "npz": _ref(f, man_path)})
        summ = next(p for p in per_day if p["day"] == day)
        snap_summ.append({"day": int(day), "role": role, "eq_diameter_mm": summ["eq_diameter_mm"],
                          "volume_mm3": summ["volume_mm3"], "f_prolif": summ["f_prolif"],
                          "f_dormant": summ["f_dormant"], "f_necrotic": summ["f_necrotic"]})
    last = snaps[-1][2]
    manifest = {
        "contract": "growth_trajectory",
        "contract_version": CONTRACT_VERSION,
        "produced_by": {"letter": "E", "tool": "E_classical_growth.src.grow", "run_id": run.path.name,
                        "code_hash": run.code_hash},
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stub": stub,
        "upstream": [{"contract": c, **_ref(p, man_path)} for c, p in inputs.items()],
        "site_id": site["site_id"],
        "seed_hex": seed_hex,
        "seed_shape_ref": _ref(inputs["seed_shape"], man_path),
        "origin_mm_lps": [float(v) for v in env.origin_mm_lps],
        "spacing_mm_xyz": [sp] * 3,
        "state_labels": STATE_LABELS,
        "snapshots": snap_entries,
    }
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    save_npz(out_dir / "environment.npz", barrier=env.barrier_code(), level=env.level.astype(np.int8),
             spacing_mm_xyz=np.array([sp] * 3, dtype=np.float64))
    summary = {
        "note": "letter-local sidecar, not a contract (see README contract change request 1)",
        "site_id": site["site_id"], "draw_id": draw["draw_id"], "placement_class": site["context"]["placement_class"],
        "tumor_type": draw["type"], "params_type": params_type, "drawn_size_mm": draw["size_mm"],
        "snapshots": snap_summ,
        "checks": {"sphericity": round(sphericity(last, sp, smooth_mm=0.5), 4),
                   "sphericity_raw": round(sphericity(last, sp), 4),
                   "inertia_ratio": round(inertia_ratio(last), 4),
                   "voxels_outside_lung": int(((last > 0) & env.outside_lung).sum()),
                   "vessel_entered_day": vessel_entered_day,
                   "first_contact_day": next((p["day"] for p in per_day if p["barrier_contacts"] > 0), None),
                   "touched_box_edge": any(p["touches_box_edge"] for p in per_day)},
        "notes": notes,
        "per_day": per_day,
    }
    (out_dir / "growth_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    return man_path
