"""CHSH → certified bits → extracted seed: one simulated certificate run (targets #4 + #5).

    python -m C_certificate.src.certify --mode ideal|heron [--rounds N] [--test-frac q]
                                        [--pulse-index i] [--settings quantum|classical]

Writes C_certificate/runs/<ts>-chsh-<mode>[-classical]/ with run.json, counts_<job>.json,
quantum_job_record.json, certificate.json, accounting.json, rounds.npz, test_round_mask.json and,
on pass only, extracted.bin. Simulation only: the certificate is "certification-ready, not
certified (simulated)". S_low ≤ 2 or too little entropy ⇒ status fail, no seed, logged to
runs/rejections.jsonl; no retry, no other pulse, no fallback (epic decision 6).
"""
from __future__ import annotations

import argparse
import json
import math
import uuid
from pathlib import Path

import numpy as np

from C_certificate.src import beacon
from C_certificate.src.chsh import make_schedule, run_rounds
from C_certificate.src.entropy import (certified_bits, chsh_estimate, extractable_len, f_hmin,
                                       s_lower_bound)
from C_certificate.src.toeplitz import TOEPLITZ_LABEL, bits_to_hex, expand_seed_bits, toeplitz_extract
from shared import CONTRACT_VERSION, RE_ROOT
from shared.runrecord import start_run
from shared.seedhash import canonical_json, derive_seed, rng, sha256_bytes, sha256_file
from shared.simbackend import REFERENCE_FAKE, calibration_snapshot, sim_label
from shared.validate import validate_file

LETTER_DIR = RE_ROOT / "C_certificate"
CERT_STATUS = "certification-ready, not certified (simulated)"
S_SCHEMA_MAX = 2.8284  # certificate.schema.json caps chsh_S at 2.8285; a statistical Ŝ can exceed 2√2


def _write_json(path: Path, obj: dict) -> dict:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    return {"path": path.name, "sha256": sha256_file(path)}


def _envelope(contract: str, run, upstream: list[dict], mode: str) -> dict:
    return {
        "contract": contract,
        "contract_version": CONTRACT_VERSION,
        "produced_by": {"letter": "C", "tool": run.tool, "run_id": run.path.name, "code_hash": run.code_hash},
        "created_utc": run.created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stub": False,
        "upstream": upstream,
        "sim_label": sim_label(mode),
        "hardware": None,
    }


def _check(path: Path) -> None:
    _, errs = validate_file(path)
    if errs:
        raise ValueError(f"{path} violates its contract:\n  " + "\n  ".join(errs))


