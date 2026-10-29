"""Contract I/O for D: load + validate the inputs, the certificate gate, write contract files.

Inputs (defaults = shared/stubs): tumor_draw, certificate, compiled_circuit. D only records tumor_draw and
compiled_circuit as upstream refs (plan Q1); the certificate gates the run and supplies every seed.
"""
from __future__ import annotations

import json
from pathlib import Path

from shared import CONTRACT_VERSION, RE_ROOT, STUBS
from shared.seedhash import sha256_file
from shared.simbackend import sim_label
from shared.validate import validate_file

LETTER = "D"
LETTER_DIR = RE_ROOT / "D_quantum_growth"
DEFAULTS = {
    "tumor_draw": STUBS / "tumor_draw" / "tumor_draw.json",
    "certificate": STUBS / "certificate" / "certificate.json",
    "compiled_circuit": STUBS / "compiled_circuit" / "compiled_circuit.json",
}


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def certificate_refusal(cert: dict) -> str | None:
    """Epic §5: a failed certificate rejects the draw — no retry, no fallback seed."""
    if cert.get("status") != "pass" or not cert.get("extracted_seed_hex"):
        return f"draw rejected: certificate status={cert.get('status')}"
    return None


def validate_inputs(paths: dict[str, Path]) -> list[str]:
    errs = []
    for contract, p in paths.items():
        got, e = validate_file(p)
        if got != contract:
            e = [f"expected contract '{contract}', file declares '{got}'"] + e
        errs += [f"{p}: {x}" for x in e]
    return errs


def load_inputs(overrides: dict[str, str | None] | None = None) -> tuple[dict[str, Path], dict[str, dict]]:
    paths = {k: Path(v) for k, v in DEFAULTS.items()}
    for k, v in (overrides or {}).items():
        if v:
            paths[k] = Path(v)
    docs = {k: read_json(p) for k, p in paths.items()}
    return paths, docs


def ref(target: Path, frm: Path) -> dict:
    """{path, sha256} of `target`, path relative to the directory of file `frm`."""
    return {"path": Path(target).resolve().relative_to(Path(frm).parent.resolve(), walk_up=True).as_posix(),
            "sha256": sha256_file(target)}


def envelope(contract: str, run, mode: str, upstream: list[dict] | None = None) -> dict:
    return {
        "contract": contract,
        "contract_version": CONTRACT_VERSION,
        "produced_by": {"letter": LETTER, "tool": run.tool, "run_id": run.path.name, "code_hash": run.code_hash},
        "created_utc": run.created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stub": False,
        "upstream": upstream or [],
        "sim_label": sim_label(mode),
        "hardware": None,
    }


def write_contract(path: Path, obj: dict) -> dict:
    """Write JSON, validate against its contract, return {path, sha256} (path = file name)."""
    path = Path(path)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    _, errs = validate_file(path)
    if errs:
        raise ValueError(f"{path} violates its contract:\n  " + "\n  ".join(errs))
    return {"path": path.name, "sha256": sha256_file(path)}


def write_sidecar(path: Path, obj: dict) -> dict:
    path = Path(path)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    return {"path": path.name, "sha256": sha256_file(path)}


def begin(mode: str, tag: str, tool: str, overrides: dict | None = None):
    """Load inputs, apply the certificate gate, start the run. Returns (run, paths, docs, seed_hex) or
    (run, None, None, None) when the draw is rejected (run already finished, caller exits 2)."""
    from shared.runrecord import start_run

    paths, docs = load_inputs(overrides)
    refusal = certificate_refusal(docs["certificate"])
    run = start_run(LETTER_DIR, tag, sim_mode=mode, tool=tool)
    for c, p in paths.items():
        run.add_input(p, c)
    if refusal:
        run.finish(refusal)
        print(refusal)
        return run, None, None, None
    errs = validate_inputs(paths)
    if errs:
        raise ValueError("input contract violations:\n  " + "\n  ".join(errs))
    seed = docs["certificate"]["extracted_seed_hex"]
    run.seed_hex = seed
    return run, paths, docs, seed


def add_input_args(ap) -> None:
    ap.add_argument("--tumor-draw")
    ap.add_argument("--certificate")
    ap.add_argument("--compiled-circuit")


def overrides_of(args) -> dict:
    return {"tumor_draw": args.tumor_draw, "certificate": args.certificate,
            "compiled_circuit": args.compiled_circuit}


def job_id(seed_hex: str, *labels) -> str:
    """Deterministic simulator job id (same inputs -> byte-identical outputs)."""
    from shared.seedhash import sha256_bytes

    return "sim-" + sha256_bytes(("|".join([seed_hex, *map(str, labels)])).encode())[:32]
