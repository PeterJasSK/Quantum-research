"""Regenerate every stub fixture in shared/stubs/ (byte-identical on every run).

    python -m shared.stubs.make_stubs

One consistent synthetic "tumor story", no patient data: a geometric chest phantom → masks →
three sites (one per placement class) → 2-node rulebook → compiled circuit → ideal-Aer job →
pass certificate → draw at S001 → D records + seed shape → growth baseline/follow-up →
lesion library + fingerprint → hybrid volume with an 8 mm sphere at S001 → signed receipt →
2-entry ledger → validation report. All numbers that a paper would provide are PLACEHOLDERS.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, qasm3
from scipy.ndimage import distance_transform_edt

from shared import CONTRACT_VERSION, SHARED, STUBS
from shared.runrecord import start_run
from shared.seedhash import canonical_json, code_hash, derive_seed, hash_json, sha256_bytes, sha256_file
from shared.simbackend import (REFERENCE_FAKE, calibration_snapshot, circuit_hash, run_counts, sim_label,
                               transpile_heron)
from shared.volumes import save_npz, write_volume

CREATED = "2026-10-28T00:00:00Z"
CREATED_DT = datetime(2026, 10, 28, tzinfo=timezone.utc)
RUN_ID = "20261028-000000-stub"
TOOL = "shared.stubs.make_stubs"
HOST = "stub-phantom-001"
SIM_SEED = 7
SHOTS = 1000
JOB_ID = "sim-stub-0001"
CERT_SEED = hashlib.sha256(b"qp-re-stub-certificate").hexdigest()
STUB_SOURCE = "STUB placeholder: not a published statistic"

SIZE_XYZ = (160, 128, 80)
SPACING_XYZ = (2.0, 2.0, 2.5)
ORIGIN_LPS = tuple(-(n * s) / 2 + s / 2 for n, s in zip(SIZE_XYZ, SPACING_XYZ))
SITES_MM = {  # (x, y, z) LPS mm, expected placement class
    "S001": ((-75.0, 30.0, 10.0), "free"),
    "S002": ((-50.0, 16.0, -20.0), "juxtavascular"),
    "S003": ((107.0, 0.0, 0.0), "juxtapleural"),
}

CODE_HASH = ""  # set in main(): tree hash of shared/


# ----------------------------------------------------------------------------- helpers
def write_json(path: Path, obj) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    return path


def fref(target: Path, frm: Path) -> dict:
    return {"path": target.relative_to(frm.parent, walk_up=True).as_posix(), "sha256": sha256_file(target)}


def upref(contract: str, target: Path, frm: Path) -> dict:
    return {"contract": contract, **fref(target, frm)}


def envelope(contract: str, upstream: list | None = None, quantum: bool = False) -> dict:
    env = {
        "contract": contract,
        "contract_version": CONTRACT_VERSION,
        "produced_by": {"letter": "stub", "tool": TOOL, "run_id": RUN_ID, "code_hash": CODE_HASH},
        "created_utc": CREATED,
        "stub": True,
        "upstream": upstream or [],
    }
    if quantum:
        env.update({"sim_label": sim_label("ideal"), "hardware": None})
    return env


def ry_angle(p1: float) -> float:
    return 2 * math.asin(math.sqrt(p1))


# ----------------------------------------------------------------------------- phantom
def phantom():
    nx, ny, nz = SIZE_XYZ
    sx, sy, sz = SPACING_XYZ
    ox, oy, oz = ORIGIN_LPS
    z, y, x = np.ogrid[:nz, :ny, :nx]
    X, Y, Z = ox + x * sx, oy + y * sy, oz + z * sz
    body = ((X / 150) ** 2 + (Y / 110) ** 2 <= 1) & (Z == Z)
    right = ((X + 65) / 50) ** 2 + (Y / 70) ** 2 + (Z / 90) ** 2 <= 1
    left = ((X - 65) / 45) ** 2 + (Y / 70) ** 2 + (Z / 90) ** 2 <= 1
    lungs = np.zeros((nz, ny, nx), np.uint8)
    lungs[right] = 1
    lungs[left] = 2
    vessels = np.zeros_like(lungs, dtype=bool)
    for cx, cy, r in ((-50, 10, 4.0), (-85, -25, 2.5), (50, 10, 4.0), (85, -25, 2.5)):
        vessels |= ((X - cx) ** 2 + (Y - cy) ** 2 <= r * r) & (Z == Z)
    vessels &= lungs > 0
    airway = body & ((X ** 2 + (Y + 20) ** 2) <= 64) & (Z > 20)
    lobes = np.zeros_like(lungs)
    zz = np.broadcast_to(Z, lungs.shape)
    yy = np.broadcast_to(Y, lungs.shape)
    lobes[right & (zz > 25)] = 3                                             # RUL
    lobes[right & (zz <= 25) & (zz > -35) & (yy < 0)] = 4                    # RML
    lobes[right & (lobes == 0)] = 5                                          # RLL
    lobes[left & (zz > 0)] = 1                                               # LUL
    lobes[left & (zz <= 0)] = 2                                              # LLL
    ct = np.full(lungs.shape, -1000, np.int16)
    ct[np.broadcast_to(body, ct.shape)] = 40
    ct[lungs > 0] = -850
    ct[vessels] = 40
    ct[airway] = -1000
    return {"host_ct": ct, "lungs": lungs, "lobes": lobes, "vessels": vessels.astype(np.uint8),
            "airway": airway.astype(np.uint8), "body": np.broadcast_to(body, ct.shape).astype(np.uint8)}


def mm_to_vox_zyx(p):
    return [int(round((p[i] - ORIGIN_LPS[i]) / SPACING_XYZ[i])) for i in (2, 1, 0)]


def vox_to_mm(v_zyx):
    return [ORIGIN_LPS[i] + v_zyx[2 - i] * SPACING_XYZ[i] for i in range(3)]


def sphere_mask(center_mm, radius_mm):
    nx, ny, nz = SIZE_XYZ
    z, y, x = np.ogrid[:nz, :ny, :nx]
    X, Y, Z = (ORIGIN_LPS[0] + x * SPACING_XYZ[0], ORIGIN_LPS[1] + y * SPACING_XYZ[1],
               ORIGIN_LPS[2] + z * SPACING_XYZ[2])
    return ((X - center_mm[0]) ** 2 + (Y - center_mm[1]) ** 2 + (Z - center_mm[2]) ** 2) <= radius_mm ** 2


def ball(n: int, r: float) -> np.ndarray:
    c = (n - 1) / 2
    z, y, x = np.ogrid[:n, :n, :n]
    return np.sqrt((x - c) ** 2 + (y - c) ** 2 + (z - c) ** 2)


# ----------------------------------------------------------------------------- stubs
def make_anatomy(vols) -> Path:
    d = STUBS / "anatomy_masks"
    files = {k: write_volume(d / f"{k}.nii.gz", v, SPACING_XYZ, ORIGIN_LPS) for k, v in vols.items()}
    m = d / "anatomy_masks.json"
    return write_json(m, {
        **envelope("anatomy_masks"),
        "host_scan_id": HOST,
        "grid": {"size_xyz": list(SIZE_XYZ), "spacing_mm_xyz": list(SPACING_XYZ), "origin_mm_lps": list(ORIGIN_LPS)},
        "files": {k: fref(files[k], m) for k in ("host_ct", "lungs", "lobes", "vessels", "airway", "body")},
        "label_tables": {"lungs": {"1": "right", "2": "left"},
                         "lobes": {"1": "LUL", "2": "LLL", "3": "RUL", "4": "RML", "5": "RLL"}},
    })


def make_sites(vols, anatomy: Path) -> Path:
    samp = SPACING_XYZ[::-1]
    d_pleura = distance_transform_edt(vols["lungs"] > 0, sampling=samp)
    d_vessel = distance_transform_edt(vols["vessels"] == 0, sampling=samp)
    d_airway = distance_transform_edt(vols["airway"] == 0, sampling=samp)
    lobe_names = {1: "LUL", 2: "LLL", 3: "RUL", 4: "RML", 5: "RLL"}
    sites = []
    for sid, (mm, expected) in SITES_MM.items():
        v = mm_to_vox_zyx(mm)
        dp, dv, da = (float(round(a[tuple(v)], 2)) for a in (d_pleura, d_vessel, d_airway))
        cls = "juxtapleural" if dp <= 5 else "juxtavascular" if dv <= 5 else "free"
        assert cls == expected, f"{sid}: got {cls}, expected {expected}"
        patch = vols["host_ct"][v[0] - 1:v[0] + 2, v[1] - 1:v[1] + 2, v[2] - 1:v[2] + 2].astype(float)
        sites.append({
            "site_id": sid, "center_vox_zyx": v, "center_mm_lps": vox_to_mm(v),
            "context": {"placement_class": cls, "lung": "right" if vols["lungs"][tuple(v)] == 1 else "left",
                        "lobe": lobe_names[int(vols["lobes"][tuple(v)])], "dist_pleura_mm": dp,
                        "dist_vessel_mm": dv, "dist_airway_mm": da,
                        "local_hu_mean": float(round(patch.mean(), 2)), "local_hu_std": float(round(patch.std(), 2))},
        })
    f = STUBS / "site_candidates" / "sites.json"
    return write_json(f, {**envelope("site_candidates", [upref("anatomy_masks", anatomy, f)]),
                          "host_scan_id": HOST, "anatomy_masks_ref": fref(anatomy, f), "sites": sites})


def make_rulebook() -> tuple[Path, dict]:
    doc = {
        **envelope("rulebook"),
        "rulebook_id": "stub-rulebook-2node",
        "nodes": [
            {"name": "solid", "states": ["no", "yes"], "parents": [], "context_keys": ["placement_class"],
             "cpt_by_context": {"free": [0.3, 0.7], "juxtavascular": [0.2, 0.8], "juxtapleural": [0.25, 0.75]},
             "sources": [STUB_SOURCE]},
            {"name": "spiculated", "states": ["no", "yes"], "parents": ["solid"], "context_keys": [],
             "cpt": [[0.9, 0.1], [0.7, 0.3]], "sources": [STUB_SOURCE]},
        ],
    }
    doc["rulebook_hash"] = hash_json(doc, exclude=["rulebook_hash", "created_utc", "produced_by"])
    return write_json(STUBS / "rulebook" / "rulebook.json", doc), doc


def stub_circuit(rulebook: dict, context: str) -> QuantumCircuit:
    solid, spic = rulebook["nodes"]
    q, c = QuantumRegister(2, "q"), ClassicalRegister(2, "c")
    qc = QuantumCircuit(q, c)
    qc.ry(ry_angle(solid["cpt_by_context"][context][1]), 0)
    qc.x(0)
    qc.cry(ry_angle(spic["cpt"][0][1]), 0, 1)
    qc.x(0)
    qc.cry(ry_angle(spic["cpt"][1][1]), 0, 1)
    qc.measure(q, c)
    return qc


def make_compiled(rulebook: dict, rb_path: Path) -> tuple[Path, QuantumCircuit]:
    qc = stub_circuit(rulebook, "free")
    tqc = transpile_heron(qc, seed=SIM_SEED)
    d = STUBS / "compiled_circuit"
    d.mkdir(parents=True, exist_ok=True)
    qasm = d / "circuit.qasm"
    qasm.write_text(qasm3.dumps(tqc))
    layout = tqc.layout.final_index_layout()
    ops = {k: int(v) for k, v in sorted(tqc.count_ops().items())}
    f = d / "compiled_circuit.json"
    write_json(f, {
        **envelope("compiled_circuit", [upref("rulebook", rb_path, f)]),
        "rulebook_hash": rulebook["rulebook_hash"], "context": {"placement_class": "free"},
        "qasm3": fref(qasm, f), "transpiled_for": REFERENCE_FAKE,
        "qubit_map": {"solid": [layout[0]], "spiculated": [layout[1]]},
        "gate_counts": ops, "depth": int(tqc.depth()), "two_qubit_count": ops.get("cz", 0),
        "circuit_hash": circuit_hash(tqc),
    })
    return f, qc


def make_job(qc: QuantumCircuit, compiled: Path) -> tuple[Path, dict, str]:
    counts, thash, job_id = run_counts(qc, "ideal", SHOTS, SIM_SEED, job_id=JOB_ID)
    counts = dict(sorted(counts.items()))
    f = STUBS / "quantum_job_record" / "quantum_job_record.json"
    write_json(f, {
        **envelope("quantum_job_record", [upref("compiled_circuit", compiled, f)], quantum=True),
        "job_id": job_id, "sim_mode": "ideal", "fake_backend": REFERENCE_FAKE, "sim_seed": SIM_SEED,
        "shots": SHOTS, "transpiled_hash": thash, "counts": counts, "test_round_mask": None,
        "calibration_snapshot": calibration_snapshot(),
    })
    return f, counts, thash


def make_certificate(job: Path) -> tuple[Path, dict]:
    S, n, n_test = 2.70, 10000, 1000
    h = 1 - math.log2(1 + math.sqrt(2 - S * S / 4))
    f = STUBS / "certificate" / "certificate.json"
    doc = {
        **envelope("certificate", [upref("quantum_job_record", job, f)], quantum=True),
        "chsh_S": S, "n_rounds": n, "n_test_rounds": n_test, "h_min_per_round": round(h, 6),
        "certified_bits": int(h * (n - n_test)),
        "extractor": {"kind": "toeplitz", "input_bits": n - n_test, "output_bits": 256},
        "curby_pulse_id": None, "job_record_ref": fref(job, f), "status": "pass",
        "extracted_seed_hex": CERT_SEED,
        "certification_status": "certification-ready, not certified (simulated)", "claim_level": "L0",
    }
    return write_json(f, doc), doc


def make_draw(sites: Path, rb: Path, rulebook: dict, job: Path, counts: dict, cert: Path) -> tuple[Path, dict]:
    top = max(counts, key=counts.get)              # bit order "c1 c0" = spiculated, solid
    f = STUBS / "tumor_draw" / "tumor_draw.json"
    doc = {
        **envelope("tumor_draw", [upref("site_candidates", sites, f), upref("rulebook", rb, f),
                                  upref("quantum_job_record", job, f), upref("certificate", cert, f)]),
        "draw_id": "D0001", "site_id": "S001", "size_mm": 8.0,
        "type": "solid" if top[-1] == "1" else "ground-glass",
        "margin": "spiculated" if top[0] == "1" else "smooth",
        "shape_seed_hex": format(derive_seed(CERT_SEED, "B.shape"), "016x"),
        "rulebook_hash": rulebook["rulebook_hash"], "job_record_ref": fref(job, f), "shot_index": 0,
    }
    return write_json(f, doc), doc


def make_quantum_d(job: Path, compiled: Path) -> dict:
    out = {}
    f = STUBS / "witness_record" / "witness_record.json"
    out["witness"] = write_json(f, {
        **envelope("witness_record", [upref("quantum_job_record", job, f)], quantum=True),
        "claim_level": "L1", "job_record_ref": fref(job, f),
        "observables": {"XX": {"value": 0.97, "stderr": 0.01}, "ZZ": {"value": 0.98, "stderr": 0.01}},
        "witness_expression": "<XX> + <ZZ> > 1 (GHZ-2 fidelity witness)", "threshold": 1.0, "passed": True,
        "bases": ["X", "Z"], "mi_network": None,
    })
    f = STUBS / "memory_advantage_record" / "memory_advantage_record.json"
    out["memory"] = write_json(f, {
        **envelope("memory_advantage_record", quantum=True), "claim_level": "L1′",
        "process_description": "STUB: 2-state renewal process (placeholder numbers)",
        "C_mu_bits": 1.0, "C_q_bits": 0.61, "C_q_measured": None, "n_qubits": 2, "passed": True,
        "job_record_ref": None,
    })
    compiled_hash = json.loads(compiled.read_text())["circuit_hash"]
    f = STUBS / "simulability_report" / "simulability_report.json"
    out["simulability"] = write_json(f, {
        **envelope("simulability_report", [upref("compiled_circuit", compiled, f)], quantum=True),
        "circuits": [{"circuit_hash": compiled_hash, "method": "belief-propagation", "bond_dim": 4,
                      "fidelity_vs_sim": 0.999, "runtime_s": 0.12}],
    })
    f = STUBS / "quantum_lineage" / "quantum_lineage.json"
    out["lineage"] = write_json(f, {
        **envelope("quantum_lineage", [upref("quantum_job_record", job, f)], quantum=True),
        "job_record_ref": fref(job, f), "claim_level": "L1",
        "generations": [{"g": 0, "measured_bits": "0", "fate": ["divide"], "chsh_round": False},
                        {"g": 1, "measured_bits": "01", "fate": ["divide", "rest"], "chsh_round": True},
                        {"g": 2, "measured_bits": "0110", "fate": ["rest", "divide", "divide", "rest"],
                         "chsh_round": False}],
    })
    d = STUBS / "seed_shape"
    occ = (ball(7, 3) <= 3).astype(np.uint8)
    npz = save_npz(d / "seed_shape.npz", occupancy=occ, spacing_mm_xyz=np.array([0.5, 0.5, 0.5]))
    f = d / "seed_shape.json"
    out["seed_shape"] = write_json(f, {
        **envelope("seed_shape", [upref("quantum_lineage", out["lineage"], f)], quantum=True),
        "lineage_ref": fref(out["lineage"], f), "claim_level": "L1", "npz": fref(npz, f), "n_cells": int(occ.sum()),
    })
    return out


def make_growth(sites_doc: dict, seed_shape: Path, cert: Path, draw: Path) -> Path:
    d = STUBS / "growth_trajectory"
    n, sp = 33, 0.5
    r = ball(n, 0)
    base = (r <= 3).astype(np.uint8)
    fu = np.zeros((n, n, n), np.uint8)
    fu[r <= 8] = 1
    fu[r <= 5] = 2
    fu[r <= 3] = 3
    s0 = save_npz(d / "step_0000.npz", state=base, spacing_mm_xyz=np.array([sp] * 3))
    s1 = save_npz(d / "step_0030.npz", state=fu, spacing_mm_xyz=np.array([sp] * 3))
    center = next(s for s in sites_doc["sites"] if s["site_id"] == "S001")["center_mm_lps"]
    f = d / "growth_trajectory.json"
    return write_json(f, {
        **envelope("growth_trajectory", [upref("seed_shape", seed_shape, f), upref("certificate", cert, f),
                                         upref("tumor_draw", draw, f)]),
        "site_id": "S001", "seed_hex": CERT_SEED, "seed_shape_ref": fref(seed_shape, f),
        "origin_mm_lps": [c - (n - 1) / 2 * sp for c in center], "spacing_mm_xyz": [sp] * 3,
        "state_labels": {"0": "host", "1": "proliferating", "2": "dormant", "3": "necrotic"},
        "snapshots": [{"step": 0, "day": 0.0, "role": "baseline", "npz": fref(s0, f)},
                      {"step": 30, "day": 90.0, "role": "follow-up", "npz": fref(s1, f)}],
    })


def make_render(vols, anatomy: Path, sites_doc: dict, draw: Path, growth: Path) -> dict:
    out = {}
    f = STUBS / "lesion_model_library" / "lesion_model_library.json"
    out["library"] = write_json(f, {
        **envelope("lesion_model_library"),
        "source": "STUB placeholder values: not fitted to LIDC (parameters only, no voxels)",
        "types": {
            "solid": {"shape_params": {"sphericity": 0.85}, "edge_profile": {"model": "erf", "params": {"width_mm": 0.8}},
                      "hu": {"mean": 30.0, "std": 25.0}, "n_fitted": 0},
            "part-solid": {"shape_params": {"sphericity": 0.75}, "edge_profile": {"model": "erf", "params": {"width_mm": 1.5}},
                           "hu": {"mean": -350.0, "std": 120.0}, "n_fitted": 0},
            "ground-glass": {"shape_params": {"sphericity": 0.7}, "edge_profile": {"model": "erf", "params": {"width_mm": 2.0}},
                             "hu": {"mean": -650.0, "std": 80.0}, "n_fitted": 0},
        },
    })
    d = STUBS / "scanner_fingerprint"
    sigma = np.where(vols["body"] > 0, 12.0, 0.0).astype(np.float32)
    smap = write_volume(d / "sigma_map.nii.gz", sigma, SPACING_XYZ, ORIGIN_LPS)
    freqs = [0.0, 0.2, 0.4, 0.6, 0.8]
    f = d / "scanner_fingerprint.json"
    out["fingerprint"] = write_json(f, {
        **envelope("scanner_fingerprint", [upref("anatomy_masks", anatomy, f)]),
        "host_scan_id": HOST,
        "mtf": {"freq_cyc_per_mm": freqs, "values": [round(math.exp(-(q / 0.45) ** 2), 4) for q in freqs]},
        "psf_sigma_mm_zyx": [0.9, 0.6, 0.6],
        "nps": {"freq_cyc_per_mm": freqs, "values": [0.0, 40.0, 55.0, 30.0, 8.0]},
        "sigma_map": fref(smap, f),
    })
    d = STUBS / "hybrid_volume"
    center = next(s for s in sites_doc["sites"] if s["site_id"] == "S001")["center_mm_lps"]
    mask = sphere_mask(center, 4.0)
    hybrid = vols["host_ct"].copy()
    hybrid[mask] = 30
    files = {
        "host_ct": write_volume(d / "host_ct.nii.gz", vols["host_ct"], SPACING_XYZ, ORIGIN_LPS),
        "hybrid_ct": write_volume(d / "hybrid_ct.nii.gz", hybrid, SPACING_XYZ, ORIGIN_LPS),
        "lesion_mask": write_volume(d / "lesion_mask.nii.gz", mask.astype(np.uint8), SPACING_XYZ, ORIGIN_LPS),
    }
    f = d / "hybrid_volume.json"
    out["hybrid"] = write_json(f, {
        **envelope("hybrid_volume", [upref("tumor_draw", draw, f), upref("growth_trajectory", growth, f),
                                     upref("scanner_fingerprint", out["fingerprint"], f),
                                     upref("anatomy_masks", anatomy, f)]),
        "host_scan_id": HOST, "site_id": "S001", "draw_id": "D0001",
        "files": {k: fref(v, f) for k, v in files.items()},
        "insertion": {"method": "STUB: hard sphere replacement (no PSF, no noise)", "params": {"radius_mm": 4.0, "hu": 30}},
        "seed_hex": CERT_SEED, "fingerprint_ref": fref(out["fingerprint"], f), "trajectory_ref": fref(growth, f),
        "snapshot_step": 30,
    })
    return out


def make_provenance(rulebook: dict, job: Path, counts: dict, cert_doc: dict, witness: Path, draw: Path,
                    hybrid: Path) -> tuple[Path, Path]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    f = STUBS / "receipt" / "receipt.json"
    commit = {"rulebook_hash": rulebook["rulebook_hash"], "code_hash": CODE_HASH, "committed_utc": CREATED}
    fill = {"job_ids": [JOB_ID], "counts_sha256": sha256_bytes(canonical_json(counts)),
            "chsh_S": cert_doc["chsh_S"], "h_min_per_round": cert_doc["h_min_per_round"],
            "witness_refs": [fref(witness, f)], "params_sha256": sha256_file(draw),
            "seed_hex": CERT_SEED, "hybrid_volume_sha256": sha256_file(hybrid)}
    key = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b"qp-re-stub-key").digest())
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    sig = key.sign(canonical_json({"commit": commit, "fill": fill}))
    write_json(f, {
        **envelope("receipt", [upref("quantum_job_record", job, f), upref("tumor_draw", draw, f),
                               upref("hybrid_volume", hybrid, f)]),
        "commit": commit, "fill": fill,
        "signature": {"alg": "Ed25519", "public_key_b64": base64.b64encode(pub).decode(),
                      "sig_b64": base64.b64encode(sig).decode(), "signed_over": "canonical_json({commit, fill})"},
        "state": "ledgered",
    })
    entries, prev = [], "0" * 64
    for i, (kind, rsha) in enumerate((("genesis", "0" * 64), ("receipt", sha256_file(f)))):
        e = {"contract": "ledger_entry", "contract_version": CONTRACT_VERSION, "index": i, "kind": kind,
             "prev_hash": prev, "receipt_sha256": rsha, "created_utc": CREATED}
        e["entry_hash"] = prev = sha256_bytes(canonical_json(e))
        entries.append(json.dumps(e, ensure_ascii=False))
    ledger = STUBS / "ledger_entry" / "ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("\n".join(entries) + "\n")
    return f, ledger


def make_validation(hybrid: Path, receipt: Path) -> Path:
    f = STUBS / "validation_report" / "validation_report.json"
    return write_json(f, {
        **envelope("validation_report", [upref("hybrid_volume", hybrid, f), upref("receipt", receipt, f)]),
        "hybrid_refs": [fref(hybrid, f)], "realism": {}, "radiomics": {}, "utility": {}, "drift": {},
        "certificate_stats": {}, "baseline": {}, "notes": "STUB: empty report shape only",
    })


def make_run_record(counts: dict, thash: str) -> Path:
    run = start_run(SHARED, "stub", seed_hex=CERT_SEED, sim_mode="ideal", tool=TOOL, created=CREATED_DT,
                    run_id=RUN_ID, include_git=False)
    counts_file = run.add_job(JOB_ID, thash, SHOTS, counts)
    src = run.finish("STUB run record (generated by make_stubs; git state omitted for byte-identical stubs)")
    d = STUBS / "run_record"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(counts_file, d / counts_file.name)
    shutil.copyfile(src, d / "run.json")
    return d / "run.json"


def main() -> None:
    global CODE_HASH
    CODE_HASH = code_hash([SHARED])
    for d in STUBS.iterdir():
        if d.is_dir() and d.name != "__pycache__":
            shutil.rmtree(d)
    vols = phantom()
    anatomy = make_anatomy(vols)
    sites = make_sites(vols, anatomy)
    sites_doc = json.loads(sites.read_text())
    rb, rulebook = make_rulebook()
    compiled, qc = make_compiled(rulebook, rb)
    job, counts, thash = make_job(qc, compiled)
    cert, cert_doc = make_certificate(job)
    draw, _ = make_draw(sites, rb, rulebook, job, counts, cert)
    dq = make_quantum_d(job, compiled)
    growth = make_growth(sites_doc, dq["seed_shape"], cert, draw)
    render = make_render(vols, anatomy, sites_doc, draw, growth)
    receipt, _ = make_provenance(rulebook, job, counts, cert_doc, dq["witness"], draw, render["hybrid"])
    make_validation(render["hybrid"], receipt)
    make_run_record(counts, thash)
    n = sum(1 for d in STUBS.iterdir() if d.is_dir() and d.name != "__pycache__")
    print(f"{n} stub contracts written to {STUBS}")


if __name__ == "__main__":
    main()