def certify(mode: str, n_rounds: int = 100_000, test_frac: float = 0.2, pulse_index: int = -1,
            classical: bool = False, eps_est: float = 1e-6, eps_ext: float = 1e-6, out_len: int = 256) -> Path:
    cache = beacon.load_cache()
    pulse = beacon.select_verified_pulse(cache, pulse_index)
    pulse_seed = beacon.pulse_seed_hex(pulse)

    schedule = make_schedule(n_rounds, test_frac, rng(pulse_seed, "C.test_mask"))
    base_seed = derive_seed(pulse_seed, f"C.aer.{mode}") % (2 ** 31)
    tag = f"chsh-{mode}" + ("-classical" if classical else "")
    run = start_run(LETTER_DIR, tag, sim_mode=mode, tool="C_certificate.src.certify")
    rr = run_rounds(mode, schedule, base_seed, classical=classical)

    x, y, a, b, test = schedule["x"], schedule["y"], rr["a"], rr["b"], schedule["test"]
    np.savez_compressed(run.path / "rounds.npz", x=x, y=y, a=a, b=b, test=test)
    mask_ref = _write_json(run.path / "test_round_mask.json",
                           {"n": n_rounds, "mask_hex": np.packbits(test).tobytes().hex()})

    # quantum job record: one logical job = the 4 setting circuits (see README, CCR-C1)
    job_id = f"sim-{uuid.uuid4()}"
    transpiled_hash = sha256_bytes(canonical_json(rr["circuit_hashes"]))
    run.add_job(job_id, transpiled_hash, n_rounds, rr["counts"])
    job = _envelope("quantum_job_record", run, [], mode) | {
        "job_id": job_id, "sim_mode": mode, "fake_backend": REFERENCE_FAKE, "sim_seed": base_seed,
        "shots": n_rounds, "transpiled_hash": transpiled_hash, "counts": rr["counts"],
        "test_round_mask": mask_ref, "calibration_snapshot": calibration_snapshot(),
    }
    job_ref = _write_json(run.path / "quantum_job_record.json", job)

    # accounting
    est = chsh_estimate(x, y, a, b, test)
    s_low, delta = s_lower_bound(est, eps_est)
    n_test = int(test.sum())
    n_gen = n_rounds - n_test
    h = f_hmin(s_low)
    cert_bits = certified_bits(n_gen, h)
    avail = extractable_len(cert_bits, eps_ext)
    fail_reason = None
    if s_low <= 2.0:
        fail_reason = f"S_low = {s_low:.4f} <= 2: no CHSH violation at confidence 1 - eps_est"
    elif avail < out_len:
        fail_reason = f"insufficient entropy: extractable {avail} < {out_len} bits"
    status = "fail" if fail_reason else "pass"

    seed_hex = None
    if status == "pass":
        gen = test == 0
        raw = np.stack([a[gen], b[gen]], axis=1).reshape(-1)  # a1 b1 a2 b2 … (2 bits per generation round)
        seed_bits = expand_seed_bits(beacon.pulse_output_bytes(pulse) + TOEPLITZ_LABEL, raw.size + out_len - 1)
        out = toeplitz_extract(raw, out_len, seed_bits)
        seed_hex = bits_to_hex(out)
        (run.path / "extracted.bin").write_bytes(bytes.fromhex(seed_hex))
        run.seed_hex = seed_hex

    accounting = {
        "sim_label": sim_label(mode), "settings": "classical" if classical else "quantum",
        "S_hat": est["S_hat"], "E_xy": est["E_xy"], "n_xy": est["n_xy"], "delta_xy": delta, "S_low": s_low,
        "eps_est": eps_est, "eps_ext": eps_ext, "n_rounds": n_rounds, "test_frac": test_frac, "n_test": n_test,
        "n_gen": n_gen, "h_min_per_round": h, "certified_bits": cert_bits, "extractable_bits": avail,
        "out_len": out_len, "status": status, "fail_reason": fail_reason,
        "pulse": {"source": cache["source"], "id": beacon.pulse_id(pulse),
                  "output_sha256": pulse_seed, "timeStamp": pulse["timeStamp"]},
        "aer_base_seed": base_seed, "circuit_hashes": rr["circuit_hashes"],
    }
    _write_json(run.path / "accounting.json", accounting)

    cert = _envelope("certificate", run, [{"contract": "quantum_job_record", **job_ref}], mode) | {
        "chsh_S": max(0.0, min(est["S_hat"], S_SCHEMA_MAX)),
        "n_rounds": n_rounds, "n_test_rounds": n_test, "h_min_per_round": h, "certified_bits": cert_bits,
        "extractor": {"kind": "toeplitz", "input_bits": 2 * n_gen, "output_bits": out_len if seed_hex else 0},
        "curby_pulse_id": beacon.pulse_id(pulse), "job_record_ref": job_ref,
        "status": status, "extracted_seed_hex": seed_hex,
        "certification_status": CERT_STATUS, "claim_level": "L0",
    }
    _write_json(run.path / "certificate.json", cert)

    for name in ("quantum_job_record.json", "certificate.json"):
        _check(run.path / name)
    run.add_output("quantum_job_record.json", "quantum_job_record")
    run.add_output("certificate.json", "certificate")
    note = f"{sim_label(mode)}; S_hat={est['S_hat']:.4f} S_low={s_low:.4f} h={h:.4f} bits={cert_bits} {status}"
    if fail_reason:
        note += f" ({fail_reason})"
        with open(LETTER_DIR / "runs" / "rejections.jsonl", "a") as f:
            f.write(json.dumps({"run_id": run.path.name, "created_utc": cert["created_utc"],
                                "mode": mode, "settings": accounting["settings"], "S_hat": est["S_hat"],
                                "S_low": s_low, "fail_reason": fail_reason}) + "\n")
    run.finish(note)
    print(f"{run.path.relative_to(RE_ROOT)}\n  {note}\n  pulse {beacon.pulse_id(pulse)}"
          + (f"\n  seed {seed_hex}" if seed_hex else "\n  rejected and logged (no retry, no fallback)"))
    return run.path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=("ideal", "heron"), required=True)
    ap.add_argument("--rounds", type=int, default=100_000)
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--pulse-index", type=int, default=-1, help="index into the cached pulse list")
    ap.add_argument("--settings", choices=("quantum", "classical"), default="quantum")
    ap.add_argument("--eps-est", type=float, default=1e-6)
    ap.add_argument("--eps-ext", type=float, default=1e-6)
    ap.add_argument("--out-len", type=int, default=256)
    args = ap.parse_args()
    if not (0.0 < args.test_frac < 1.0) or not math.isfinite(args.test_frac):
        ap.error("--test-frac must be in (0, 1)")
    certify(args.mode, args.rounds, args.test_frac, args.pulse_index, args.settings == "classical",
            args.eps_est, args.eps_ext, args.out_len)


if __name__ == "__main__":
    main()
