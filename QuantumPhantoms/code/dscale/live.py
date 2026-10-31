"""D-SCALE live hardware run (Peter's runs): one proof-of-concept job per budget on an automatically picked IBM backend.

    python -m dscale.live --run research_runs/<run> --budget 40|100|120 [--max-qpu-seconds 50] [--shots 2000]
    python -m dscale.live --run ... --budget 40 --job <job id>          # resume: fetch a submitted job's result
    python -m dscale.live --run ... --budget 40 --fake FakeMarrakesh    # local test of the same path (Aer, no QPU)
    python -m dscale.live --run ... --budget 120 --dry-run              # pick + build + spend estimate, no submit

What it does, in order:
  1. backend: QiskitRuntimeService() (the pre-saved account; never a token) -> operational, non-simulator backends with
     >= budget qubits, least busy first; the first one on which the composite allocation fits after calibration
     pruning (readout > 0.06, sx >= 0.5, 2q > 0.02) is used.
  2. one composite job: ghz-spine (ghz2 + 16 DFE stabilizers), ch-qca (9 tomography settings + 1 echo at t_w = 2, plus
     one Z-snapshot circuit per tile with that tile's draw-driven initial set) and one pmd-bank machine (Z / X / Y),
     on disjoint buffered regions of the same chip and multiplexed into the same circuits (Q13: regions never share a
     gate; every family job passes dscale.lint first).
  3. spend guard: shots are cut until the estimate (shots x (circuit duration + 250 us) summed) is <= the cap
     (default 50 s, inside the 1-QPU-minute budget); below 300 shots it refuses. Submission is direct (SamplerV2,
     XX dynamical decoupling, measurement twirling). The job id is written before waiting, so `--job` can resume.
  4. results -> <run>/dscale/: claims, per-tile seed shapes (the snapshot shot picked by rng(geometry seed,
     "DS-qca-snapshot")), dscale_run.json labelled `hardware: <backend>, job <id>`; then imaging.build_tiles grows
     the tumours from those seeds and f3_web.build_web shows the panel.
Proof of concept: one job, n = 1, no repeats; the QCA witness is measured on the first tile's initial set and applies
to the run, not per tile. Never "certified" by itself; never an L2 / advantage claim.
"""
from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, qpy, transpile

from common.datamodel import DScaleRun
from dscale import allocate as A, families as F, lint as L, seedlift as SL, targets as T, witness_scale as WS
from dscale import run as R
from dscale.families import ch_qca as Q, ghz_spine as G, pmd_bank as P
from imaging.seedhash import rng

CAP_S = 50.0                 # QPU-seconds estimate cap (1-minute budget with margin)
SHOTS = 2000
MIN_SHOTS = 300
REP_DELAY_S = 250e-6
M_DFE = 16
QCA = {"t_max": 2, "t_w": 2, "alpha": math.pi / 2, "rule": "parity"}
REGS = {"ghz-spine": "s", "ch-qca": "c", "pmd-bank": "p"}


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------------------------- backend
def live_target(b, fake: bool) -> T.Target:
    props = None
    try:
        props = b.properties()
    except Exception:
        pass
    when = getattr(props, "last_update_date", None)
    cal = {"backend": b.name, "last_update_date": str(when) if when else None, "fake": fake,
           "qiskit_ibm_runtime_version": md.version("qiskit-ibm-runtime")}
    tg = T.from_backend(b.name, b, "", cal, {"live": not fake})
    lat = "square lattice" if max(dict(tg.graph.degree()).values()) >= 4 else "heavy-hex"
    tg.label = f"{b.name} ({'fake, ' if fake else ''}{b.num_qubits} q {lat})"
    tg.meta["lattice"] = lat
    return T.register(tg)


