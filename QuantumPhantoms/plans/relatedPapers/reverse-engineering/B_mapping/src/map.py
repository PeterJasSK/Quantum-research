"""B-1 / B-2 orchestrator: rulebook + CT context + certificate seed -> circuit -> job record -> TumorDraw."""
import argparse
import json
import os
import sys
from collections import Counter

from qiskit import qasm3

from B_mapping.src import decode, drift, joint
from B_mapping.src.compiler import compile_rulebook, statevector_joint
from B_mapping.src.rulebook import RULEBOOK_PATH, PRIOR_PATH, ancestral_sample, joint_table
from shared import CONTRACT_VERSION, RE_ROOT, STUBS
from shared.runrecord import start_run
from shared.seedhash import derive_seed, rng, sha256_file
from shared.simbackend import calibration_snapshot, circuit_hash, make_simulator, sim_label, transpile_heron
from shared.validate import validate_file

LETTER_DIR = RE_ROOT / "B_mapping"
DEFAULT_SITES = STUBS / "site_candidates" / "sites.json"
DEFAULT_CERT = STUBS / "certificate" / "certificate.json"


def _write_json(path, obj) -> dict:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    return {"path": path.name, "sha256": sha256_file(path)}


def _ref(run, path, contract) -> dict:
    return {"contract": contract, "path": os.path.relpath(path, run.path), "sha256": sha256_file(path)}


def _envelope(contract, run, upstream, mode=None) -> dict:
    env = {"contract": contract, "contract_version": CONTRACT_VERSION,
           "produced_by": {"letter": "B", "tool": run.tool, "run_id": run.path.name, "code_hash": run.code_hash},
           "created_utc": run.created.strftime("%Y-%m-%dT%H:%M:%SZ"), "stub": False, "upstream": upstream}
    if mode:
        env |= {"sim_label": sim_label(mode), "hardware": None}
    return env


def _check(path):
    _, errs = validate_file(path)
    if errs:
        raise ValueError(f"{path.name} violates its contract: {errs[:3]}")


def physical_map(c, tqc) -> dict:
    """node -> physical qubits (measure targets, match $n in the QASM); ancillas via initial layout."""
    phys = {}
    for inst in tqc.data:
        if inst.operation.name == "measure":
            phys[tqc.find_bit(inst.clbits[0]).index] = tqc.find_bit(inst.qubits[0]).index
    qm = {nm: [phys[q] for q in qs] for nm, qs in c.node_qubits.items()}
    if c.n_ancilla:
        fin = tqc.layout.final_index_layout(filter_ancillas=False)   # virtual -> physical after routing
        qm["ancilla"] = [fin[c.n_logical + i] for i in range(c.n_ancilla)]
    return qm


