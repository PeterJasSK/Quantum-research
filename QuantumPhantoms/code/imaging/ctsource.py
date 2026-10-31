"""F2 CT backgrounds — real public lung CT, with a labeled synthetic dev fallback
(plan §4, AC-3).

`--ct-source synthetic` (dev default) builds a procedurally-generated lung field so the
pipeline runs with zero downloaded data (mirrors F1's Aer default). `--ct-source <dir>`
reads real LIDC/LUNA16 slices: LUNA16 `.mhd/.raw` via SimpleITK (HU + spacing), `.npy`
HU arrays, or grayscale PNG. Every background records its `source` so each tile can carry
the real-vs-synthetic honesty flag (epic §6). LIDC DICOM is out of scope — convert first.
"""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass

import numpy as np

LUNG_BG_HU = -750.0

# Bundled real lung CT (F3.1): a clean axial lung-window thorax slice.
# Siemens SOMATOM Sensation 64; Wikimedia Commons, author Ptrump16, CC BY-SA 4.0.
# See data/ct_slices/NOTICE.md for the full attribution + share-alike obligation.
_HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLED_CT = os.path.normpath(
    os.path.join(_HERE, "..", "..", "data", "ct_slices", "thorax_ptrump16_cc-by-sa-4.0.jpg")
)
BUNDLED_ATTRIBUTION = (
    "CT background: Ptrump16, CC BY-SA 4.0 (Wikimedia Commons); "
    "changes: synthetic quantum-rolled lesion inserted."
)


@dataclass
class Background:
    array: np.ndarray    # 2D slice (HU when is_hu, else 0..255 intensity)
    source: str          # bundled_real | real_luna16 | npy | png | synthetic_dev
    spacing_mm: float
    is_hu: bool


def synthesize_lung_field(shape=(512, 512), spacing_mm: float = 0.7,
                          seed: int = 0) -> Background:
    """A clearly-labeled synthetic HU lung field (dev only): parenchyma + vessels + wall."""
    rng = np.random.default_rng(seed)
    h, w = shape
    img = np.full(shape, LUNG_BG_HU, dtype=np.float32)
    img += rng.normal(0.0, 45.0, shape).astype(np.float32)  # parenchymal grain

    # a few brighter vessel streaks
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(rng.integers(8, 16)):
        x0, y0 = rng.uniform(0, w), rng.uniform(0, h)
        ang = rng.uniform(0, np.pi)
        d = np.abs((xx - x0) * np.sin(ang) - (yy - y0) * np.cos(ang))
        img += (120.0 * np.exp(-(d ** 2) / (2 * 2.0 ** 2))).astype(np.float32)

    # denser chest-wall ring toward the border
    cy, cx = h / 2, w / 2
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) / (0.5 * min(h, w))
    wall = np.clip(r - 0.82, 0, None) * 2500.0
    img += wall.astype(np.float32)
    return Background(img, "synthetic_dev", spacing_mm, is_hu=True)


def _central_slice(vol: np.ndarray) -> np.ndarray:
    return vol[vol.shape[0] // 2] if vol.ndim == 3 else vol


def _read_mhd(path: str) -> Background:
    import SimpleITK as sitk

    image = sitk.ReadImage(path)
    arr = sitk.GetArrayFromImage(image)  # (z, y, x), already HU for CT
    spacing = float(image.GetSpacing()[0])  # in-plane mm/px
    return Background(_central_slice(arr).astype(np.float32), "real_luna16", spacing, True)


def _read_npy(path: str, spacing_mm: float) -> Background:
    arr = np.load(path)
    return Background(_central_slice(arr).astype(np.float32), "npy", spacing_mm, True)


def _read_png(path: str, spacing_mm: float) -> Background:
    from PIL import Image

    arr = np.asarray(Image.open(path).convert("L"), dtype=np.float32)
    return Background(arr, "png", spacing_mm, is_hu=False)


def _read_bundled() -> Background:
    from PIL import Image

    if not os.path.isfile(BUNDLED_CT):
        raise FileNotFoundError(
            f"bundled lung CT missing: {BUNDLED_CT} (see data/ct_slices/NOTICE.md)."
        )
    arr = np.asarray(Image.open(BUNDLED_CT).convert("L"), dtype=np.float32)
    return Background(arr, "bundled_real", 0.7, is_hu=False)


def load_background(source: str, spacing_mm: float, seed: int = 0) -> Background:
    """Load ONE background slice — the shared reference lung (F3.1, Q2).

    source:  "bundled" (default, real CC BY-SA lung) | "synthetic" (dev) | a dir
    (first readable LUNA16 .mhd / .npy / .png in it).
    """
    if source in ("bundled", "", "default"):
        return _read_bundled()
    if source in ("synthetic", "synth"):
        return synthesize_lung_field(spacing_mm=spacing_mm, seed=seed)
    if not os.path.isdir(source):
        raise FileNotFoundError(
            f"--ct-source '{source}' is not 'bundled', 'synthetic', or a directory."
        )
    for path in sorted(glob.glob(os.path.join(source, "*"))):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".mhd":
            return _read_mhd(path)
        if ext == ".npy":
            return _read_npy(path, spacing_mm)
        if ext in (".png", ".jpg", ".jpeg"):
            return _read_png(path, spacing_mm)
    raise FileNotFoundError(
        f"No readable CT in '{source}' (looked for *.mhd / *.npy / *.png / *.jpg). "
        f"Add a file or use --ct-source bundled."
    )


def load_backgrounds(source: str, spacing_mm: float, want: int, seed: int = 0) -> list[Background]:
    """Return at least `want` backgrounds (cycled if the pool is smaller)."""
    if source in ("synthetic", "", "synth"):
        return [
            synthesize_lung_field(spacing_mm=spacing_mm, seed=seed + i)
            for i in range(want)
        ]

    if not os.path.isdir(source):
        raise FileNotFoundError(
            f"--ct-source '{source}' is not a directory. Add CT files there or use "
            f"--ct-source synthetic."
        )

    pool: list[Background] = []
    for path in sorted(glob.glob(os.path.join(source, "*"))):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".mhd":
            pool.append(_read_mhd(path))
        elif ext == ".npy":
            pool.append(_read_npy(path, spacing_mm))
        elif ext in (".png", ".jpg", ".jpeg"):
            pool.append(_read_png(path, spacing_mm))

    if not pool:
        raise FileNotFoundError(
            f"No readable CT backgrounds in '{source}' (looked for *.mhd / *.npy / *.png). "
            f"Add files or use --ct-source synthetic."
        )

    return [pool[i % len(pool)] for i in range(want)]