def pick_backend(budget: int, fake: str | None):
    if fake:
        from qiskit_ibm_runtime import fake_provider as fp
        b = getattr(fp, fake)()
        tg = live_target(b, True)
        return b, tg, A.composite(budget, tg.name), None
    from qiskit_ibm_runtime import QiskitRuntimeService
    service = QiskitRuntimeService()                     # pre-saved account
    cands = service.backends(operational=True, simulator=False, min_num_qubits=budget)
    ranked = []
    for b in cands:
        try:
            ranked.append((b.status().pending_jobs, b.name, b))
        except Exception:
            continue
    ranked.sort(key=lambda x: (x[0], x[1]))
    log("candidates (pending jobs): " + ", ".join(f"{n} ({p})" for p, n, _ in ranked))
    for pending, name, b in ranked:
        tg = live_target(b, False)
        try:
            alloc = A.composite(budget, tg.name)
        except A.Infeasible as e:
            log(f"  {name}: composite does not fit after pruning ({e}); next")
            continue
        log(f"picked {name}: {pending} pending jobs, {b.num_qubits} q, used {alloc['n_used']} after pruning "
            f"{len(alloc['pruned']['qubits'])} qubits")
        return b, tg, alloc, service
    raise SystemExit(f"no operational backend with >= {budget} qubits fits the {budget}-q composite")


# ---------------------------------------------------------------------------------------------- job
def components(alloc: dict, tg: T.Target, draws: list[dict], m_dfe: int = M_DFE) -> dict[str, list[QuantumCircuit]]:
    draw0 = draws[0]
    out: dict[str, list[QuantumCircuit]] = {}
    fams = {r["family"] for r in alloc["regions"].values()}
    if "ghz-spine" in fams:
        out["ghz-spine"] = G.build(alloc, {"m": m_dfe}, draw0)[:-1]          # ghz2 X, Z + DFE (no soma here)
    if "ch-qca" in fams:
        patch = Q.patch_of(alloc, tg)
        sp0 = Q.spec(patch, QCA, draw0)
        job = [Q.circuit(sp0, QCA["t_w"], (a, b)) for a in Q.BASES for b in Q.BASES]
        job.append(Q.circuit(sp0, QCA["t_w"], "Z", echo=True))
        for d in draws:
            c = Q.circuit(Q.spec(patch, QCA, d), QCA["t_w"], "Z")
            c.metadata["tile_id"] = d["tile_id"]
            c.name = f"seed_{d['tile_id']}"
            job.append(c)
        out["ch-qca"] = job
    pm = [r for k, r in sorted(alloc["regions"].items()) if r["family"] == "pmd-bank" and r["role"] == "active"]
    proc = P.process()
    if pm and len(pm[0]["qubits"]) >= proc["L"] + 1:
        out["pmd-bank"] = [c for c in P.build({"regions": {"pmd0": pm[0]}}, {}, draw0)]
    return out


def merge(comp: dict[str, list[QuantumCircuit]], n_phys: int) -> list[QuantumCircuit]:
    """K circuits; circuit k carries component k mod len of every family, each into its own classical register."""
    K = max(len(v) for v in comp.values())
    out = []
    for k in range(K):
        regs = {f: ClassicalRegister(v[0].num_clbits, REGS[f]) for f, v in comp.items()}
        qc = QuantumCircuit(QuantumRegister(n_phys, "q"), *regs.values(), name=f"dscale_live_{k:02d}")
        for f, v in comp.items():
            c = v[k % len(v)]
            qc.compose(c, qubits=c.metadata["layout"], clbits=list(regs[f]), inplace=True)
        qc.metadata = {"layout": list(range(n_phys)), "parts": {f: k % len(v) for f, v in comp.items()}}
        out.append(qc)
    return out


def qpu_seconds(isa: list[QuantumCircuit], b, shots: int) -> float:
    tot = 0.0
    for c in isa:
        try:
            d = float(c.estimate_duration(b.target, unit="s"))
        except Exception:
            d = c.depth() * 1e-7 + 3e-6
        tot += shots * (d + REP_DELAY_S)
    return tot


def submit(isa: list[QuantumCircuit], b, shots: int, fake: str | None):
    from qiskit_ibm_runtime import SamplerV2

    if fake:
        from qiskit_aer import AerSimulator
        mode = AerSimulator.from_backend(b, method="matrix_product_state")      # local test, not a QPU
        return SamplerV2(mode=mode).run(isa, shots=shots)
    sampler = SamplerV2(mode=b)
    sampler.options.dynamical_decoupling.enable = True
    sampler.options.dynamical_decoupling.sequence_type = "XX"
    sampler.options.twirling.enable_measure = True
    return sampler.run(isa, shots=shots)


