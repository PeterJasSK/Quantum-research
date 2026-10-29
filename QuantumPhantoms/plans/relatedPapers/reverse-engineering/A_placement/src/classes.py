"""Placement-class rule (target #18), the single source for the reproduction and for placement.

Definitions re-implemented from Ambrosini et al. [F01], who cite Kostis et al. (200 nodules):
    free (well-circumscribed)  no voxel contact with vessel or lung wall
    juxtavascular (vascularized)  shares voxels with a large vessel, placed at a bifurcation
    juxtapleural  shape merged with the lung-mask contour
SYN-LUNGS [A01] gives no rule or threshold. Every threshold below was fixed BEFORE the
reproduction run (plan Q5) and is never fitted to the Kostis proportions.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import binary_dilation, generate_binary_structure

CLASSES = ("free", "juxtavascular", "juxtapleural")
CLASS_CODE = {name: i + 1 for i, name in enumerate(CLASSES)}  # 0 = ambiguous / not eligible

# --- thresholds (plan Q5) -----------------------------------------------------------------------
RING_VOX = 1                 # contact ring: one 6-connected dilation step around the nodule
PLEURA_CONTACT_FRAC = 0.10   # ring fraction outside lungs ∪ nodule ∪ airway => merged with lung contour
VESSEL_CONTACT_VOX = 5       # ring voxels on a vessel => shares voxels with a vessel
MIN_VESSEL_RADIUS_MM = 1.5   # "large vessel" gate for bifurcation points
SITE_MARGIN_MM = 3.0         # clearance band separating free from contact classes
CONSENSUS_LEVEL = 0.5        # pylidc consensus(clevel)
MIN_READERS = 3              # radiologists who outlined the nodule (of 4)
MIN_DIAMETER_MM = 3.0        # LIDC outlines nodules >= 3 mm

# --- reproduction reference (Kostis via [F01]: "almost half / around one-third / approaching one-quarter")
KOSTIS = {"juxtavascular": 0.45, "free": 0.33, "juxtapleural": 0.22}
KOSTIS_ORDER = ("juxtavascular", "free", "juxtapleural")
AGREEMENT_PP = 0.10

THRESHOLDS = {
    "ring_vox": RING_VOX, "pleura_contact_frac": PLEURA_CONTACT_FRAC,
    "vessel_contact_vox": VESSEL_CONTACT_VOX, "min_vessel_radius_mm": MIN_VESSEL_RADIUS_MM,
    "site_margin_mm": SITE_MARGIN_MM, "consensus_level": CONSENSUS_LEVEL,
    "min_readers": MIN_READERS, "min_diameter_mm": MIN_DIAMETER_MM,
}


def contact_ring(nodule: np.ndarray) -> np.ndarray:
    ring = binary_dilation(nodule, generate_binary_structure(3, 1), iterations=RING_VOX)
    return ring & ~nodule


def classify_mask(nodule: np.ndarray, lungs: np.ndarray, vessels: np.ndarray,
                  airway: np.ndarray) -> tuple[str, dict]:
    """Class of a real (annotated) nodule; all arrays share one grid or one crop of it.

    `vessels` must not contain the nodule's own voxels. Precedence pleura > vessel > free,
    so the classes are mutually exclusive as in Kostis.
    """
    nodule = nodule.astype(bool)
    ring = contact_ring(nodule)
    n_ring = int(ring.sum())
    outside = ~((lungs > 0) | nodule | (airway > 0))
    pleura_frac = float(outside[ring].sum()) / max(n_ring, 1)
    vessel_vox = int((vessels[ring] > 0).sum())
    if pleura_frac >= PLEURA_CONTACT_FRAC:
        cls = "juxtapleural"
    elif vessel_vox >= VESSEL_CONTACT_VOX:
        cls = "juxtavascular"
    else:
        cls = "free"
    return cls, {"ring_vox": n_ring, "pleura_frac": round(pleura_frac, 4), "vessel_contact_vox": vessel_vox}


def classify_site_arrays(d_pleura, d_vessel, d_bif, r: float, margin: float = SITE_MARGIN_MM) -> np.ndarray:
    """Vectorised class code (CLASS_CODE, 0 = ambiguous) of a sphere of radius r centred at each voxel.

    juxtapleural   sphere crosses the lung contour: d_pleura <= r
    juxtavascular  sphere overlaps a vessel near a large-vessel bifurcation: d_vessel <= r and
                   d_bif <= r, with the pleura clear by the margin
    free           pleura and vessels both clear by the margin
    The band between contact and clearance is ambiguous and never emitted.
    """
    d_pleura, d_vessel, d_bif = (np.asarray(a) for a in (d_pleura, d_vessel, d_bif))
    out = np.zeros(np.broadcast(d_pleura, d_vessel, d_bif).shape, np.uint8)
    pleura_clear = d_pleura > r + margin
    out[pleura_clear & (d_vessel > r + margin)] = CLASS_CODE["free"]
    out[pleura_clear & (d_vessel > 0) & (d_vessel <= r) & (d_bif <= r)] = CLASS_CODE["juxtavascular"]
    out[(d_pleura > 0) & (d_pleura <= r)] = CLASS_CODE["juxtapleural"]
    return out


def classify_site(d_pleura: float, d_vessel: float, d_bif: float, r: float) -> str | None:
    code = int(classify_site_arrays(d_pleura, d_vessel, d_bif, r))
    return CLASSES[code - 1] if code else None


def wilson_ci(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, float(mid - half)), min(1.0, float(mid + half))


def agreement(props: dict) -> dict:
    """Pass = every class within ±AGREEMENT_PP of Kostis AND the Kostis ordering holds."""
    within = {c: abs(props[c] - KOSTIS[c]) <= AGREEMENT_PP for c in CLASSES}
    order = props[KOSTIS_ORDER[0]] > props[KOSTIS_ORDER[1]] > props[KOSTIS_ORDER[2]]
    return {"within_pp": within, "ordering_holds": bool(order), "pass": bool(all(within.values()) and order)}
