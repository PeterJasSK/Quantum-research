"""Commit-before-draw receipt (AC-3..AC-6).

    python -m G_provenance.src.receipt commit [--rulebook rulebook.json]
    python -m G_provenance.src.receipt fill --commit <committed receipt.json> [--job ..] [--certificate ..]
        [--witness ..]... [--draw ..] [--hybrid ..]

commit: hash the rulebook and the producing code, sign {commit, fill: null}, append to the ledger.
fill:   bind the job, certificate, witnesses, draw and the hybrid CT voxels; check order and code
        against the commitment; sign; append the final entry. Inputs default to shared/stubs/.
Every receipt file is written as canonical JSON so that sha256(file) is what the ledger holds.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from G_provenance.src import keys as keymod
from G_provenance.src import ledger as ledgermod
from G_provenance.src.hashing import commit_code_hash, producer_code_hashes, voxel_hashes_of_file
from shared import CONTRACT_VERSION, RE_ROOT, STUBS
from shared.runrecord import start_run
from shared.seedhash import canonical_json, hash_json, sha256_bytes, sha256_file
from shared.validate import validate_file

LETTER_DIR = RE_ROOT / "G_provenance"
SIGNED_OVER = "canonical_json({commit, fill})"
STUB_ORDER_NOTE = "order not provable (stub input)"


def _utc(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(target: Path, base_file: Path) -> str:
    return Path(target).resolve().relative_to(Path(base_file).resolve().parent, walk_up=True).as_posix()


def file_ref(target: Path, base_file: Path) -> dict:
    return {"path": rel(target, base_file), "sha256": sha256_file(target)}


def upstream_ref(contract: str, target: Path, base_file: Path) -> dict:
    return {"contract": contract, **file_ref(target, base_file)}


def sign(key: Ed25519PrivateKey, commit: dict, fill: dict | None) -> dict:
    sig = key.sign(canonical_json({"commit": commit, "fill": fill}))
    return {"alg": "Ed25519", "public_key_b64": keymod.public_b64(key),
            "sig_b64": base64.b64encode(sig).decode(), "signed_over": SIGNED_OVER}


def write_receipt(path: Path, doc: dict) -> str:
    """Canonical bytes, so sha256(file) = sha256(canonical_json(doc)) and re-serialising is stable."""
    Path(path).write_bytes(canonical_json(doc))
    return sha256_file(path)


def _envelope(run, upstream: list[dict]) -> dict:
    return {"contract": "receipt", "contract_version": CONTRACT_VERSION,
            "produced_by": {"letter": "G", "tool": run.tool, "run_id": run.path.name, "code_hash": run.code_hash},
            "created_utc": _utc(run.created), "stub": False, "upstream": upstream}


def _check_file(path: Path) -> list[str]:
    _, errs = validate_file(path)
    return [f"{path.name}: {e}" for e in errs]


def _load(path: Path) -> dict:
    return json.loads(Path(path).read_text())


# ------------------------------------------------------------------ commit

def commit(rulebook: Path, ledger_path: Path, keys_dir: Path) -> int:
    rulebook = Path(rulebook).resolve()
    errs = _check_file(rulebook)
    doc = _load(rulebook)
    if hash_json(doc, exclude=["rulebook_hash", "created_utc", "produced_by"]) != doc.get("rulebook_hash"):
        errs.append("rulebook_hash does not match the rulebook content")
    if errs:
        print("rulebook rejected:\n  " + "\n  ".join(errs))
        return 1
    key = keymod.load_signer(keys_dir)
    run = start_run(LETTER_DIR, "commit", tool="G_provenance:commit")
    hashes = producer_code_hashes()
    cm = {"rulebook_path": rulebook.as_posix(), "rulebook_hash": doc["rulebook_hash"], "code_hashes": hashes}
    c = {"rulebook_hash": doc["rulebook_hash"], "code_hash": commit_code_hash(hashes),
         "committed_utc": _utc(run.created)}
    f = run.path / "receipt.json"
    body = {**_envelope(run, [upstream_ref("rulebook", rulebook, f)]), "commit": c, "fill": None,
            "signature": sign(key, c, None), "state": "committed"}
    sha = write_receipt(f, body)
    entry = ledgermod.append(sha, ledger_path)
    cm["ledger_index"] = entry["index"]
    (run.path / "commit_manifest.json").write_text(json.dumps(cm, indent=2) + "\n")
    errs = _check_file(f)
    run.add_input(rulebook, "rulebook")
    run.add_output(f, "receipt")
    run.finish("commit-before-draw receipt")
    if errs:
        print("\n".join(errs))
        return 1
    print(f"committed: ledger index {entry['index']}\n  receipt {f}")
    return 0


# ------------------------------------------------------------------ fill

def _commit_state(commit_receipt: Path, ledger_path: Path) -> tuple[dict, dict, dict]:
    doc = _load(commit_receipt)
    manifest = _load(Path(commit_receipt).parent / "commit_manifest.json")
    entry = ledgermod.find_receipt(sha256_file(commit_receipt), ledger_path)
    if entry is None:
        raise ValueError("committed receipt is not in the ledger")
    if commit_code_hash(manifest["code_hashes"]) != doc["commit"]["code_hash"]:
        raise ValueError("commit_manifest.json does not match commit.code_hash")
    return doc, manifest, entry


def build_bound_params(paths: dict[str, Path], commit_doc: dict, commit_entry: dict, commit_sha: str) -> dict:
    hybrid = _load(paths["hybrid"])
    base = paths["hybrid"].parent

    def voxel(key):
        return voxel_hashes_of_file(base / hybrid["files"][key]["path"])[0]

    v, slices, grid = voxel_hashes_of_file(base / hybrid["files"]["hybrid_ct"]["path"])
    return {"tumor_draw_sha256": sha256_file(paths["draw"]),
            "certificate_sha256": sha256_file(paths["certificate"]),
            "job_record_sha256": sha256_file(paths["job"]),
            "hybrid": {"voxel_sha256": v, "slice_sha256s": slices, "grid": grid},
            "lesion_mask_voxel_sha256": voxel("lesion_mask"),
            "host_voxel_sha256": voxel("host_ct"),
            "insertion": hybrid["insertion"],
            "commit_receipt": {"ledger_index": commit_entry["index"], "sha256": commit_sha, "receipt": commit_doc}}


def fill(commit_receipt: Path, paths: dict, witnesses: list[Path], ledger_path: Path, keys_dir: Path) -> int:
    commit_receipt = Path(commit_receipt).resolve()
    run = start_run(LETTER_DIR, "fill", tool="G_provenance:fill")
    report = {"checks": [], "stub_exemptions": []}

    def check(name: str, ok: bool, detail: str = "") -> bool:
        report["checks"].append({"name": name, "ok": ok, "detail": detail})
        return ok

    def finish(code: int, msg: str) -> int:
        (run.path / "fill_report.json").write_text(json.dumps(report, indent=2) + "\n")
        run.finish(msg)
        print(msg)
        return code

    commit_doc, manifest, centry = _commit_state(commit_receipt, ledger_path)
    inputs = {"job": ("quantum_job_record", paths["job"]), "certificate": ("certificate", paths["certificate"]),
              "draw": ("tumor_draw", paths["draw"]), "hybrid": ("hybrid_volume", paths["hybrid"])}
    docs = {}
    bad = []
    for name, (_, p) in inputs.items():
        bad += _check_file(p)
        docs[name] = _load(p)
    for w in witnesses:
        bad += _check_file(w)
    if bad:
        check("input_contracts", False, "; ".join(bad))
        return finish(1, "input validation failed:\n  " + "\n  ".join(bad))
    check("input_contracts", True)
    if docs["certificate"]["status"] != "pass":
        return finish(0, "certificate failed, nothing to sign")

    c = commit_doc["commit"]
    sources = {**{k: docs[k] for k in docs}, **{f"witness:{w.name}": _load(w) for w in witnesses}}
    hashes = manifest["code_hashes"]
    for name, d in sources.items():
        if d.get("stub"):
            report["stub_exemptions"].append({"input": name, "note": STUB_ORDER_NOTE})
            continue
        check(f"order:{name}", d["created_utc"] >= c["committed_utc"],
              f"created {d['created_utc']} vs committed {c['committed_utc']}")
        pb = d["produced_by"]
        check(f"code_hash:{name}", hashes.get(pb["letter"]) == pb["code_hash"],
              f"letter {pb['letter']}: producer code hash is not the committed one")
    check("rulebook", docs["draw"].get("rulebook_hash") == c["rulebook_hash"],
          "tumor_draw.rulebook_hash vs commit.rulebook_hash")
    check("commit_before", centry["index"] < len(ledgermod.read(ledger_path)), "commit entry precedes this entry")

    if not all(x["ok"] for x in report["checks"]):
        fails = [f"{x['name']}: {x['detail']}" for x in report["checks"] if not x["ok"]]
        return finish(1, "FAIL " + "; ".join(fails) + " (no signature)")

    key = keymod.load_signer(keys_dir)
    bound = build_bound_params(paths, commit_doc, centry, sha256_file(commit_receipt))
    bound_file = run.path / "bound_params.json"
    bound_file.write_bytes(canonical_json(bound))
    f = run.path / "receipt.json"
    cert, job = docs["certificate"], docs["job"]
    fill_doc = {"job_ids": [job["job_id"]], "counts_sha256": sha256_bytes(canonical_json(job["counts"])),
                "chsh_S": cert["chsh_S"], "h_min_per_round": cert["h_min_per_round"],
                "witness_refs": [file_ref(w, f) for w in witnesses],
                "params_sha256": sha256_bytes(canonical_json(bound)), "seed_hex": cert["extracted_seed_hex"],
                "hybrid_volume_sha256": sha256_file(paths["hybrid"])}
    ups = [upstream_ref(c_, p, f) for c_, p in (inputs[k] for k in ("job", "certificate", "draw", "hybrid"))]
    ups += [upstream_ref("receipt", commit_receipt, f)] + [upstream_ref("witness_record", w, f) for w in witnesses]
    receipt = {**_envelope(run, ups), "commit": c, "fill": fill_doc, "signature": sign(key, c, fill_doc),
               "state": "ledgered"}
    sha = write_receipt(f, receipt)
    entry = ledgermod.append(sha, ledger_path)
    errs = _check_file(f) + [f"ledger: {e}" for e in ledgermod.verify_chain(ledger_path)]
    for k, (cn, p) in inputs.items():
        run.add_input(p, cn)
    run.add_output(f, "receipt")
    run.add_output(bound_file, "bound_params")
    check("self_validate", not errs, "; ".join(errs))
    if errs:
        return finish(1, "FAIL self-validation:\n  " + "\n  ".join(errs))
    return finish(0, f"filled: ledger index {entry['index']}\n  receipt {f}")


def _stub(*parts: str) -> Path:
    return STUBS.joinpath(*parts)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("commit", "fill"):
        p = sub.add_parser(name)
        p.add_argument("--ledger", type=Path, default=ledgermod.LEDGER)
        p.add_argument("--keys", type=Path, default=keymod.KEYS_DIR)
    sub.choices["commit"].add_argument("--rulebook", type=Path, default=_stub("rulebook", "rulebook.json"))
    fp = sub.choices["fill"]
    fp.add_argument("--commit", type=Path, required=True)
    fp.add_argument("--job", type=Path, default=_stub("quantum_job_record", "quantum_job_record.json"))
    fp.add_argument("--certificate", type=Path, default=_stub("certificate", "certificate.json"))
    fp.add_argument("--witness", type=Path, action="append")
    fp.add_argument("--draw", type=Path, default=_stub("tumor_draw", "tumor_draw.json"))
    fp.add_argument("--hybrid", type=Path, default=_stub("hybrid_volume", "hybrid_volume.json"))
    a = ap.parse_args(argv)
    if a.cmd == "commit":
        return commit(a.rulebook, a.ledger, a.keys)
    paths = {k: getattr(a, k).resolve() for k in ("job", "certificate", "draw", "hybrid")}
    witnesses = [w.resolve() for w in (a.witness or [_stub("witness_record", "witness_record.json")])]
    return fill(a.commit, paths, witnesses, a.ledger, a.keys)


if __name__ == "__main__":
    sys.exit(main())