def wait(job, poll_s: int = 30):
    t0 = time.time()
    last = None
    while True:
        try:
            st = str(job.status())
        except Exception as e:                             # transient API error: keep waiting
            st = f"status unavailable ({e.__class__.__name__})"
        if st != last or time.time() - t0 > poll_s:
            log(f"job {job.job_id()}: {st} (waited {int(time.time() - t0)} s)")
            last = st
        if any(k in st for k in ("DONE", "ERROR", "CANCELLED")):
            break
        time.sleep(poll_s if "QUEUED" in st or "RUNNING" in st else 5)
    return job.result()


def bits(pub, reg: str) -> np.ndarray:
    arr = getattr(pub.data, reg)
    return np.array([[int(ch) for ch in s[::-1]] for s in arr.get_bitstrings()], dtype=np.uint8)


# ---------------------------------------------------------------------------------------------- cohort roll
EXIT_CHSH = 7
CHSH_SHOTS = 2048


def roll_circuits(n_tiles: int, n_pairs: int, chsh_shots: int):
    """F1's circuits as one job: (name, circuit, shots). One shot per independent tile, one per sibling pair,
    the 4 CHSH settings for the job-level certificate."""
    from f1_quantum.circuit import build_chsh_circuits, build_sibling_pair_circuit, build_tumor_circuit
    from f1_quantum.lineage import DEFAULT_THETA_MUT
    from f1_quantum.rulebook import Rulebook, angles_from_rulebook

    rb = Rulebook()
    ang = angles_from_rulebook(rb)
    n_indep = n_tiles - 2 * n_pairs
    out = []
    if n_indep > 0:
        out.append(("tumor", build_tumor_circuit(ang), n_indep))
    if n_pairs > 0:
        out.append(("pairs", build_sibling_pair_circuit(ang, DEFAULT_THETA_MUT), n_pairs))
    for pair, qc in build_chsh_circuits().items():
        out.append((f"chsh_{pair[0]}_{pair[1]}", qc, chsh_shots))
    return out, rb, n_indep


def roll_cohort(b, tg, run_dir: Path, n_tiles: int, n_pairs: int, fake: str | None, roll_job: str | None,
                service) -> tuple[float, float]:
    """F1 on the picked QPU in ONE job; writes cohort_params.json + quantum_run.json (job id, hardware CHSH, raw
    bits). CHSH S <= 2: the draw is rejected and logged, no retry (honesty gate). Returns (S, QPU-s estimate)."""
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    from common.datamodel import QuantumRun
    from f1_quantum.certify import CHSH_SETTINGS, chsh_value
    from f1_quantum.decode import decode_memory
    from f1_quantum.lineage import decode_pairs

    circs, rb, n_indep = roll_circuits(n_tiles, n_pairs, CHSH_SHOTS)
    pm = generate_preset_pass_manager(optimization_level=3, backend=b, seed_transpiler=1)
    isa = [pm.run(qc) for _, qc, _ in circs]
    est = sum(sh * (c.depth() * 1e-7 + 3e-6 + REP_DELAY_S) for c, (_, _, sh) in zip(isa, circs))
    try:
        est = sum(sh * (float(c.estimate_duration(b.target, unit="s")) + REP_DELAY_S)
                  for c, (_, _, sh) in zip(isa, circs))
    except Exception:
        pass
    if roll_job:
        job = service.job(roll_job)
        log(f"cohort roll: resuming job {roll_job}")
    else:
        from qiskit_ibm_runtime import SamplerV2
        if fake:
            from qiskit_aer import AerSimulator
            sampler = SamplerV2(mode=AerSimulator.from_backend(b))
        else:
            sampler = SamplerV2(mode=b)
        job = sampler.run([(c, None, sh) for c, (_, _, sh) in zip(isa, circs)])
        (run_dir / "roll_job.json").write_text(json.dumps({"job_id": job.job_id(), "backend": b.name,
                                                           "circuits": [n for n, _, _ in circs]}, indent=1))
        log(f"cohort roll SUBMITTED job {job.job_id()} on {b.name} ({len(circs)} circuits, ~{est:.1f} QPU-s); "
            f"resume with --roll-job {job.job_id()}")
    res = wait(job) if not fake else job.result()
    shots_of = {n: res[i].data.c.get_bitstrings() for i, (n, _, _) in enumerate(circs)}
    counts = {n: {} for n in shots_of}
    for n, bs in shots_of.items():
        for x in bs:
            counts[n][x] = counts[n].get(x, 0) + 1
    by_pair = {tuple(n.split("_")[1:3]): counts[n] for n in counts if n.startswith("chsh_")}
    S = chsh_value(by_pair)
    raw, tiles = [], []
    if n_indep > 0:
        words = shots_of["tumor"][:n_indep]
        raw += words
        tiles += decode_memory(words, rb, generation=0, shot_start=0, lineage_prefix="tile", n_qubits=9)
    if n_pairs > 0:
        pw = shots_of["pairs"][:n_pairs]
        raw += pw
        pc = {}
        for x in pw:
            pc[x] = pc.get(x, 0) + 1
        tiles += decode_pairs(pc, rb, n_pairs=n_pairs, shot_start=n_indep, lineage_prefix="pair")
    label = b.name if not fake else f"{b.name} (local fake, not hardware)"
    qrun = QuantumRun(backend_name=label, job_id=job.job_id(), chsh_value=S, chsh_settings=dict(CHSH_SETTINGS),
                      raw_bits=raw, shot_indices=[t.shot_index for t in tiles])
    (run_dir / "quantum_run.json").write_text(json.dumps(qrun.to_dict(), indent=2))
    if S <= 2:
        (run_dir / "REJECTED_CHSH.txt").write_text(f"CHSH S = {S:.4f} <= 2 on {b.name}, job {job.job_id()}: "
                                                   f"draw rejected, no seed, no retry (honesty gate)\n")
        return S, est
    (run_dir / "cohort_params.json").write_text(json.dumps([t.to_dict() for t in tiles], indent=2))
    log(f"cohort rolled on {label}, job {job.job_id()}: CHSH S = {S:.3f} (> 2), {len(tiles)} tumours: "
        + ", ".join(f"{t.type[:5]} {t.size_mm:.0f}mm {t.lobe}" for t in tiles))
    return S, est


