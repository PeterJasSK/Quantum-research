# Volume conventions (FROZEN v1.0.0, 2026-10-28)

The epic is **fully 3-D**. Every imaging artifact (masks, context features, cell lattices, PSF/NPS, hybrid CT)
is a 3-D volume; 2-D slices are a final export only (PNG under a letter's `figures/`), never a contract input.
Use [`shared/volumes.py`](../volumes.py): it is the only sanctioned NIfTI / NPZ I/O path.

## NIfTI (everything on the host grid)

| Rule | Value |
|---|---|
| File | NIfTI-1, `.nii.gz`, written by SimpleITK (`write_volume`) |
| Physical frame | DICOM/ITK **LPS** (x → patient Left, y → Posterior, z → Superior) |
| Direction | identity after `sitk.DICOMOrient(img, "LPS")`; the validator rejects anything else |
| Array order | numpy **(z, y, x)** (`sitk.GetArrayFromImage`) |
| Vector order in JSON | **(x, y, z)** for `size_xyz`, `spacing_mm_xyz`, `origin_mm_lps`, `center_mm_lps`; a field ending in `_zyx` is numpy order |
| Spacing | mm, inherited from the host DICOM; never implicitly resampled. A letter that resamples records the new spacing in its manifest |
| Grid | all NIfTI referenced by one manifest share size, spacing, origin, direction (`check_same_grid`) |

| Content (manifest field name) | dtype | Values |
|---|---|---|
| CT: `host_ct`, `hybrid_ct` | `int16` | HU stored directly (no slope/intercept), clipped to [−1024, 3071]; air = −1000 |
| Binary masks: `vessels`, `airway`, `body`, `lesion_mask` | `uint8` | {0, 1} |
| `lungs` | `uint8` | 0 background, 1 right, 2 left |
| `lobes` | `uint8` | 0, 1 LUL, 2 LLL, 3 RUL, 4 RML, 5 RLL (lungmask LTRCLobes order) |
| Continuous maps: `sigma_map` | `float32` | physical units (σ in HU) |

## NPZ (off-grid arrays: lattices, kernels, spectra)

Write with `volumes.save_npz` (deterministic bytes), read with `volumes.load_npz(path, required=...)`.
Every NPZ holds 3-D arrays in **(z, y, x)** plus `spacing_mm_xyz` (float64, shape (3,)). Placement in the host
is given by the manifest's `origin_mm_lps` (LPS position of lattice index (0, 0, 0)) + `spacing_mm_xyz`.

| Contract | NPZ | Keys |
|---|---|---|
| `seed_shape` | `seed_shape.npz` | `occupancy` uint8 3-D {0, 1}; `spacing_mm_xyz` float64 (3,) |
| `growth_trajectory` | `step_<NNNN>.npz` | `state` uint8 3-D (cell codes below); `spacing_mm_xyz` float64 (3,) |

**Cell states** (`state`): 0 host/empty · 1 proliferating · 2 dormant (non-proliferating) · 3 necrotic.
Codes 4–15 are reserved for letter-specific states and must be named in the manifest's `state_labels`.

## Privacy

No patient voxels enter any generator. Host volumes are only *read* to place, fingerprint and insert into;
lesion appearance comes from fitted parameters (`lesion_model_library`) and published statistics only.
