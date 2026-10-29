"""#16 Projection-domain lesion insertion rebuilt on XCIST (Mayo [F03] §2.1; Robins/Duke [F02] Technique A).

Mayo forward-projects a segmented lesion with the scanner's exact geometry, adds its line integrals to
the patient's processed (post-log) projections, and reconstructs. Here the scanner is XCIST configured
from published parameters (`F_render/xcist/siemens_definition_like.cfg`) and the host is a synthetic
voxel phantom, because the Mayo raw data and vendor geometry decoder are not available (plan Q3).

    prep_A = prep_host + prep_lesion      (lesion projected alone: excess attenuation over lung, noise off)
    image_A = FBP(prep_A)

The lesion is projected polychromatically with the host spectrum and added in the log domain; Mayo
projected monochromatically at 70 keV, the beam-hardening-correction energy [F03 §2.1].
"""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

import numpy as np

from F_render.src.io import F_DIR

XCIST_DIR = F_DIR / "xcist"
SIEMENS_CFG = XCIST_DIR / "siemens_definition_like.cfg"
NAEOTOM_CFG = XCIST_DIR / "naeotom_alpha.cfg"


@contextlib.contextmanager
def chdir(path: Path):
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def voxel_phantom(workdir: Path, name: str, water_fraction_zyx: np.ndarray, voxel_mm_zyx) -> Path:
    """Single-material (water volume fraction) XCIST voxel phantom centred on the isocentre."""
    workdir.mkdir(parents=True, exist_ok=True)
    nz, ny, nx = water_fraction_zyx.shape
    raw = workdir / f"{name}_water_{nx}x{ny}x{nz}.raw"
    np.ascontiguousarray(water_fraction_zyx, np.float32).tofile(raw)
    vz, vy, vx = (float(v) for v in voxel_mm_zyx)
    doc = {"n_materials": 1, "mat_name": ["water"], "volumefractionmap_filename": [raw.name],
           "volumefractionmap_datatype": ["float"], "cols": [nx], "rows": [ny], "slices": [nz],
           "x_size": [vx], "y_size": [vy], "z_size": [vz],
           "x_offset": [nx / 2 + 0.5], "y_offset": [ny / 2 + 0.5], "z_offset": [nz / 2 + 0.5]}
    j = workdir / f"{name}.json"
    j.write_text(json.dumps(doc, indent=1))
    return j


def _catsim(cfg_path: Path):
    import gecatsim as xc

    return xc.CatSim(str(Path(cfg_path).with_suffix("")))


def simulate(workdir: Path, name: str, phantom_json: Path, cfg_path: Path = SIEMENS_CFG, *, noise: bool = True,
             seed: int = 1, mA: float | None = None) -> Path:
    """Run air + offset + phantom scans and prep; returns <workdir>/<name>.prep."""
    from gecatsim.pyfiles.set_rndseed import set_rndseed

    ct = _catsim(cfg_path)
    ct.phantom.filename = phantom_json.name
    ct.resultsName = name
    ct.physics.enableQuantumNoise = int(noise)
    ct.physics.enableElectronicNoise = int(noise)
    if mA is not None:
        ct.protocol.mA = mA
    np.random.seed(seed)                       # XCIST electronic noise uses numpy's global RNG
    with chdir(workdir):
        cfg = ct.get_current_cfg()
        if hasattr(cfg, "clib"):
            set_rndseed(cfg, seed)             # C-side quantum-noise RNG
        ct.run_all()
    return workdir / f"{name}.prep"


def add_prep(a: Path, b: Path, out: Path) -> Path:
    """Projection-domain insertion: line integrals add in the post-log domain."""
    (np.fromfile(a, np.float32) + np.fromfile(b, np.float32)).astype(np.float32).tofile(out)
    return out


def reconstruct(workdir: Path, name: str, cfg_path: Path = SIEMENS_CFG) -> np.ndarray:
    """FBP of <workdir>/<name>.prep with the cfg's recon block → HU array (slices, rows, cols)."""
    import gecatsim as xc
    import gecatsim.reconstruction.pyfiles.recon as xrecon

    ct = _catsim(cfg_path)
    ct.resultsName = name
    ct.do_Recon = 1
    with chdir(workdir):
        xrecon.recon(ct)
        n, s = ct.recon.imageSize, ct.recon.sliceCount
        return xc.rawread(f"{name}_{n}x{n}x{s}.raw", [s, n, n], "float")


def recon_grid(cfg_path: Path = SIEMENS_CFG) -> dict:
    ct = _catsim(cfg_path)
    r = ct.recon
    return {"pixel_mm": r.fov / r.imageSize, "slice_mm": r.sliceThickness, "image_size": r.imageSize,
            "slices": r.sliceCount}
