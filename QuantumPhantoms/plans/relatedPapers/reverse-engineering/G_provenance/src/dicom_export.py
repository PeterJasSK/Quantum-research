"""Hybrid CT -> DICOM CT series carrying the signed receipt in a private tag block (AC-7).

    python -m G_provenance.src.dicom_export <ledgered receipt.json> [--out DIR] [--ledger ledger.jsonl]

One CT Image Storage file per axial slice (explicit VR little endian, int16, slope 1 / intercept 0).
Private block group 0x0011, creator "QP-RE G PROVENANCE": receipt_json, bound_params_json,
ledger_index, ledger_entry_hash, slice_index, slice_sha256. `read_series` is what the verifier uses.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pydicom
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from G_provenance.src import ledger as ledgermod
from G_provenance.src.hashing import grid_of, slice_sha256s
from shared import RE_ROOT
from shared.runrecord import start_run
from shared.seedhash import canonical_json, sha256_file
from shared.volumes import read_volume

LETTER_DIR = RE_ROOT / "G_provenance"
CREATOR = "QP-RE G PROVENANCE"
GROUP = 0x0011
ELEMENTS = {"receipt_json": (0x01, "UT"), "bound_params_json": (0x02, "UT"), "ledger_index": (0x03, "UL"),
            "ledger_entry_hash": (0x04, "LO"), "slice_index": (0x05, "UL"), "slice_sha256": (0x06, "LO")}


def _ds_str(v: float) -> str:
    return f"{v:.6f}".rstrip("0").rstrip(".") or "0"


def set_tags(ds: pydicom.Dataset, values: dict) -> None:
    block = ds.private_block(GROUP, CREATOR, create=True)
    for name, (offset, vr) in ELEMENTS.items():
        if name in values:
            block.add_new(offset, vr, values[name])


def export(receipt_path: Path, out_dir: Path, ledger_path: Path = ledgermod.LEDGER) -> list[Path]:
    receipt_path = Path(receipt_path).resolve()
    receipt = json.loads(receipt_path.read_text())
    if receipt["state"] != "ledgered":
        raise ValueError(f"receipt state is {receipt['state']!r}, need 'ledgered'")
    sha = sha256_file(receipt_path)
    entry = ledgermod.find_receipt(sha, ledger_path)
    if entry is None:
        raise ValueError("receipt is not in the ledger")
    bound = json.loads((receipt_path.parent / "bound_params.json").read_text())
    hyb_ref = next(u for u in receipt["upstream"] if u["contract"] == "hybrid_volume")
    hyb_path = (receipt_path.parent / hyb_ref["path"]).resolve()
    hyb = json.loads(hyb_path.read_text())
    arr, meta = read_volume(hyb_path.parent / hyb["files"]["hybrid_ct"]["path"])
    arr = arr.astype("<i2")
    grid = grid_of(meta)
    sx, sy, sz = meta["spacing_mm_xyz"]
    x0, y0, z0 = meta["origin_mm_lps"]
    hashes = slice_sha256s(arr)
    receipt_json = canonical_json(receipt).decode()
    bound_json = canonical_json(bound).decode()
    uid = lambda *a: generate_uid(None, [sha, *map(str, a)])  # noqa: E731  deterministic from the receipt hash
    study, series, frame = uid("study"), uid("series"), uid("frame")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for z in range(arr.shape[0]):
        fm = FileMetaDataset()
        fm.MediaStorageSOPClassUID = CTImageStorage
        fm.MediaStorageSOPInstanceUID = uid("sop", z)
        fm.TransferSyntaxUID = ExplicitVRLittleEndian
        fm.ImplementationClassUID = generate_uid(None, ["QP-RE"])
        path = out_dir / f"slice_{z:04d}.dcm"
        ds = FileDataset(str(path), {}, file_meta=fm, preamble=b"\0" * 128)
        ds.SOPClassUID, ds.SOPInstanceUID = CTImageStorage, fm.MediaStorageSOPInstanceUID
        ds.StudyInstanceUID, ds.SeriesInstanceUID, ds.FrameOfReferenceUID = study, series, frame
        ds.Modality, ds.ImageType = "CT", ["DERIVED", "SECONDARY", "SYNTHETIC"]
        ds.PatientName, ds.PatientID = "SYNTHETIC^QP-RE", hyb["draw_id"]
        ds.StudyDate = ds.SeriesDate = ds.ContentDate = receipt["created_utc"][:10].replace("-", "")
        ds.SeriesDescription = "QP-RE synthetic hybrid CT (provenance-signed)"
        ds.InstitutionName = "QP-RE"
        ds.InstanceNumber, ds.SeriesNumber = z + 1, 1
        ds.ImagePositionPatient = [_ds_str(x0), _ds_str(y0), _ds_str(z0 + z * sz)]
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        ds.PixelSpacing = [_ds_str(sy), _ds_str(sx)]
        ds.SliceThickness, ds.SliceLocation = _ds_str(sz), _ds_str(z0 + z * sz)
        ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, "MONOCHROME2"
        ds.Rows, ds.Columns = arr.shape[1], arr.shape[2]
        ds.BitsAllocated = ds.BitsStored = 16
        ds.HighBit, ds.PixelRepresentation = 15, 1
        ds.RescaleSlope, ds.RescaleIntercept = "1", "0"
        ds.PixelData = np.ascontiguousarray(arr[z]).tobytes()
        set_tags(ds, {"receipt_json": receipt_json, "bound_params_json": bound_json,
                      "ledger_index": entry["index"], "ledger_entry_hash": entry["entry_hash"],
                      "slice_index": z, "slice_sha256": hashes[z]})
        ds.save_as(path, enforce_file_format=True)
        written.append(path)
    assert grid == bound["hybrid"]["grid"], "exported grid differs from the bound grid"
    return written


def read_series(series_dir: Path) -> tuple[np.ndarray, dict, list[dict], list[pydicom.Dataset]]:
    """(array_zyx int16, meta{shape, spacing_mm_xyz, origin_mm_lps}, per-slice tag dicts, datasets) by z."""
    dss = [pydicom.dcmread(f) for f in sorted(Path(series_dir).glob("*.dcm"))]
    if not dss:
        raise ValueError(f"no .dcm files in {series_dir}")
    dss.sort(key=lambda d: float(d.ImagePositionPatient[2]))
    arr = np.stack([np.frombuffer(d.PixelData, dtype="<i2").reshape(d.Rows, d.Columns) for d in dss])
    z = [float(d.ImagePositionPatient[2]) for d in dss]
    dz = float(dss[0].SliceThickness) if len(z) < 2 else float(np.median(np.diff(z)))
    sy, sx = (float(v) for v in dss[0].PixelSpacing)
    meta = {"shape": [arr.shape[2], arr.shape[1], arr.shape[0]], "spacing_mm_xyz": [sx, sy, dz],
            "origin_mm_lps": [float(v) for v in dss[0].ImagePositionPatient]}
    tags = []
    for d in dss:
        block = d.private_block(GROUP, CREATOR)
        tags.append({name: block[off].value for name, (off, _) in ELEMENTS.items()})
    return arr, meta, tags, dss


def write_pixels(series_dir: Path, array_zyx: np.ndarray) -> None:
    """Replace PixelData in each slice file, leaving every tag untouched (the G01 attacker model)."""
    files = sorted(Path(series_dir).glob("*.dcm"))
    for f in files:
        ds = pydicom.dcmread(f)
        z = int(round((float(ds.ImagePositionPatient[2]) - float(pydicom.dcmread(files[0]).ImagePositionPatient[2]))
                      / float(ds.SliceThickness)))
        ds.PixelData = np.ascontiguousarray(array_zyx[z], dtype="<i2").tobytes()
        ds.save_as(f, enforce_file_format=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("receipt", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--ledger", type=Path, default=ledgermod.LEDGER)
    a = ap.parse_args(argv)
    run = start_run(LETTER_DIR, "dicom", tool="G_provenance:dicom_export")
    out = a.out or run.path / "series"
    files = export(a.receipt, out, a.ledger)
    run.add_input(a.receipt, "receipt")
    run.finish(f"{len(files)} CT slices with private provenance block")
    print(f"wrote {len(files)} slices to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
