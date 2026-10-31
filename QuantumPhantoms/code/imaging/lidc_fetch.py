"""F5 — fetch one public LIDC-IDRI CT series from TCIA (host scan for the grown renderer).

    python -m imaging.lidc_fetch LIDC-IDRI-0481          # default host: SIEMENS SOMATOM Definition

Scans live OUTSIDE the repo: $LIDC_ROOT, default ~/data/LIDC-IDRI, in the pylidc layout
<root>/<patient_id>/<study_uid>/<series_uid>/*.dcm. The series is looked up through the public NBIA
`getSeries` call (CT only, largest image count per patient); a non-Siemens scanner prints a warning
(F5 plan Q3: hosts are Siemens-scanner cases). LIDC-IDRI is CC BY 3.0
(https://doi.org/10.7937/K9/TCIA.2015.LO9QL9SX).
"""
# copied from plans/relatedPapers/reverse-engineering/F_render/src/lidc.py @ 2609cbe
# (download_series, series_dir, LIDC_ROOT, NBIA); added: NBIA series lookup + Siemens check.

from __future__ import annotations

import argparse
import functools
import io
import json
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

print = functools.partial(print, flush=True)

LIDC_ROOT = Path(os.environ.get("LIDC_ROOT", "~/data/LIDC-IDRI")).expanduser()
NBIA = "https://services.cancerimagingarchive.net/nbia-api/services/v1"
DEFAULT_HOST = "LIDC-IDRI-0481"


def lookup_series(patient_id: str) -> dict:
    """NBIA series record for the patient's main CT series (largest ImageCount)."""
    url = f"{NBIA}/getSeries?Collection=LIDC-IDRI&PatientID={patient_id}&Modality=CT"
    with urllib.request.urlopen(url, timeout=120) as r:
        recs = json.loads(r.read() or b"[]")
    if not recs:
        raise ValueError(f"{patient_id}: no CT series found in TCIA LIDC-IDRI")
    return max(recs, key=lambda s: int(s.get("ImageCount", 0)))


def series_dir(rec: dict) -> Path:
    return LIDC_ROOT / rec["PatientID"] / rec["StudyInstanceUID"] / rec["SeriesInstanceUID"]


def find_local_series(patient_id: str) -> Path | None:
    """Largest local series dir for a patient (pylidc layout), or None."""
    root = LIDC_ROOT / patient_id
    if not root.is_dir():
        return None
    dirs = [d for d in root.glob("*/*") if d.is_dir() and any(d.glob("*.dcm"))]
    return max(dirs, key=lambda d: len(list(d.glob("*.dcm")))) if dirs else None


def download_series(rec: dict) -> Path:
    """Fetch one series zip from the TCIA NBIA API and unpack it in the pylidc layout."""
    dest = series_dir(rec)
    if dest.is_dir() and any(dest.glob("*.dcm")):
        return dest
    url = f"{NBIA}/getImage?SeriesInstanceUID={rec['SeriesInstanceUID']}"
    with urllib.request.urlopen(url, timeout=900) as r:
        data = r.read()
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            if name.endswith(".dcm"):
                (dest / Path(name).name).write_bytes(zf.read(name))
    return dest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("patient_id", nargs="?", default=DEFAULT_HOST, help="LIDC patient id")
    a = ap.parse_args(argv)
    rec = lookup_series(a.patient_id)
    make = rec.get("Manufacturer", "?")
    print(f"  {a.patient_id}: {make} {rec.get('ManufacturerModelName', '?')}, "
          f"{rec.get('ImageCount')} images, {int(rec.get('FileSize', 0)) / 1e6:.0f} MB")
    if "SIEMENS" not in str(make).upper():
        print(f"  WARNING: {a.patient_id} is not a Siemens-scanner case (F5 hosts should be Siemens).")
    dest = download_series(rec)
    print(f"  series -> {dest} ({len(list(dest.glob('*.dcm')))} DICOM files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
