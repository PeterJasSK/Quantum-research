"""LIDC-IDRI subset selection and download (plan AC-2). Data stays outside the repo.

    python -m A_placement.src.lidc_fetch --select 40          # write repro/lidc_subset.txt
    python -m A_placement.src.lidc_fetch --fetch              # download listed series to $LIDC_ROOT
    python -m A_placement.src.lidc_fetch --select 40 --fetch

Selection is deterministic: patients in ID order, first scan per patient, slice thickness
<= 2.5 mm, at least one nodule outlined by >= MIN_READERS radiologists with mean diameter
>= MIN_DIAMETER_MM. Only pylidc's bundled annotation DB is needed to select.
"""
from __future__ import annotations

import argparse
import configparser
from pathlib import Path

from A_placement.src.classes import MIN_DIAMETER_MM, MIN_READERS
from A_placement.src.lidc_io import LIDC_ROOT, SUBSET, pylidc, read_subset

MAX_SLICE_THICKNESS_MM = 2.5
PYLIDCRC = Path.home() / ".pylidcrc"


def write_pylidcrc(root: Path = LIDC_ROOT) -> None:
    cfg = configparser.ConfigParser()
    if PYLIDCRC.exists():
        cfg.read(PYLIDCRC)
        if cfg.get("dicom", "path", fallback=None) == str(root):
            return
        PYLIDCRC.replace(PYLIDCRC.with_suffix(".bak"))
        print(f"backed up existing {PYLIDCRC} to {PYLIDCRC.with_suffix('.bak')}")
    cfg["dicom"] = {"path": str(root), "warn": "True"}
    with open(PYLIDCRC, "w") as f:
        cfg.write(f)
    print(f"wrote {PYLIDCRC} (dicom path = {root})")


def select(n: int) -> list[tuple[str, str]]:
    pl = pylidc()
    chosen, seen = [], set()
    for scan in pl.query(pl.Scan).order_by(pl.Scan.patient_id, pl.Scan.id):
        if scan.patient_id in seen:
            continue
        seen.add(scan.patient_id)
        if scan.slice_thickness > MAX_SLICE_THICKNESS_MM:
            continue
        clusters = scan.cluster_annotations(verbose=False)
        if not any(len(c) >= MIN_READERS and sum(a.diameter for a in c) / len(c) >= MIN_DIAMETER_MM
                   for c in clusters):
            continue
        chosen.append((scan.patient_id, scan.series_instance_uid))
        if len(chosen) == n:
            break
    SUBSET.write_text("# patient_id series_instance_uid  (lidc_fetch --select, deterministic)\n"
                      + "".join(f"{p} {s}\n" for p, s in chosen))
    print(f"selected {len(chosen)} patients -> {SUBSET}")
    return chosen


def fetch(root: Path = LIDC_ROOT) -> None:
    from tcia_utils import nbia

    for pid, series in read_subset():
        dest = root / pid
        if (dest / series).is_dir() and any((dest / series).glob("*.dcm")):
            continue
        dest.mkdir(parents=True, exist_ok=True)
        print(f"downloading {pid} {series}")
        nbia.downloadSeries([series], input_type="list", path=str(dest))
    print(f"all {len(read_subset())} series present under {root}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--select", type=int, metavar="N")
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args()
    write_pylidcrc()
    if a.select:
        select(a.select)
    if a.fetch:
        fetch()


if __name__ == "__main__":
    main()
