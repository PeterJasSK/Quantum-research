"""Check a DICOM CT series (e.g. G's export) against the documented AI-Rad Companion input requirements.

    python -m H_analysis.src.airad_check <dicom_dir>

Requirements live in airad_requirements.json (each with its source URL; verify=true means unconfirmed).
Prints one pass/fail line per requirement. Nothing is submitted anywhere.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pydicom

REQ = Path(__file__).with_name("airad_requirements.json")


def series_facts(d: Path) -> dict:
    files = sorted(p for p in d.rglob("*") if p.is_file() and p.suffix.lower() in ("", ".dcm"))
    heads = []
    for f in files:
        try:
            heads.append(pydicom.dcmread(f, stop_before_pixels=True))
        except Exception:  # noqa: BLE001  non-DICOM file in the folder
            continue
    if not heads:
        raise SystemExit(f"no DICOM files in {d}")
    h0 = heads[0]
    z = sorted(float(h.ImagePositionPatient[2]) for h in heads if "ImagePositionPatient" in h)
    st = getattr(h0, "SliceThickness", None)
    age = getattr(h0, "PatientAge", None)
    return {"modality": getattr(h0, "Modality", None),
            "age": int(str(age)[:3]) if age and str(age)[:3].isdigit() else None,
            "slice_thickness_mm": float(st) if st is not None else None,
            "in_plane_spacing_mm": float(h0.PixelSpacing[0]) if "PixelSpacing" in h0 else None,
            "convolution_kernel": getattr(h0, "ConvolutionKernel", None),
            "coverage_mm": float(z[-1] - z[0] + (float(st) if st else 0)) if len(z) > 1 else None,
            "patient_position": getattr(h0, "PatientPosition", None), "n_slices": len(heads)}


def check(req: dict, f: dict):
    key = {"adult_patient": "age"}.get(req["id"], req["id"])
    v = f.get(key)
    if v is None:
        return None
    c, ref = req["check"], req["value"]
    if c == "equals":
        return v == ref
    if c in ("min_age_years", "min"):
        return v >= ref
    if c == "max":
        return v <= ref
    if c == "in":
        return v in ref
    return bool(v)  # "present"


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 1:
        print(__doc__)
        return 2
    facts = series_facts(Path(argv[0]))
    print(f"series: {facts['n_slices']} slices")
    bad = 0
    for r in json.loads(REQ.read_text())["requirements"]:
        res = check(r, facts)
        state = "unknown (tag missing)" if res is None else ("pass" if res else "FAIL")
        bad += res is False
        print(f"  {r['id']:22s} {state:22s} value={facts.get({'adult_patient': 'age'}.get(r['id'], r['id']))!s:14s} "
              f"required {r['check']} {r['value']}{' (verify)' if r['verify'] else ''}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