# ---------------------------------------------------------------------------------------------- analysis
def analyse_spine(comps, bl, alloc, tg, shots) -> dict:
    lay = comps[0].metadata["layout"]
    col = {q: k for k, q in enumerate(lay)}
    trees = G._trees(alloc)
    t0 = trees[0]
    anc = [col[c["ancilla"]] for t in trees for c in t["checks"]]
    keep = [(b[:, anc].sum(1) == 0) if anc else np.ones(len(b), bool) for b in bl]
    cols0 = [col[q] for q in t0["nodes"]]
    edges0 = [(col[a], col[b]) for a, b in t0["edges"]]
    g2 = WS.ghz2(bl[0][keep[0]], bl[1][keep[1]], cols0, edges0)
    vals, vt = [], []
    for c, b, kp in zip(comps[2:], bl[2:], keep[2:]):
        st = c.metadata["stabilizers"][t0["name"]]
        v, se = WS.stabilizer_value(b[kp], st, cols0)
        vals.append(v)
        used = [q for q, p in zip(t0["nodes"], st["paulis"]) if p != "I"]
        vt.append(WS.trex_lite(v, se, used, tg.p01, tg.p10)[0])
    dfe, dfe_t = WS.dfe_ghz(vals), WS.dfe_ghz(vt)
    al = WS.alive([dfe["F"]], shots, threshold=0.5, sigma_extra=dfe["sigma"])
    return {"N": len(t0["nodes"]), "depth": t0["depth"], "n_checks": len(t0["checks"]),
            "kept_fraction": float(np.mean([k.mean() for k in keep])), "m": len(vals),
            "F_dfe": dfe["F"], "F_sigma": al["sigma"], "gme": al["alive"], "gme_k3": al["alive_k3"],
            "F_dfe_trex": dfe_t["F"], "ghz2": g2["value"], "ghz2_sigma": g2["sigma"], "ghz2_X": g2["X"],
            "ghz2_ZZ": g2["ZZ"]}


