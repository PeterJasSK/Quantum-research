"""Cohort manifest: load + shared.validate every listed contract file; joins; analysis seed.

Manifest paths are relative to the manifest file. Format (see README "Inputs"):
  seed_note, hybrids[]{path, seed_source?}, draws[], rulebook, compiled_circuit, job_records[], certificates[],
  witness[], memory[], simulability[], trajectories[], receipts[], ledger
"""
from __future__ import annotations

import json
from pathlib import Path

from shared import seedhash, validate

LIST_KINDS = ["draws", "job_records", "certificates", "witness", "memory", "simulability", "trajectories", "receipts"]
ONE_KINDS = ["rulebook", "compiled_circuit", "ledger"]


class CohortError(SystemExit):
    pass


def load(manifest_path: str | Path) -> dict:
    mp = Path(manifest_path).resolve()
    raw = json.loads(mp.read_text())
    base = mp.parent

    def p(rel):
        return (base / rel).resolve()

    files: dict[str, list[Path]] = {}
    files["hybrids"] = [p(h["path"]) for h in raw.get("hybrids", [])]
    for k in LIST_KINDS:
        files[k] = [p(x) for x in raw.get(k, [])]
    for k in ONE_KINDS:
        files[k] = [p(raw[k])] if raw.get(k) else []
    errors = []
    for kind, paths in files.items():
        for f in paths:
            if not f.exists():
                errors.append(f"{kind}: missing {f}")
                continue
            _, errs = validate.validate_file(f)
            errors += [f"{kind}: {f.name}: {e}" for e in errs]
    if errors:
        raise CohortError("cohort aborted, shared.validate errors:\n  " + "\n  ".join(errors))
    obj = {k: [json.loads(f.read_text()) if f.suffix == ".json" else
               [json.loads(line) for line in f.read_text().splitlines() if line.strip()] for f in v]
           for k, v in files.items()}
    seed_source = [h.get("seed_source") for h in raw.get("hybrids", [])]
    return {"path": mp, "raw": raw, "files": files, "obj": obj, "seed_source": seed_source,
            "seed": seedhash.hash_json(raw)}


def draw_index(c: dict) -> dict:
    return {d["draw_id"]: d for d in c["obj"]["draws"]}


def hybrid_type(c: dict, i: int) -> str:
    h = c["obj"]["hybrids"][i]
    d = draw_index(c).get(h.get("draw_id"))
    return d["type"] if d else "unknown"


def resolve(c: dict, base: Path, ref: dict) -> Path:
    return (base.parent / ref["path"]).resolve()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def load_hybrid(c: dict, i: int) -> dict:
    """ROIs (1 mm isotropic, 48^3) of hybrid i: hybrid CT, host CT (same location, lesion absent), lesion mask."""
    import numpy as np

    from H_analysis.src import roi
    from shared import volumes

    h, hp = c["obj"]["hybrids"][i], c["files"]["hybrids"][i]
    refs = {k: (hp.parent / v["path"]).resolve() for k, v in h["files"].items()}
    hyb, meta = volumes.read_volume(refs["hybrid_ct"])
    host, _ = volumes.read_volume(refs["host_ct"])
    mask, _ = volumes.read_volume(refs["lesion_mask"])
    sx, sy, sz = meta["spacing_mm_xyz"]
    sp = (sz, sy, sx)
    cen = np.argwhere(mask > 0).mean(0)
    mroi = roi.crop_mask(mask, sp, cen)
    return {"hybrid": roi.crop_iso(hyb, sp, cen), "host": roi.crop_iso(host, sp, cen), "mask": mroi,
            "d_eq_mm": roi.equivalent_diameter_mm(mroi), "type": hybrid_type(c, i), "host_scan_id": h["host_scan_id"],
            "seed_source": c["seed_source"][i] if i < len(c["seed_source"]) else None, "draw_id": h.get("draw_id")}
