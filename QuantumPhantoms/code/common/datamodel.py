"""F1 data model — the entities the quantum roll introduces (epic §4).

Plain dataclasses, serialized to JSON. No DB. `TumorParams` is the `Sampler`
output contract that F2/F3/F4 consume; `QuantumRun` records one job's provenance
(raw bits, backend, job id, the job-level CHSH value). Nothing here knows about
pixels, CT, or the web render — that is F2/F3.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


# The five lung lobes the MVP renders (3-qubit code, 5 of 8 used; see decode.py).
LOBES = ("RUL", "RML", "RLL", "LUL", "LLL")
TYPES = ("solid", "part-solid", "ground-glass", "calcified")
MARGINS = ("smooth", "lobulated", "spiculated")


@dataclass
class TumorParams:
    """One decoded tumor = one grid tile. The Sampler output contract.

    `generation` is 0 for an independent/parent tile and 1 for a division
    daughter; tiles sharing a `lineage_id` are a sibling pair (epic §5).
    """

    size_mm: float
    type: str
    margin: str
    lobe: str
    lineage_id: str
    generation: int
    shot_index: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TumorParams":
        return cls(**d)


@dataclass
class QuantumRun:
    """Provenance for one pipeline run / one job (epic §4).

    `chsh_value` is a single job-level statistic (one Bell test over many shots
    across 4 settings), NOT a per-tile value — carried onto every tile with that
    tile's own `shot_index` (plan §4 honesty note).
    """

    backend_name: str
    job_id: str
    chsh_value: float
    chsh_settings: dict
    raw_bits: list[str] = field(default_factory=list)
    shot_indices: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "QuantumRun":
        return cls(**d)


@dataclass
class CohortTile:
    """One rendered grid cell: a real/synthetic CT slice + inserted lesion + label +
    provenance stamp (epic §4; introduced by F2, consumed by F3).

    The CHSH value / backend / job id are copied verbatim from the run's QuantumRun —
    F2 never recomputes quantum anything. `background_source` makes the real-vs-synthetic
    status of the CT background explicit (honesty gate, epic §6).
    """

    tile_id: str
    png_path: str           # zoom crop centred on the nodule
    size_mm: float
    type: str
    margin: str
    lobe: str
    lineage_id: str
    generation: int
    shot_index: int
    insert_xy: list[int]
    spacing_mm: float
    background_source: str
    backend_name: str
    job_id: str
    chsh_value: float
    full_png_path: str = ""      # whole-slice view (F3.1); shared across tiles of one run
    bbox: list[float] = None     # nodule box in full-slice NORMALISED coords [fx, fy, fw, fh]
    morphology_source: str = "classical"  # "quantum" when shape/texture seeded from raw_bits (F2.1)
    # F5 (grown renderer) — all optional; omitted from JSON when unset so procedural output is unchanged.
    renderer: str = None              # None/"procedural" | "grown+fitted" | "procedural-3d" | "procedural-fallback"
    host_id: str = None               # e.g. "LIDC-IDRI-0481"
    slice_z: int = None               # axial index of the exported slice in the host volume
    growth: list[dict] = field(default_factory=list)  # [{k, day, diameter_mm, role, png_path}]
    seed_hex_geometry: str = None
    seed_hex_appearance: str = None
    diag: dict = field(default_factory=dict)  # {volume_pd_pct, vdt_d, day_baseline, sigma_ratio_in_out, hu_source, ...}
    # D-SCALE (quantum seed shape for the grower) — optional, omitted when unset like the F5 fields.
    seed_source: str = None           # "ball" | "dscale:ch-qca:<region>"
    dscale: dict = field(default_factory=dict)  # {family, claim_level, witness_passed}

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in _F5_OPTIONAL:
            if d[k] in (None, [], {}):
                del d[k]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "CohortTile":
        return cls(**{k: v for k, v in d.items() if k in _COHORT_FIELDS})


_F5_OPTIONAL = ("renderer", "host_id", "slice_z", "growth", "seed_hex_geometry", "seed_hex_appearance", "diag",
                "seed_source", "dscale")
_COHORT_FIELDS = set(CohortTile.__dataclass_fields__)


