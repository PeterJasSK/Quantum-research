"""Provenance verifier (AC-8): recompute everything, trust nothing stored.

    python -m G_provenance.src.verify <series dir | receipt.json> [--ledger ledger.jsonl] [--trusted keys.json]

Checks: signature, trusted_key, params, voxels (+ tampered slices), geometry, ledger_chain,
ledger_entry, commit_first (and receipt_consistency for a series). Each prints OK or FAIL <where>.
Exit 0 = VERIFIED, 2 = TAMPER DETECTED.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from G_provenance.src import keys as keymod
from G_provenance.src import ledger as ledgermod
from G_provenance.src.dicom_export import read_series
from G_provenance.src.hashing import grid_of, slice_sha256s, voxel_sha256
from shared import RE_ROOT
from shared.runrecord import start_run
from shared.seedhash import canonical_json, sha256_bytes
from shared.validate import _verify_signature
from shared.volumes import read_volume

LETTER_DIR = RE_ROOT / "G_provenance"
CHECKS = ("signature", "trusted_key", "params", "voxels", "geometry", "ledger_chain", "ledger_entry", "commit_first")


def _load_target(target: Path) -> dict:
    """-> {receipt, bound, arr, meta, ledger_index, entry_hash, problems}; problems are pre-check failures."""
    target = Path(target)
    if target.is_dir():
        arr, meta, tags, _ = read_series(target)
        out = {"arr": arr, "meta": meta, "problems": []}
        for name in ("receipt_json", "bound_params_json", "ledger_index", "ledger_entry_hash"):
            if len({str(t[name]) for t in tags}) > 1:
                out["problems"].append(f"{name} differs between slices")
        out["receipt"] = json.loads(tags[0]["receipt_json"])
        out["bound"] = json.loads(tags[0]["bound_params_json"])
        out["ledger_index"], out["entry_hash"] = int(tags[0]["ledger_index"]), tags[0]["ledger_entry_hash"]
        return out
    receipt = json.loads(target.read_text())
    bound = json.loads((target.parent / "bound_params.json").read_text())
    ref = next(u for u in receipt["upstream"] if u["contract"] == "hybrid_volume")
    hyb_path = (target.parent / ref["path"]).resolve()
    hyb = json.loads(hyb_path.read_text())
    arr, meta = read_volume(hyb_path.parent / hyb["files"]["hybrid_ct"]["path"])
    return {"arr": arr, "meta": meta, "problems": [], "receipt": receipt, "bound": bound,
            "ledger_index": None, "entry_hash": None}


def verify(target: Path, ledger_path: Path = ledgermod.LEDGER, trusted: set[str] | None = None) -> dict:
    trusted = keymod.trusted_public_keys() if trusted is None else trusted
    t = _load_target(target)
    receipt, bound, entries = t["receipt"], t["bound"], ledgermod.read(ledger_path)
    results: dict[str, str | None] = {}  # name -> None (OK) | where

    def get(name, fn):
        try:
            results[name] = fn()
        except (KeyError, IndexError, TypeError, ValueError) as e:
            results[name] = f"malformed ({type(e).__name__}: {e})"

    def signature():
        errs = _verify_signature(receipt) if receipt.get("signature") else ["receipt has no signature"]
        return errs[0] if errs else None

    def trusted_key():
        return None if receipt["signature"]["public_key_b64"] in trusted else "signing key is not in the trusted list"

    def params():
        got = sha256_bytes(canonical_json(bound))
        return None if got == receipt["fill"]["params_sha256"] else "bound parameters differ from fill.params_sha256"

    def voxels():
        want = bound["hybrid"]
        if voxel_sha256(t["arr"], t["meta"]) == want["voxel_sha256"]:
            return None
        got, ref = slice_sha256s(t["arr"]), want["slice_sha256s"]
        if len(got) != len(ref):
            return f"slice count {len(got)} != {len(ref)}"
        bad = [z for z in range(len(got)) if got[z] != ref[z]]
        return f"slices {bad}" if bad else "grid/header differs, pixels equal"

    def geometry():
        return None if grid_of(t["meta"]) == bound["hybrid"]["grid"] else "grid differs from the bound grid"

    def chain():
        errs = ledgermod.verify_chain(ledger_path) if entries else ["ledger missing or empty"]
        return errs[0] if errs else None

    rsha = sha256_bytes(canonical_json(receipt))

    def entry():
        idx = t["ledger_index"]
        if idx is None:
            found = ledgermod.find_receipt(rsha, ledger_path)
            return None if found else "no ledger entry holds this receipt"
        if not 0 <= idx < len(entries):
            return f"ledger index {idx} not in ledger"
        e = entries[idx]
        if e["receipt_sha256"] != rsha:
            return f"ledger index {idx}: receipt_sha256 differs from the receipt"
        if e["entry_hash"] != t["entry_hash"]:
            return f"ledger index {idx}: entry_hash differs from the tag"
        return None

    def commit_first():
        cr = bound["commit_receipt"]
        idx = cr["ledger_index"]
        if not 0 <= idx < len(entries):
            return f"commit entry at ledger index {idx} is missing"
        csha = sha256_bytes(canonical_json(cr["receipt"]))
        if entries[idx]["receipt_sha256"] != csha or csha != cr["sha256"]:
            return f"ledger index {idx} is not the committed receipt"
        mine = t["ledger_index"]
        if mine is None:
            mine = (ledgermod.find_receipt(rsha, ledger_path) or {}).get("index")
        if mine is None or idx >= mine:
            return f"commit (index {idx}) does not precede the receipt (index {mine})"
        if cr["receipt"]["commit"] != receipt["commit"] or cr["receipt"]["fill"] is not None:
            return "committed receipt carries a different commit"
        if _verify_signature(cr["receipt"]) or cr["receipt"]["signature"]["public_key_b64"] not in trusted:
            return "committed receipt signature or key is not trusted"
        return None

    for name, fn in zip(CHECKS, (signature, trusted_key, params, voxels, geometry, chain, entry, commit_first)):
        get(name, fn)
    if t["problems"]:
        results["receipt_consistency"] = "; ".join(t["problems"])
    elif Path(target).is_dir():
        results["receipt_consistency"] = None
    checks = [{"name": n, "ok": w is None, "where": w} for n, w in results.items()]
    failed = [c["name"] for c in checks if not c["ok"]]
    return {"target": str(target), "checks": checks, "failed": failed,
            "verdict": "VERIFIED" if not failed else "TAMPER DETECTED: " + ", ".join(failed)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("target", type=Path)
    ap.add_argument("--ledger", type=Path, default=ledgermod.LEDGER)
    ap.add_argument("--trusted", type=Path, help="trusted_keys.json (default: G_provenance/runs/keys/)")
    a = ap.parse_args(argv)
    trusted = None
    if a.trusted:
        trusted = {e["public_key_b64"] for e in json.loads(a.trusted.read_text())}
    report = verify(a.target, a.ledger, trusted)
    for c in report["checks"]:
        print(f"{'OK  ' if c['ok'] else 'FAIL'} {c['name']}" + ("" if c["ok"] else f" {c['where']}"))
    print(report["verdict"])
    run = start_run(LETTER_DIR, "verify", tool="G_provenance:verify")
    (run.path / "verify_report.json").write_text(json.dumps(report, indent=2) + "\n")
    run.finish(report["verdict"])
    return 0 if not report["failed"] else 2


if __name__ == "__main__":
    sys.exit(main())
