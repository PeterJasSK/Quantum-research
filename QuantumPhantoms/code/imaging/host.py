"""F5 — a real 3-D HU host CT (public LIDC-IDRI case) + threshold lung/body masks.

    host = load_host("LIDC-IDRI-0481")      # SIEMENS SOMATOM Definition (F5 default host)

Reads the DICOM series from ~/data/LIDC-IDRI (fetch it first: `python -m imaging.lidc_fetch <id>`) with
SimpleITK (HU via the DICOM rescale), in the LPS identity frame (z ascending). Masks are threshold +
connected components (RE F's F-local host masks, no lungmask/TotalSegmentator):
    body  = largest component of smoothed HU > −500, holes filled per slice
    lungs = HU < −400 inside the body, trachea/main bronchi removed, closed + hole-filled
    left_right = 1 patient right (low x in LPS), 2 patient left
No vessel mask (F5 plan Q8). Host voxels and masks are cached in research_runs/_hosts/<id>/ (gitignored,
it holds patient voxels); nothing voxel-wise from the host ever reaches the repo except cropped 2-D
display PNGs of the public scan.
"""
# copied from plans/relatedPapers/reverse-engineering/F_render/src/host_masks.py @ 2609cbe
# (_largest, _fill_slices, make_masks); dropped: vessels output, lobes, free_site, contract writing,
# pylidc loading (replaced by the SimpleITK series reader below).

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

import numpy as np
import SimpleITK as sitk
from scipy import ndimage as ndi

from imaging.lidc_fetch import LIDC_ROOT, find_local_series

HU_MIN, HU_MAX = -1024, 3071
HOSTS_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                                          "research_runs", "_hosts"))
_TAGS = {"manufacturer": "0008|0070", "model": "0008|1090", "kernel": "0018|1210",
         "slice_thickness": "0018|0050", "series_uid": "0020|000e"}


class HostMissing(FileNotFoundError):
    """The host's DICOM series is not on this machine (exit code 2 in build_tiles)."""


@dataclass
class Host:
    host_id: str
    hu: np.ndarray                 # int16 (z, y, x), LPS identity frame
    spacing_zyx: tuple             # mm
    origin_lps: tuple              # mm, LPS of voxel (0, 0, 0), (x, y, z)
    body: np.ndarray               # uint8
    lungs: np.ndarray              # uint8 0/1
    left_right: np.ndarray         # uint8 0 none, 1 patient right, 2 patient left
    meta: dict = field(default_factory=dict)   # manufacturer, model, kernel, slice_thickness, series_uid

    @property
    def host_meta(self) -> dict:
        """RE-style host grid description (xyz order) for lesion rendering."""
        z, y, x = self.hu.shape
        return {"size_xyz": [x, y, z], "spacing_mm_xyz": list(self.spacing_zyx[::-1]),
                "origin_mm_lps": list(self.origin_lps)}


def _largest(mask, k=1):
    lab, n = ndi.label(mask)
    if n == 0:
        return np.zeros_like(mask, bool), []
    sizes = ndi.sum(mask, lab, range(1, n + 1))
    order = np.argsort(sizes)[::-1][:k] + 1
    return np.isin(lab, order), [lab == i for i in order]


def _fill_slices(mask):
    return np.stack([ndi.binary_fill_holes(s) for s in mask])


def make_masks(hu: np.ndarray, sp_zyx) -> dict:
    sp = np.asarray(sp_zyx, float)
    sm = ndi.gaussian_filter(hu.astype(np.float32), (0, 1, 1))
    body, _ = _largest(sm > -500)
    body = _fill_slices(body)
    cand = (sm < -400) & body
    cand = ndi.binary_opening(cand, iterations=1)
    big, comps = _largest(cand, 3)
    vox_ml = sp.prod() / 1000.0
    comps = [c for c in comps if c.sum() * vox_ml > 100]
    xs = np.flatnonzero(body.any((0, 1)))
    cx = 0.5 * (xs.min() + xs.max())
    lung_any = np.zeros_like(body)
    for c in comps:
        lung_any |= c
    xg = np.arange(hu.shape[2])[None, None, :]
    airway = lung_any & (sm < -950) & (np.abs(xg - cx) * sp[2] < 25)
    airway, _ = _largest(airway)
    lung_any &= ~ndi.binary_dilation(airway, iterations=2)
    filled = _fill_slices(ndi.binary_closing(lung_any, iterations=2))
    left_right = np.zeros(hu.shape, np.uint8)
    left_right[filled & (xg < cx)] = 1      # patient right
    left_right[filled & (xg >= cx)] = 2     # patient left
    return {"body": body.astype(np.uint8), "lungs": filled.astype(np.uint8), "left_right": left_right}


