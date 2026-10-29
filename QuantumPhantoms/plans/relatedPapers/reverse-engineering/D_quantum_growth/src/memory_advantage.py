"""D-5: cell-cycle division timer simulated by a 1-qubit-memory quantum model, as a dynamic circuit (target #6).

    python -m D_quantum_growth.src.memory_advantage --mode ideal|heron

Per step: U on (memory, output) -> measure output mid-circuit -> reset output; L steps in one circuit; three
tomography variants (final memory in Z / X / Y) in one Aer job. Compared with the exact process (per-symbol KL)
and with the best 1-bit classical model. Claim level L1' (simulated), never L2.
"""
from __future__ import annotations

import argparse
from collections import Counter

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile

from D_quantum_growth.src import causal_states as C, heavyhex, io_contracts as io, witness as W
from shared.seedhash import canonical_json, derive_seed, rng, sha256_bytes, sha256_file
from shared.simbackend import (REFERENCE_FAKE, calibration_snapshot, circuit_hash, fake_backend,
                               make_simulator, sim_label)

L = 10
SHOTS = 40000
TOOL = "D_quantum_growth.src.memory_advantage"
VARIANTS = ("Z", "X", "Y")          # counts key prefix: 00, 01, 10


def build(model: dict, basis: str, steps: int = L) -> QuantumCircuit:
    s0 = model["sigma"][0]
    U = C.kraus_unitary(model["A0"], model["A1"])
    q = QuantumRegister(2, "q")
    c = ClassicalRegister(steps + 1, "c")
    qc = QuantumCircuit(q, c, name=f"d5_{basis}")
    m, o = q
    qc.ry(2 * np.arctan2(s0[1].real, s0[0].real), m)        # sigma_0 is real (beta0 Z0 + beta1 Z1)
    for t in range(steps):
        qc.unitary(U, [m, o], label="U")
        qc.measure(o, c[t])
        qc.reset(o)
    if basis == "X":
        qc.h(m)
    elif basis == "Y":
        qc.sdg(m)
        qc.h(m)
    qc.measure(m, c[steps])
    return qc


def rho_after(model: dict, steps: int) -> np.ndarray:
    """Exact unconditional memory state after `steps` steps from sigma_0."""
    s = model["sigma"][0]
    rho = np.outer(s, s.conj())
    for _ in range(steps):
        rho = model["A0"] @ rho @ model["A0"].conj().T + model["A1"] @ rho @ model["A1"].conj().T
    return rho


def rho_from_bits(tomo: dict[str, np.ndarray]) -> np.ndarray:
    """Linear inversion from the Z/X/Y memory bits (1 = eigenvalue -1), then nearest physical state."""
    r = {b: float(np.mean(1 - 2 * tomo[b].astype(float))) for b in "XYZ"}
    rho = 0.5 * (np.eye(2) + r["X"] * W.PAULI["X"] + r["Y"] * W.PAULI["Y"] + r["Z"] * W.PAULI["Z"])
    return W.nearest_physical(rho)