def main() -> int:
    from dscale import budget as B

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", required=True)
    ap.add_argument("--budget", type=int, required=True, choices=F.BUDGETS)
    ap.add_argument("--max-qpu-seconds", type=float, default=CAP_S)
    ap.add_argument("--shots", type=int, default=SHOTS)
    ap.add_argument("--job", help="resume: fetch this submitted job instead of submitting")
    ap.add_argument("--fake", help="local test on a fake backend (e.g. FakeMarrakesh); never touches a QPU")
    ap.add_argument("--dry-run", action="store_true", help="pick the backend, build, print the spend; do not submit")
    ap.add_argument("--roll-cohort", action="store_true",
                    help="roll the tumour parameters on the same QPU first (F1 circuits + CHSH, one job)")
    ap.add_argument("--roll-job", help="resume an interrupted cohort-roll job")
    ap.add_argument("--tiles", type=int, default=12)
    ap.add_argument("--pairs", type=int, default=2)
    ap.add_argument("--m-dfe", type=int, default=M_DFE, help="DFE stabilizers on the spine (default 16)")
    a = ap.parse_args()
    if a.shots > B.SHOTS:
        raise SystemExit(f"refused: --shots {a.shots} > {B.SHOTS} (first-run cap)")
    run_dir = R.resolve_run(a.run)
    tr = R.tracked_files(run_dir)
    if tr:
        print(f"refused: {run_dir} holds git-tracked files (e.g. {tr[0]})")
        return R.EXIT_TRACKED
    out = run_dir / "dscale"
    live = out / "live"
    live.mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)

    # ---- plan (fresh) or reload (resume)
    if a.job:
        plan = json.loads((live / "plan.json").read_text())
        if plan["job_id"] != a.job:
            raise SystemExit(f"{live / 'plan.json'} belongs to job {plan['job_id']}, not {a.job}")
        from qiskit_ibm_runtime import QiskitRuntimeService
        service = QiskitRuntimeService()
        b = service.backend(plan["backend"])
        tg = live_target(b, False)
        alloc = plan["alloc"]
        with open(live / "components.qpy", "rb") as f:
            flat = qpy.load(f)
        comp, i = {}, 0
        for fam, n in plan["n_components"].items():
            comp[fam] = flat[i:i + n]
            i += n
        with open(live / "isa.qpy", "rb") as f:
            isa = qpy.load(f)
        shots = plan["shots"]
        params, qrun = R.load_f1(run_dir)
        run_key = qrun.job_id or run_dir.name
        draws = R.draws(params, qrun, run_key)
        job = service.job(a.job)
        log(f"resuming job {a.job} on {plan['backend']}")
    else:
        log(f"budget {a.budget}: picking a backend ({'local fake ' + a.fake if a.fake else 'live, auto'})")
        b, tg, alloc, service = pick_backend(a.budget, a.fake)
        roll_est = 0.0
        if a.roll_cohort and a.dry_run:
            circs, _, _ = roll_circuits(a.tiles, a.pairs, CHSH_SHOTS)
            roll_est = sum(sh for _, _, sh in circs) * (REP_DELAY_S + 5e-6)
            log(f"dry run: the cohort roll would be {len(circs)} circuits, ~{roll_est:.1f} QPU-s")
            draws = [F.default_draw() | {"tile_id": f"tile_{k}_0"} for k in range(a.tiles)]
            run_key = "dry-run"
        else:
            if a.roll_cohort:
                S, roll_est = roll_cohort(b, tg, run_dir, a.tiles, a.pairs, a.fake, a.roll_job, service)
                if S <= 2:
                    log(f"CHSH S = {S:.3f} <= 2: draw rejected (no seed, no retry); D-SCALE job not submitted")
                    return EXIT_CHSH
            params, qrun = R.load_f1(run_dir)
            run_key = qrun.job_id or run_dir.name
            draws = R.draws(params, qrun, run_key)
        a.max_qpu_seconds -= roll_est
        comp = components(alloc, tg, draws, a.m_dfe)
        for fam, job_c in comp.items():
            L.enforce(job_c, alloc["regions"], fam, tg.graph)
        log("lint ok: " + ", ".join(f"{f} {len(v)} circuits" for f, v in comp.items()))
        merged = merge(comp, tg.n_qubits)
        log(f"transpiling {len(merged)} composite circuits for {tg.name}")
        isa = [transpile(c, backend=b, initial_layout=list(range(tg.n_qubits)), optimization_level=1,
                         seed_transpiler=1) for c in merged]
        per_shot = qpu_seconds(isa, b, 1)
        shots = min(a.shots, int(a.max_qpu_seconds / per_shot))
        est = qpu_seconds(isa, b, shots)
        log(f"spend: {len(isa)} circuits x {shots} shots ~ {est:.1f} QPU-s (cap left {a.max_qpu_seconds:.0f} s); "
            f"2q gates per circuit up to {max(c.count_ops().get(tg.gate_2q, 0) for c in isa)}")
        if shots < MIN_SHOTS:
            raise SystemExit(f"refused: only {shots} shots fit under {a.max_qpu_seconds} s (min {MIN_SHOTS})")
        if a.dry_run:
            log("dry run: nothing submitted")
            return 0
        with open(live / "components.qpy", "wb") as f:
            qpy.dump([c for v in comp.values() for c in v], f)
        with open(live / "isa.qpy", "wb") as f:
            qpy.dump(isa, f)
        job = submit(isa, b, shots, a.fake)
        plan = {"job_id": job.job_id(), "backend": tg.name, "fake": a.fake, "budget": a.budget, "shots": shots,
                "qpu_seconds_estimate": est, "submitted_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "n_components": {f: len(v) for f, v in comp.items()}, "alloc": R._clean(alloc),
                "calibration": tg.calibration}
        (live / "plan.json").write_text(json.dumps(plan, indent=1, default=str))
        log(f"SUBMITTED job {plan['job_id']} on {tg.name} ({'local fake' if a.fake else 'QPU'}); "
            f"resume with --job {plan['job_id']}")

    result = wait(job) if not a.fake else job.result()
    label = (f"hardware: {plan['backend']}, job {plan['job_id']}" if not plan.get("fake")
             else f"local test: {plan['fake']} noise via SamplerV2 local mode (not hardware)")
    log(f"result in; analysing ({label})")
    try:
        usage = job.usage() if not a.fake else None
    except Exception:
        usage = None

    # ---- unpack per family (circuit k holds component k mod len)
    K = len(isa)
    fam_bits: dict[str, list[np.ndarray]] = {}
    for fam, v in comp.items():
        per = [[] for _ in v]
        for k in range(K):
            per[k % len(v)].append(bits(result[k], REGS[fam]))
        fam_bits[fam] = [np.concatenate(x) for x in per]
    np.savez_compressed(live / "bits.npz", **{f"{f}_{j}": x for f, v in fam_bits.items() for j, x in enumerate(v)})

    claims, detail = [], {"label": label, "plan": {k: plan[k] for k in plan if k != "alloc"}, "usage_s": usage}
    if "ghz-spine" in comp:
        sp = analyse_spine(comp["ghz-spine"], fam_bits["ghz-spine"], alloc, tg, shots)
        detail["ghz_spine"] = sp
        claims.append(G.claim(sp | {"sim_label": label}))
        log(f"ghz-spine N={sp['N']}: F_dfe {sp['F_dfe']:.3f} +- {sp['F_sigma']:.3f} (m={sp['m']}, TREX-lite "
            f"{sp['F_dfe_trex']:.3f}), GME {sp['gme']}; ghz2 {sp['ghz2']:.3f}; kept {sp['kept_fraction']:.2f}")
    seed_tiles, masks = {}, {}
    if "ch-qca" in comp:
        cq, bq = comp["ch-qca"], fam_bits["ch-qca"]
        sp0 = cq[0].metadata["qca"]
        an = Q.analyse(cq[:10], bq[:10], sp0, shots, draws[0]["seed_hex"])
        detail["ch_qca"] = {"sites": len(sp0["nodes"]), "rule": sp0["rule"], "alpha": sp0["alpha"], "t_w": QCA["t_w"],
                            "init": sp0["init"], "negativity_edges": an["negativity_edges"], "echo": an["echo"],
                            "random_band": an["random_band"], "witness_passed": an["witness_passed"]}
        cell = detail["ch_qca"] | {"sim_label": label}
        claims.append(Q.claim(cell))
        log(f"ch-qca {len(sp0['nodes'])} sites: witness {an['witness_passed']}; echo F "
            + ", ".join(f"t{e['t']}={e['F']:.3f}" for e in an["echo"]))
        patch = Q.patch_of(alloc, tg)
        lvl = Q.CLAIM if an["witness_passed"] else "L0"
        for c, bt in zip(cq[10:], bq[10:]):
            tid = c.metadata["tile_id"]
            d = next(x for x in draws if x["tile_id"] == tid)
            shot = int(rng(d["seed_hex"], "DS-qca-snapshot").integers(len(bt)))
            active = [q for q, v in zip(c.metadata["layout"], bt[shot]) if v]
            occ = SL.lift(patch, active)
            masks[tid] = occ
            seed_tiles[tid] = {"region": f"{tg.name}:{len(patch['nodes'])}", "sites": len(patch["nodes"]),
                               "init": c.metadata["qca"]["init"], "active": active, "seed_cells": int(occ.sum()),
                               "shot": shot, "claim_level": lvl, "witness_passed": an["witness_passed"],
                               "witness_scope": "run-level (measured on the first tile's initial set)",
                               "type": d["type"], "size_mm": d["size_mm"]}
            log(f"  seed {tid:10s} {d['type']:12s} {d['size_mm']:5.1f} mm: {len(active)}/{len(patch['nodes'])} "
                f"active -> {int(occ.sum())} vox")
    if "pmd-bank" in comp:
        cp, bp_ = comp["pmd-bank"], fam_bits["pmd-bank"]
        proc = cp[0].metadata["process"]
        st = P.staircase(proc, draws[0]["seed_hex"], n_starts=6)
        d_q, n = P.words_dkl([bp_[0]], proc, cp[0].metadata["outputs"])
        v = P.machine_verdict(d_q, n, proc, st)
        detail["pmd_bank"] = {"process": proc, "machines": [{"k": "pmd0", "path": cp[0].metadata["layout"]} | v],
                              "passed_all": v["passed"]}
        claims.append(P.claim(detail["pmd_bank"] | {"sim_label": label}))
        log(f"pmd-bank: d_KL(q) {d_q:.2e} (n={n}, floor {v['floor']:.2e}), gap/floor {v['gap_over_floor']:.2f}, "
            f"passed {v['passed']}")

    # ---- write the dscale/ stage record (same files as dscale.run, hardware-labelled)
    hashes = {}
    R.write_qasm(out / "circuits", "live", isa, hashes)
    if masks:
        R.save_npz_deterministic(out / "seed_shapes.npz", masks)
        R.seed_montage(masks, seed_tiles, out / "figures" / "seed_shapes.png", label)
    A.figure(alloc, out / "figures" / f"allocation_{a.budget}_{tg.name}.png")
    (out / "allocation.json").write_text(json.dumps(R._clean(alloc), indent=1, default=str))
    detail |= {"seed_tiles": seed_tiles, "circuits": hashes,
               "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (out / "scale_detail.json").write_text(json.dumps(R._clean(detail), indent=1, default=str))
    rec = DScaleRun(budget=a.budget, target=tg.name, mode="hardware" if not plan.get("fake") else "local-fake",
                    sim_label=label, recipe="composite", claims=claims,
                    goldilocks={"cells": [], "empty": None, "ref_kinds": [],
                                "note": "live proof of concept: the survive-vs-simulable map is a simulation product "
                                        "(python -m dscale.survival)"},
                    seed_shapes="seed_shapes.npz" if masks else "", param_grid_sha256="", shots=shots, repeats=1,
                    truncated=False, run_key=run_key)
    d = rec.to_dict() | {"target_label": tg.label, "job_id": plan["job_id"],
                         "honest_label": f"{label}; proof of concept (one job, n = 1, ~1 QPU-minute); the seed shape "
                                         f"is a quantum snapshot measured on the device; growth and image are "
                                         f"classical; no classical-hardness claim"}
    (out / "dscale_run.json").write_text(json.dumps(R._clean(d), indent=1, default=str))
    log("claims: " + "; ".join(f"{c['family']} {c['claim_level']} (passed {c['passed']})" for c in claims))
    log(f"wrote {out} (label: {label})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
