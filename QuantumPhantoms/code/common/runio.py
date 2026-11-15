"""Run context and the files the sections exchange in research_runs/<run>/. Sections pass files, never objects.

    C  certificate.json, certified_bits.bin (the bit pool)      B  cohort_params.json, quantum_run.json, rulebook.json
    D  dscale/dscale_run.json, dscale/seed_shapes.npz           A  sites.json
    E  growth.json, _roi/growth_<tile>.pkl                      F  tiles.json, tiles/*.png
    G  lineage_record.json, ledger.jsonl                        H  analysis.json
    claims.json  every hypothesis claim of B and D              jobs/<key>.json  submitted job ids (resume)
                                                                jobs/<key>.npz   raw bit arrays of every job
"""
from __future__ import annotations

import hashlib
import json
import pickle
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from common.datamodel import QuantumRun, TumorParams


@dataclass
class Ctx:
    run_dir: Path
    backend: str | None            # None = dry run on the local fake backend; "auto" or an IBM backend name = live
    shots: int
    qpu_spent: float = 0.0         # estimated QPU-s submitted so far in this run

    @property
    def live(self) -> bool:
        return self.backend is not None

    def path(self, *parts: str) -> Path:
        p = self.run_dir.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


# ---------------------------------------------------------------------------------------------- seeds / hashes
def derive_seed(seed_hex: str, label: str) -> int:
    """uint64 = first 8 bytes (big-endian) of sha256(seed || label)."""
    return int.from_bytes(hashlib.sha256(bytes.fromhex(seed_hex) + label.encode("utf-8")).digest()[:8], "big")


def rng(seed_hex: str, label: str) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(derive_seed(seed_hex, label)))


def tile_seeds(run_key: str, shot_index: int, generation: int, raw_bits: list[str]) -> tuple[str, str, str]:
    """(geometry seed, appearance seed, source) of one tumour. Each shot carries ~9 quantum bits, so these seeds
    are a replay key + provenance, not strong randomness."""
    word = str(raw_bits[shot_index % len(raw_bits)]) if raw_bits else ""

    def h(tag: str) -> str:
        return hashlib.sha256(f"{run_key}|{tag}|{shot_index}|{generation}|{word}".encode()).hexdigest()

    return h("geom"), h("app"), "quantum" if raw_bits else "classical"


def run_key(ctx_or_dir) -> str:
    """Replay key of the run: the SHA-256 of the bit pool (section C). Before the pool exists, and in run
    directories older than the pool: the roll's job id on hardware, else the run directory name."""
    d = Path(getattr(ctx_or_dir, "run_dir", ctx_or_dir))
    if (d / POOL_FILE).is_file():
        return sha256_file(d / POOL_FILE)
    f = d / "quantum_run.json"
    return (json.loads(f.read_text()).get("job_id") if f.is_file() else "") or d.name


def config_seed(ctx: Ctx, key: str) -> str:
    return hashlib.sha256(f"{run_key(ctx)}|{key}".encode()).hexdigest()


# ---------------------------------------------------------------------------------------------- bit pool (C -> B, D)
POOL_FILE = "certified_bits.bin"


def has_pool(ctx_or_dir) -> bool:
    return (Path(getattr(ctx_or_dir, "run_dir", ctx_or_dir)) / POOL_FILE).is_file()


def draw_bits(ctx: Ctx, label: str, n: int) -> np.ndarray:
    """The next n bits of the pool, recorded as certificate.json budget.spent[label] = n. Bits are handed out in
    the order of first use; asking again with the same label returns the same bits (a continued run replays its
    draws). A draw beyond the budget raises: there is no fallback to another source."""
    f = ctx.run_dir / "certificate.json"
    cert = load_json(f) or {}
    budget = cert.get("budget")
    if budget is None or not has_pool(ctx):
        raise RuntimeError("no bit pool in this run (section C did not pass)")
    spent = budget["spent"]
    if label in spent:
        if spent[label] != n:
            raise RuntimeError(f"bit pool: {label!r} drew {spent[label]} bits earlier, {n} asked now")
        start = sum(v for k, v in list(spent.items())[:list(spent).index(label)])
    else:
        start = sum(spent.values())
        if start + n > budget["available"]:
            raise RuntimeError(f"bit pool exhausted: {label!r} asks {n} bits, {budget['available'] - start} of "
                               f"{budget['available']} left")
        spent[label] = n
        save_json(f, cert)
    return np.unpackbits(np.fromfile(ctx.run_dir / POOL_FILE, dtype=np.uint8))[start:start + n]