def run(run_, seed_hex: str, mode: str, shots: int = SHOTS, steps: int = L) -> dict:
    p = C.CELLCYCLE
    N, G, V = p["N"], p["Gamma"], p["V"]
    model = C.wu_model(G, V, N)
    cc = C.classical_complexity(G, V, N)
    cq_theory, dq = C.wu_cq(model, cc["pi"])
    seed = derive_seed(seed_hex, "D5-sim") % 2 ** 31
    circs = [build(model, b, steps) for b in VARIANTS]
    lay = heavyhex.path(2)
    t = [transpile(c, backend=fake_backend(), initial_layout=lay, optimization_level=1, seed_transpiler=seed)
         for c in circs]
    res = make_simulator(mode).run(t, shots=shots, seed_simulator=seed, memory=True).result()
    bits = [np.array([[int(ch) for ch in s[::-1]] for s in res.get_memory(i)], np.uint8) for i in range(3)]
    hashes = [circuit_hash(x) for x in t]
    thash = sha256_bytes(canonical_json(hashes))

    # word statistics: Z-variant only. The three circuits share one simulator seed and identical dynamics up to
    # the final basis change, so their word samples are copies of each other, not independent draws.
    words = bits[0][:, :steps]
    idx = words @ (1 << np.arange(steps - 1, -1, -1))
    n_samp = len(idx)
    p_sim = np.bincount(idx, minlength=2 ** steps) / n_samp
    p_exact = C.exact_words(cc["h"], steps, start=0)
    d_q = C.kl_bits(p_sim, p_exact) / steps
    floor = (2 ** steps - 1) / (2 * n_samp * np.log(2)) / steps       # expected sampling bias of the KL estimate
    base = C.best_classical_fixed_memory(p_exact, steps, 2, seed_hex)
    q_ex = C.hmm_words(base["T"], steps)
    d_c = C.kl_bits(q_ex, p_exact) / steps                       # exact (model distribution is known)
    cs = rng(seed_hex, "D5-classical-samples").choice(2 ** steps, size=n_samp, p=q_ex / q_ex.sum())
    d_c_sampled = C.kl_bits(np.bincount(cs, minlength=2 ** steps) / n_samp, p_exact) / steps  # same sampling floor

    # memory tomography -> C_q(measured)
    tomo = {b: bits[i][:, steps] for i, b in enumerate(VARIANTS)}
    rho_m = rho_from_bits(tomo)
    rho_ex = rho_after(model, steps)
    cq_meas = W.vn_entropy(rho_m)
    cq_exact_L = W.vn_entropy(rho_ex)
    se = W.boot_se(np.stack([tomo["Z"][: shots], tomo["X"][: shots], tomo["Y"][: shots]], 1),
                   lambda s: W.vn_entropy(rho_from_bits({"Z": s[:, 0], "X": s[:, 1], "Y": s[:, 2]})),
                   seed_hex, "D-bootstrap-D5", 300)
    fid = float(np.real(np.trace(_sqrtm(_sqrtm(rho_ex) @ rho_m @ _sqrtm(rho_ex)))) ** 2)

    passed = bool(cq_meas < cc["C_mu"] and d_q < 1e-2 and d_q < d_c_sampled)

    # job record: one logical job = 3 variant circuits; counts merged under a 2-bit variant prefix (CCR-D1)
    merged = {}
    for i in range(3):
        for k, v in Counter("".join(map(str, r[::-1])) for r in bits[i]).items():
            merged[f"{i:02b} {k}"] = v
    job_id = io.job_id(seed_hex, "qmachine", mode, shots)
    cf = run_.add_job(job_id, thash, shots * 3, merged)
    jrec = io.envelope("quantum_job_record", run_, mode) | {
        "job_id": job_id, "sim_mode": mode, "fake_backend": REFERENCE_FAKE, "sim_seed": seed,
        "shots": shots * 3, "transpiled_hash": thash, "counts_file": {"path": cf.name, "sha256": sha256_file(cf)},
        "test_round_mask": None, "calibration_snapshot": calibration_snapshot()}
    jfile = run_.path / "quantum_job_record_qmachine.json"
    jref = io.write_contract(jfile, jrec)
    run_.add_output(jfile.name, "quantum_job_record")

    desc = (f"cell-cycle division timer, PMD renewal process (Wu et al. form): N={N}, Gamma={G}, V={V}; "
            f"{sim_label(mode)}. 1-qubit-memory quantum model run as a dynamic circuit, L={steps} steps; "
            f"d_KL(quantum)={d_q:.5f} bits/symbol (sampling floor ~{floor:.5f}), d_KL(best 1-bit classical)="
            f"{d_c:.5f} exact / {d_c_sampled:.5f} at the same sample count; C_q theory (stationary)={cq_theory:.4f}, C_q exact after L steps={cq_exact_L:.4f}; "
            f"D_mu={cc['D_mu']:.2f} bits, D_q={dq:.0f} qubit. Advantage needs strong correlations "
            f"(low-correlation processes compress classically too).")
    rec = io.envelope("memory_advantage_record", run_, mode, [{"contract": "quantum_job_record", **jref}]) | {
        "claim_level": "L1′", "process_description": desc, "C_mu_bits": cc["C_mu"], "C_q_bits": cq_theory,
        "C_q_measured": cq_meas, "n_qubits": 1, "passed": passed, "job_record_ref": jref}
    rfile = run_.path / "memory_advantage_record.json"
    io.write_contract(rfile, rec)
    run_.add_output(rfile.name, "memory_advantage_record")
    detail = {"sim_label": sim_label(mode), "process": {k: p[k] for k in ("N", "Gamma", "V", "source")}, "L": steps,
              "shots_per_variant": shots, "n_word_samples": n_samp, "d_kl_quantum_bits_per_symbol": d_q,
              "kl_sampling_floor": float(floor), "d_kl_classical_1bit_bits_per_symbol": d_c,
              "d_kl_classical_1bit_sampled": d_c_sampled,
              "d_kl_quantum_debiased": max(d_q - float(floor), 0.0),
              "C_mu": cc["C_mu"], "D_mu": cc["D_mu"], "C_q_theory": cq_theory, "D_q": dq,
              "C_q_measured": cq_meas, "C_q_measured_stderr": se, "C_q_exact_after_L": cq_exact_L,
              "memory_state_fidelity": fid, "wu_model_check": C.wu_check(model, G, V, N), "passed": passed,
              "classical_T": base["T"].tolist(), "circuit_hashes": hashes}
    io.write_sidecar(run_.path / "memory_advantage_detail.json", detail)
    return {"detail": detail, "rec_file": rfile, "p_sim": p_sim, "p_exact": p_exact, "passed": passed, "circuits": t,
            "logical": circs}


def _sqrtm(a: np.ndarray) -> np.ndarray:
    w, v = np.linalg.eigh((a + a.conj().T) / 2)
    return (v * np.sqrt(np.clip(w, 0, None))) @ v.conj().T


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=("ideal", "heron"), required=True)
    ap.add_argument("--shots", type=int, default=SHOTS)
    io.add_input_args(ap)
    a = ap.parse_args()
    run_, paths, docs, seed = io.begin(a.mode, f"qmachine-{a.mode}", TOOL, io.overrides_of(a))
    if seed is None:
        return 2
    r = run(run_, seed, a.mode, a.shots)
    d = r["detail"]
    note = (f"{sim_label(a.mode)}; d_KL q={d['d_kl_quantum_bits_per_symbol']:.5f} vs 1-bit classical "
            f"{d['d_kl_classical_1bit_bits_per_symbol']:.5f} exact/{d['d_kl_classical_1bit_sampled']:.5f} sampled; C_q meas={d['C_q_measured']:.4f}"
            f"+-{d['C_q_measured_stderr']:.4f} (theory {d['C_q_theory']:.4f}) < C_mu={d['C_mu']:.4f}; passed={d['passed']}")
    run_.finish(note)
    print(run_.path, "\n ", note, f"\n  fidelity(mem)={d['memory_state_fidelity']:.4f}  KL floor~{d['kl_sampling_floor']:.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