def _read_series(series_dir) -> tuple[np.ndarray, tuple, tuple, dict]:
    reader = sitk.ImageSeriesReader()
    files = reader.GetGDCMSeriesFileNames(str(series_dir))
    reader.SetFileNames(files)
    reader.MetaDataDictionaryArrayUpdateOn()
    reader.LoadPrivateTagsOn()
    img = reader.Execute()
    arr = sitk.GetArrayFromImage(img)                  # (z, y, x), HU after rescale
    d = np.asarray(img.GetDirection(), float).reshape(3, 3)
    sp = np.asarray(img.GetSpacing(), float)           # x, y, z
    org = np.asarray(img.GetOrigin(), float)
    if not np.allclose(np.abs(d), np.eye(3), atol=1e-3):
        raise ValueError(f"oblique series (direction {d.tolist()}); F5 handles axial LPS series only")
    for ax in range(3):                                # flip any reversed axis into the LPS identity frame
        if d[ax, ax] < 0:
            arr = np.flip(arr, axis=2 - ax)
            org[ax] = org[ax] + d[ax, ax] * sp[ax] * (img.GetSize()[ax] - 1)
    meta = {}
    for k, tag in _TAGS.items():
        meta[k] = reader.GetMetaData(0, tag).strip() if reader.HasMetaDataKey(0, tag) else ""
    hu = np.clip(arr, HU_MIN, HU_MAX).astype(np.int16)
    return np.ascontiguousarray(hu), tuple(sp[::-1].tolist()), tuple(org.tolist()), meta


def load_host(host_id: str, log=print) -> Host:
    """Load (or build + cache) the host volume and masks."""
    cdir = os.path.join(HOSTS_DIR, host_id)
    npz, js = os.path.join(cdir, "host.npz"), os.path.join(cdir, "host.json")
    if os.path.isfile(npz) and os.path.isfile(js):
        with open(js) as f:
            info = json.load(f)
        z = np.load(npz)
        return Host(host_id, z["hu"], tuple(info["spacing_zyx"]), tuple(info["origin_lps"]),
                    z["body"], z["lungs"], z["left_right"], info["meta"])
    series = find_local_series(host_id)
    if series is None:
        raise HostMissing(f"{host_id} not found under {LIDC_ROOT}; fetch it with "
                          f"`python -m imaging.lidc_fetch {host_id}`")
    t0 = time.time()
    hu, sp, org, meta = _read_series(series)
    masks = make_masks(hu, sp)
    os.makedirs(cdir, exist_ok=True)
    np.savez_compressed(npz, hu=hu, **masks)
    info = {"host_id": host_id, "spacing_zyx": list(sp), "origin_lps": list(org), "shape_zyx": list(hu.shape),
            "meta": meta, "series_dir": str(series),
            "lung_voxels": int(masks["lungs"].sum()), "prep_seconds": round(time.time() - t0, 1),
            "attribution": "LIDC-IDRI (TCIA), CC BY 3.0, https://doi.org/10.7937/K9/TCIA.2015.LO9QL9SX"}
    with open(js, "w") as f:
        json.dump(info, f, indent=2)
    log(f"  host prep {host_id}: {info['prep_seconds']} s (cached -> {cdir})")
    return Host(host_id, hu, sp, org, masks["body"], masks["lungs"], masks["left_right"], meta)
