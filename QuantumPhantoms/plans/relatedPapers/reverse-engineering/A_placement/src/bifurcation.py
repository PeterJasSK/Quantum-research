"""Large-vessel bifurcation points (plan AC-7): Ambrosini [F01] places vascularized nodules
"at a large vessel bifurcation".

3-D skeleton of the vessel mask -> skeleton voxels with >= 3 skeleton neighbours (26-connectivity)
-> kept where the local vessel radius (EDT inside the vessel) is >= MIN_VESSEL_RADIUS_MM.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import convolve, distance_transform_edt
from skimage.morphology import skeletonize

from A_placement.src.classes import MIN_VESSEL_RADIUS_MM


def bifurcations(vessels: np.ndarray, spacing_zyx, min_radius_mm: float = MIN_VESSEL_RADIUS_MM) -> np.ndarray:
    """Boolean mask of large-vessel branch points, same shape as `vessels`."""
    v = vessels > 0
    skel = skeletonize(v)
    nb = convolve(skel.astype(np.uint8), np.ones((3, 3, 3), np.uint8), mode="constant") - skel
    radius = distance_transform_edt(v, sampling=spacing_zyx)
    return skel & (nb >= 3) & (radius >= min_radius_mm)