def run_variant(variant, mode, sites_path, cert_path, site_id, shots, k_sites, out_tag=None, level=1, multi_control=None):
    # b2 default = ancilla: an 8-control mcry transpiles to ~10^5 CZ, the Toffoli chain is linear in controls
    multi_control = multi_control or ("mcry" if variant == "b1" else "ancilla")
    cert = json.loads(cert_path.read_text())
    if cert["status"] != "pass" or not cert.get("extracted_seed_hex"):
        print(f"certificate status={cert['status']}: no draw (no retry, no fallback)", file=sys.stderr)
        raise SystemExit(2)
    seed = cert["extracted_seed_hex"]
    sites_doc = json.loads(sites_path.read_text())
    rb = json.loads(RULEBOOK_PATH.read_text())
    prior = json.loads(PRIOR_PATH.read_text())["prior"]
    by_id = {s["site_id"]: s for s in sites_doc["sites"]}
    if variant == "b1":
        if site_id not in by_id:
            raise SystemExit(f"site {site_id} not in {sites_path}: have {sorted(by_id)}")
        site = by_id[site_id]
        ctx = {"placement_class": site["context"]["placement_class"]}
        c = compile_rulebook(rb, ctx, multi_control=multi_control)
        exact = joint_table(rb, ctx)
        ctx_out = ctx
        subset = None
    else:
        subset = joint.pick_sites(sites_doc["sites"], k_sites, seed)
        c = joint.compile_joint(rb, subset, prior, multi_control=multi_control)
        exact = joint.joint_reference(rb, subset, prior)
        ctx_out = {"variant": "b2", "sites": ",".join(s["site_id"] for s in subset)}
        site = None

    # exact-circuit check before spending shots
    sv = statevector_joint(c)
    dev = max(abs(sv.get(k, 0) - exact.get(k, 0)) for k in set(exact) | set(sv))
    assert dev < 1e-9, f"circuit != classical joint: {dev:.2e}"

    run = start_run(LETTER_DIR, f"{variant}-{out_tag or mode}", sim_mode=mode, tool="B_mapping.src.map")
    sim_seed = derive_seed(seed, "B.sim") % (2 ** 31)
    tqc = transpile_heron(c.circuit, seed=sim_seed, optimization_level=level)
    res = make_simulator(mode, seed=sim_seed).run(tqc, shots=shots, memory=True).result()
    memory = res.get_memory()
    counts = dict(Counter(memory))

    # files
    rb_path = run.path / "rulebook.json"
    _write_json(rb_path, rb)
    qasm_text = qasm3.dumps(tqc)
    (run.path / "compiled_circuit.qasm").write_text(qasm_text)
    up_in = [_ref(run, sites_path, "site_candidates"), _ref(run, cert_path, "certificate"), _ref(run, rb_path, "rulebook")]
    ops = tqc.count_ops()
    cc = _envelope("compiled_circuit", run, up_in) | {
        "rulebook_hash": rb["rulebook_hash"], "context": ctx_out,
        "qasm3": {"path": "compiled_circuit.qasm", "sha256": sha256_file(run.path / "compiled_circuit.qasm")},
        "transpiled_for": "FakeMarrakesh", "qubit_map": physical_map(c, tqc),
        "gate_counts": {k: int(v) for k, v in ops.items()}, "depth": tqc.depth(),
        "two_qubit_count": int(ops.get("cz", 0)), "circuit_hash": circuit_hash(tqc)}
    _write_json(run.path / "compiled_circuit.json", cc)
    job = _envelope("quantum_job_record", run, [_ref(run, run.path / "compiled_circuit.json", "compiled_circuit")], mode) | {
        "job_id": f"sim-b-{variant}-{mode}-{sim_seed}",
        "sim_mode": mode, "fake_backend": "FakeMarrakesh", "sim_seed": sim_seed, "shots": shots,
        "transpiled_hash": circuit_hash(tqc), "test_round_mask": None,
        "calibration_snapshot": calibration_snapshot(), "counts": counts}
    job_ref = _write_json(run.path / "quantum_job_record.json", job)

    combos = decode.shot_combos(c, memory)
    idx = decode.select_shot(combos, seed)
    body = decode.to_draw(c, combos[idx], idx, seed, site_id)
    draw = _envelope("tumor_draw", run, up_in + [_ref(run, run.path / "quantum_job_record.json", "quantum_job_record")]) | body | {
        "rulebook_hash": rb["rulebook_hash"], "job_record_ref": job_ref}
    _write_json(run.path / "tumor_draw.json", draw)

    # drift
    valid = Counter(x for x in combos if x is not None)
    n_inv = sum(1 for x in combos if x is None)
    g = rng(seed, "B.baseline")
    base = (ancestral_sample(rb, ctx, shots, g) if variant == "b1"
            else joint.ancestral_joint(rb, subset, prior, shots, g))
    gi = {"qubits_logical": c.n_logical, "qubits_ancilla": c.n_ancilla, "depth": tqc.depth(),
          "cz_count": int(ops.get("cz", 0)), "gate_counts": {k: int(v) for k, v in ops.items()},
          "sim_label": sim_label(mode), "bp_simulability": "pending D #9"}
    dr = drift.drift_entry(dict(valid), n_inv, shots, exact, base, c.nodes, c.states, gi)
    drift.write(run.path / "drift.json", {variant: {mode: dr}})

    for name, contract in [("rulebook.json", "rulebook"), ("compiled_circuit.json", "compiled_circuit"),
                           ("quantum_job_record.json", "quantum_job_record"), ("tumor_draw.json", "tumor_draw")]:
        _check(run.path / name)
        run.add_output(name, contract)
    run.finish(f"{variant} {mode}: joint TVD {dr['joint_tvd']:.4f} vs ancestral baseline "
               f"{dr['baseline_ancestral_tvd']:.4f}; invalid shots {dr['invalid_shot_fraction']:.3%}")
    return run, draw, dr


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--variant", choices=("b1", "b2"), required=True)
    ap.add_argument("--mode", choices=("ideal", "heron"), required=True)
    ap.add_argument("--site", default="S001")
    ap.add_argument("--sites", default=str(DEFAULT_SITES))
    ap.add_argument("--certificate", default=str(DEFAULT_CERT))
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--multi-control", choices=("mcry", "ancilla"))
    ap.add_argument("--k-sites", type=int, default=8, choices=(4, 8, 16))
    a = ap.parse_args()
    run, draw, dr = run_variant(a.variant, a.mode, __import__("pathlib").Path(a.sites).resolve(),
                                __import__("pathlib").Path(a.certificate).resolve(), a.site, a.shots, a.k_sites, multi_control=a.multi_control)
    print(run.path.relative_to(RE_ROOT))
    print(f"[{sim_label(a.mode)}] draw {draw['draw_id']} site={draw['site_id']} {draw['type']} "
          f"{draw['size_mm']} mm {draw['margin']}; joint TVD {dr['joint_tvd']:.4f} "
          f"(ancestral baseline {dr['baseline_ancestral_tvd']:.4f}); invalid {dr['invalid_shot_fraction']:.3%}")


if __name__ == "__main__":
    main()