def pair_map(run_dir) -> dict[tuple[int, int], float]:
    """Bell map of the run: (a, b) with a < b -> CHSH S of that coupler; empty when section C has not run."""
    cert = load_json(Path(run_dir) / "certificate.json") or {}
    out = {}
    for k, S in cert.get("pair_map", {}).items():
        a, b = sorted(int(q) for q in k.split("-"))
        out[(a, b)] = float(S)
    return out


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def code_hash(folder: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(Path(folder).rglob("*.py")):
        h.update(f.relative_to(folder).as_posix().encode() + b"\0" + hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()


def git_state(path: Path) -> dict | None:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=True)
        status = subprocess.run(["git", "status", "--porcelain", "--", "."], cwd=path, capture_output=True, text=True)
        return {"commit": commit.stdout.strip(), "dirty": bool(status.stdout.strip())}
    except Exception:
        return None


def clean(o):
    """JSON-safe copy (numpy scalars / arrays, non-finite floats, private keys)."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.generic):
        return clean(o.item())
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, float) and not np.isfinite(o):
        return None
    return o


def save_json(path: Path, obj) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(clean(obj), indent=1, default=str))


def load_json(path: Path):
    return json.loads(Path(path).read_text()) if Path(path).is_file() else None


# ---------------------------------------------------------------------------------------------- cohort (B)
def tile_id(p) -> str:
    return f"tile_{p.shot_index}_{p.generation}"


def load_cohort(run_dir) -> tuple[list[TumorParams], QuantumRun]:
    d = Path(run_dir)
    cp, qr = load_json(d / "cohort_params.json"), load_json(d / "quantum_run.json")
    if cp is None or qr is None:
        raise FileNotFoundError(f"{d} has no cohort_params.json / quantum_run.json (section B)")
    return [TumorParams.from_dict(x) for x in cp], QuantumRun.from_dict(qr)


def group_by_lineage(params) -> list[list]:
    """Sibling pairs share a lineage_id; the parent comes first (placement and render order)."""
    groups: dict[str, list] = {}
    for p in params:
        groups.setdefault(p.lineage_id, []).append(p)
    return list(groups.values())


def draws(run_dir) -> list[dict]:
    """One dict per tumour for the quantum-growth circuits: id, size, type, margin and its geometry seed."""
    params, qrun = load_cohort(run_dir)
    key = run_key(run_dir)
    out = []
    for p in params:
        geom, app, src = tile_seeds(key, p.shot_index, p.generation, qrun.raw_bits)
        out.append({"tile_id": tile_id(p), "size_mm": p.size_mm, "type": p.type, "margin": p.margin,
                    "seed_hex": geom, "seed_hex_appearance": app, "morphology_source": src})
    return out


# ---------------------------------------------------------------------------------------------- claims (B, D)
def add_claims(ctx: Ctx, stage: str, claims: list[dict]) -> None:
    old = [c for c in (load_json(ctx.run_dir / "claims.json") or []) if c.get("stage") != stage]
    save_json(ctx.path("claims.json"), old + [{"stage": stage} | c for c in claims])


# ---------------------------------------------------------------------------------------------- seed shapes (D -> E)
def save_seed_shapes(ctx: Ctx, masks: dict[str, np.ndarray], tiles: dict, family: str) -> None:
    """masks: tile_id -> 3-D uint8 occupancy at 0.5 mm; tiles: tile_id -> info (region, claim_level, ...)."""
    np.savez_compressed(ctx.path("dscale", "seed_shapes.npz"), **masks)
    save_json(ctx.path("dscale", "seed_tiles.json"), {t: {"family": family} | v for t, v in tiles.items()})


def load_seed_shapes(run_dir) -> tuple[dict, dict]:
    d = Path(run_dir) / "dscale"
    if not (d / "seed_shapes.npz").is_file():
        return {}, {}
    with np.load(d / "seed_shapes.npz") as z:
        masks = {k: z[k] for k in z.files}
    return masks, load_json(d / "seed_tiles.json") or {}


def seed_label(tiles: dict, tid: str) -> str:
    info = tiles.get(tid, {})
    return f"dscale:{info.get('family', 'ch-qca')}:{info.get('region', 'seed')}"


# ---------------------------------------------------------------------------------------------- growth (E -> F)
def save_growth(run_dir, tid: str, growth, error: str | None) -> None:
    d = Path(run_dir) / "_roi"                             # gitignored: the lattice is cut from host voxels
    d.mkdir(exist_ok=True)
    with open(d / f"growth_{tid}.pkl", "wb") as f:
        pickle.dump({"growth": growth, "error": error}, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_growth(run_dir, tid: str) -> dict | None:
    f = Path(run_dir) / "_roi" / f"growth_{tid}.pkl"
    if not f.is_file():
        return None
    with open(f, "rb") as fh:
        return pickle.load(fh)
