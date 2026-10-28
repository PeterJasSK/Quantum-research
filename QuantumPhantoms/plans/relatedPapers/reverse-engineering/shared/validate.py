"""Contract validator.

    python -m shared.validate --stubs          # every stub in shared/stubs/
    python -m shared.validate --status         # every <L>_<name>/status.json + the 21-target set
    python -m shared.validate path/to/x.json   # any letter output (.json or ledger .jsonl)

Schema is chosen from the file's `contract` field. Beyond the JSON Schema it checks: every
{path, sha256} reference exists and matches, NIfTI/NPZ obey contracts/VOLUMES.md, all NIfTI of one
manifest share a grid, rulebook CPT rows sum to 1 and its hash, receipt signatures, ledger chain.
Exit code 0 only if everything passes.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from shared import CONTRACTS, LETTERS, RE_ROOT, STUBS
from shared.seedhash import canonical_json, hash_json, sha256_bytes, sha256_file
from shared.volumes import HU_MAX, HU_MIN, IDENTITY, read_header, read_volume, same_grid

NIFTI_DTYPE = {
    "host_ct": "16-bit signed integer",
    "hybrid_ct": "16-bit signed integer",
    "lungs": "8-bit unsigned integer",
    "lobes": "8-bit unsigned integer",
    "vessels": "8-bit unsigned integer",
    "airway": "8-bit unsigned integer",
    "body": "8-bit unsigned integer",
    "lesion_mask": "8-bit unsigned integer",
    "sigma_map": "32-bit float",
}
NIFTI_VALUES = {"lungs": {0, 1, 2}, "lobes": {0, 1, 2, 3, 4, 5}, "vessels": {0, 1}, "airway": {0, 1},
                "body": {0, 1}, "lesion_mask": {0, 1}}
NPZ_KEYS = {
    "seed_shape": {"occupancy": ("uint8", 3), "spacing_mm_xyz": ("float64", 1)},
    "growth_trajectory": {"state": ("uint8", 3)},
}


@lru_cache(maxsize=1)
def _registry() -> tuple[Registry, dict]:
    schemas = {}
    resources = []
    for f in sorted(CONTRACTS.glob("*.schema.json")):
        sch = json.loads(f.read_text())
        resources.append((sch["$id"], Resource.from_contents(sch)))
        if not f.name.startswith("_"):
            schemas[f.name.removesuffix(".schema.json")] = sch
    return Registry().with_resources(resources), schemas


def contracts() -> list[str]:
    return sorted(_registry()[1])


def schema_errors(obj, contract: str | None = None) -> list[str]:
    registry, schemas = _registry()
    contract = contract or (obj.get("contract") if isinstance(obj, dict) else None)
    if contract not in schemas:
        return [f"/: unknown or missing contract {contract!r} (known: {', '.join(schemas)})"]
    v = Draft202012Validator(schemas[contract], registry=registry,
                             format_checker=Draft202012Validator.FORMAT_CHECKER)
    errs = sorted(v.iter_errors(obj), key=lambda e: list(e.absolute_path))
    return [f"/{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in errs]


def _file_refs(node, key=None):
    """Yield (parent_key, ref) for every {path, sha256} object in the document."""
    if isinstance(node, dict):
        if "path" in node and "sha256" in node:
            yield key, node
        for k, v in node.items():
            yield from _file_refs(v, k)
    elif isinstance(node, list):
        for v in node:
            yield from _file_refs(v, key)


def _check_nifti(path: Path, key: str | None) -> list[str]:
    errs = []
    h = read_header(path)
    if len(h["size_xyz"]) != 3:
        errs.append(f"{path.name}: must be 3-D, got {len(h['size_xyz'])}-D")
    if not np.allclose(h["direction"], IDENTITY, atol=1e-6):
        errs.append(f"{path.name}: direction must be LPS identity, got {h['direction']}")
    if min(h["spacing_mm_xyz"]) <= 0:
        errs.append(f"{path.name}: spacing must be > 0")
    want = NIFTI_DTYPE.get(key)
    if want and h["dtype"] != want:
        errs.append(f"{path.name} ({key}): dtype must be {want}, got {h['dtype']}")
    if key in NIFTI_VALUES or want == NIFTI_DTYPE["host_ct"]:
        arr, _ = read_volume(path, reorient=False)
        if key in NIFTI_VALUES:
            extra = set(np.unique(arr).tolist()) - NIFTI_VALUES[key]
            if extra:
                errs.append(f"{path.name} ({key}): unexpected label values {sorted(extra)[:5]}")
        elif arr.min() < HU_MIN or arr.max() > HU_MAX:
            errs.append(f"{path.name} ({key}): HU outside [{HU_MIN}, {HU_MAX}]")
    return errs


def _check_cpt(table, where: str) -> list[str]:
    if all(isinstance(x, (int, float)) for x in table):
        return [] if abs(sum(table) - 1.0) < 1e-6 else [f"{where}: CPT row sums to {sum(table)}"]
    return [e for i, t in enumerate(table) for e in _check_cpt(t, f"{where}[{i}]")]


def _semantic_errors(obj: dict, path: Path) -> list[str]:
    errs = []
    contract = obj.get("contract")
    niftis = []
    for key, ref in _file_refs(obj):
        target = (path.parent / ref["path"]).resolve()
        if not target.is_file():
            errs.append(f"{ref['path']}: referenced file missing")
            continue
        if sha256_file(target) != ref["sha256"]:
            errs.append(f"{ref['path']}: sha256 mismatch")
            continue
        if target.name.endswith(".nii.gz") or target.suffix == ".nii":
            niftis.append(target)
            errs += _check_nifti(target, key)
        elif target.suffix == ".npz" and contract in NPZ_KEYS:
            with np.load(target, allow_pickle=False) as z:
                for k, (dtype, ndim) in NPZ_KEYS[contract].items():
                    if k not in z.files:
                        errs.append(f"{target.name}: missing NPZ key '{k}'")
                    elif str(z[k].dtype) != dtype or z[k].ndim != ndim:
                        errs.append(f"{target.name}: '{k}' must be {dtype} ndim={ndim}, "
                                    f"got {z[k].dtype} ndim={z[k].ndim}")
    if len(niftis) > 1:
        first = read_header(niftis[0])
        errs += [f"{p.name}: grid differs from {niftis[0].name}" for p in niftis[1:]
                 if not same_grid(first, read_header(p))]
    if contract == "anatomy_masks" and niftis:
        h = read_header(niftis[0])
        g = obj["grid"]
        if not same_grid(h, {**g, "direction": IDENTITY}):
            errs.append("/grid: does not match the NIfTI header of the referenced volumes")
    if contract == "rulebook":
        for n in obj["nodes"]:
            tables = [n["cpt"]] if "cpt" in n else list(n["cpt_by_context"].values())
            for t in tables:
                errs += _check_cpt(t, f"/nodes/{n['name']}")
        if hash_json(obj, exclude=["rulebook_hash", "created_utc", "produced_by"]) != obj["rulebook_hash"]:
            errs.append("/rulebook_hash: does not match hash_json(doc minus hash/created_utc/produced_by)")
    if contract == "quantum_job_record" and "counts" in obj and sum(obj["counts"].values()) != obj["shots"]:
        errs.append("/counts: total does not equal shots")
    if contract == "receipt" and obj.get("signature"):
        errs += _verify_signature(obj)
    return errs


def _verify_signature(obj: dict) -> list[str]:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    sig = obj["signature"]
    try:
        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(sig["public_key_b64"]))
        pub.verify(base64.b64decode(sig["sig_b64"]), canonical_json({"commit": obj["commit"], "fill": obj["fill"]}))
    except (InvalidSignature, ValueError):
        return ["/signature: Ed25519 verification failed (receipt was modified or wrongly signed)"]
    return []


def ledger_errors(path: Path) -> list[str]:
    errs = []
    prev = "0" * 64
    for i, line in enumerate(path.read_text().splitlines()):
        entry = json.loads(line)
        errs += [f"line {i}{e}" for e in schema_errors(entry, "ledger_entry")]
        if entry.get("index") != i:
            errs.append(f"line {i}/index: expected {i}")
        if entry.get("prev_hash") != prev:
            errs.append(f"line {i}/prev_hash: chain broken")
        body = {k: v for k, v in entry.items() if k != "entry_hash"}
        if sha256_bytes(canonical_json(body)) != entry.get("entry_hash"):
            errs.append(f"line {i}/entry_hash: does not match entry content")
        prev = entry.get("entry_hash")
    return errs


def validate_file(path: str | Path) -> tuple[str, list[str]]:
    """Return (contract, errors) for one contract file."""
    path = Path(path).resolve()
    if path.suffix == ".jsonl":
        return "ledger_entry", ledger_errors(path)
    try:
        obj = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return "?", [f"/: cannot read JSON ({e})"]
    errs = schema_errors(obj)
    if not errs:
        errs = _semantic_errors(obj, path)
    return obj.get("contract", "?") if isinstance(obj, dict) else "?", errs


def stub_files() -> list[Path]:
    """Contract files in shared/stubs/ (JSON with a `contract` key, or ledger .jsonl)."""
    out = []
    for f in sorted(STUBS.glob("*/*.json*")):
        if f.suffix == ".jsonl" or "contract" in json.loads(f.read_text()):
            out.append(f)
    return out


def check_status_set(root: Path = RE_ROOT) -> tuple[dict, list[str]]:
    """Validate every letter status.json and the global 21-target set. Returns ({letter: status}, errors)."""
    statuses, errs = {}, []
    numbers = []
    for letter, folder in LETTERS.items():
        f = root / folder / "status.json"
        if not f.is_file():
            errs.append(f"{folder}/status.json: missing")
            continue
        obj = json.loads(f.read_text())
        e = schema_errors(obj, "target_status")
        if not e and obj["letter"] != letter:
            e.append(f"/letter: {obj['letter']!r} in folder {folder}")
        for t in obj.get("targets", []) if not e else []:
            numbers.append(t["number"])
            if not (f.parent / t["dossier"]).is_file():
                e.append(f"/targets/#{t['number']}/dossier: {t['dossier']} missing")
        errs += [f"{folder}/status.json {x}" for x in e]
        statuses[letter] = obj
    dup = sorted({n for n in numbers if numbers.count(n) > 1})
    missing = sorted(set(range(1, 22)) - set(numbers))
    if dup:
        errs.append(f"target numbers duplicated across letters: {dup}")
    if missing:
        errs.append(f"target numbers missing: {missing}")
    return statuses, errs


def _report(path: Path, contract: str, errs: list[str]) -> bool:
    try:
        rel = path.resolve().relative_to(RE_ROOT)
    except ValueError:
        rel = path
    print(f"{'OK  ' if not errs else 'FAIL'} {rel} ({contract})")
    for e in errs:
        print(f"     {e}")
    return not errs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m shared.validate", description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--stubs", action="store_true", help="validate every stub in shared/stubs/")
    ap.add_argument("--status", action="store_true", help="validate every letter status.json")
    a = ap.parse_args(argv)
    if not (a.files or a.stubs or a.status):
        ap.error("give files, --stubs or --status")
    ok = True
    for f in (stub_files() if a.stubs else []) + a.files:
        ok &= _report(f, *validate_file(f))
    if a.status:
        statuses, errs = check_status_set()
        for letter in statuses:
            n = len(statuses[letter]["targets"])
            if not any(x.startswith(LETTERS[letter] + "/") for x in errs):
                print(f"OK   {LETTERS[letter]}/status.json (target_status, {n} targets)")
        for e in errs:
            print(f"FAIL {e}")
        ok &= not errs
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
