"""Sanctioned volume I/O (contracts/VOLUMES.md).

NIfTI via SimpleITK in the DICOM/ITK LPS frame with identity direction; numpy arrays in (z, y, x).
JSON / metadata vectors (spacing, origin, size) are ITK order (x, y, z).
NPZ written with fixed zip timestamps so regeneration is byte-identical.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import SimpleITK as sitk

IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
HU_MIN, HU_MAX = -1024, 3071
_ZIP_DATE = (1980, 1, 1, 0, 0, 0)


def _meta(img: sitk.Image) -> dict:
    return {
        "size_xyz": list(img.GetSize()),
        "spacing_mm_xyz": [float(v) for v in img.GetSpacing()],
        "origin_mm_lps": [float(v) for v in img.GetOrigin()],
        "direction": [float(v) for v in img.GetDirection()],
    }


def read_volume(path: str | Path, reorient: bool = True) -> tuple[np.ndarray, dict]:
    """Return (array_zyx, meta). With reorient=True the image is first brought to LPS identity."""
    img = sitk.ReadImage(str(path))
    if reorient:
        img = sitk.DICOMOrient(img, "LPS")
    return sitk.GetArrayFromImage(img), _meta(img)


def read_header(path: str | Path) -> dict:
    """Meta + pixel type without reorienting (used by the validator to check the stored frame)."""
    r = sitk.ImageFileReader()
    r.SetFileName(str(path))
    r.ReadImageInformation()
    return {
        "size_xyz": list(r.GetSize()),
        "spacing_mm_xyz": [float(v) for v in r.GetSpacing()],
        "origin_mm_lps": [float(v) for v in r.GetOrigin()],
        "direction": [float(v) for v in r.GetDirection()],
        "dtype": sitk.GetPixelIDValueAsString(r.GetPixelID()),
    }


def write_volume(path: str | Path, array_zyx: np.ndarray, spacing_mm_xyz, origin_mm_lps) -> Path:
    """Write a 3-D array (z, y, x) as .nii.gz in LPS with identity direction."""
    if array_zyx.ndim != 3:
        raise ValueError(f"3-D arrays only, got ndim={array_zyx.ndim}")
    img = sitk.GetImageFromArray(np.ascontiguousarray(array_zyx))
    img.SetSpacing([float(v) for v in spacing_mm_xyz])
    img.SetOrigin([float(v) for v in origin_mm_lps])
    img.SetDirection(IDENTITY)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(img, str(path), useCompression=True)
    return path


def same_grid(a: dict, b: dict, tol: float = 1e-4) -> bool:
    return (
        list(a["size_xyz"]) == list(b["size_xyz"])
        and np.allclose(a["spacing_mm_xyz"], b["spacing_mm_xyz"], atol=tol)
        and np.allclose(a["origin_mm_lps"], b["origin_mm_lps"], atol=tol)
        and np.allclose(a["direction"], b["direction"], atol=tol)
    )


def check_same_grid(paths) -> list[str]:
    """Return error strings for every volume whose grid differs from the first one."""
    paths = list(paths)
    if len(paths) < 2:
        return []
    ref = read_header(paths[0])
    return [f"{p}: grid differs from {paths[0]}" for p in paths[1:] if not same_grid(ref, read_header(p))]


def save_npz(path: str | Path, **arrays) -> Path:
    """Compressed .npz with deterministic bytes (fixed zip entry dates, sorted keys)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for key in sorted(arrays):
            buf = io.BytesIO()
            np.lib.format.write_array(buf, np.asanyarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy", date_time=_ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, buf.getvalue())
    return path


def load_npz(path: str | Path, required: dict[str, tuple[str, int]] | None = None) -> dict:
    """Load all arrays; `required` maps key -> (dtype, ndim) and raises ValueError on mismatch."""
    with np.load(path, allow_pickle=False) as z:
        data = {k: z[k] for k in z.files}
    for key, (dtype, ndim) in (required or {}).items():
        if key not in data:
            raise ValueError(f"{path}: missing key '{key}'")
        if str(data[key].dtype) != dtype or data[key].ndim != ndim:
            raise ValueError(f"{path}: '{key}' must be {dtype} ndim={ndim}, "
                             f"got {data[key].dtype} ndim={data[key].ndim}")
    return data
