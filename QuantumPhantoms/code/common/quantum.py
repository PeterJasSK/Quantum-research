"""The one way a circuit reaches a device.

    backend not set      dry run: the same circuits on the local fake backend (common.FAKE_BACKEND, Aer; not hardware)
    backend "auto"       real hardware: the least busy operational backend with >= 100 qubits
    backend "<name>"     real hardware, that backend            (pre-saved QiskitRuntimeService account; Peter only)

One backend per run: the first pick is written to <run>/backend.json and reused by every section and by a
continued run. Every submitted job id is written to <run>/jobs/<key>.json before waiting; when that file exists the
job is fetched instead of submitted again (so a stopped live run can be continued without paying twice).
Spend guard: shots are cut so the estimate stays under common.MAX_QPU_SECONDS for the run; below MIN_SHOTS it refuses.
"""
from __future__ import annotations

import importlib.metadata as md
import math
import time
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from qiskit import QuantumCircuit, transpile

from common import FAKE_BACKEND, MAX_QPU_SECONDS, MIN_SHOTS, lint as L, pauli_noise as PN, runio, targets as T
from common.runio import Ctx

REP_DELAY_S = 250e-6
WIDE = 16                     # logical qubits above which the local fake run needs MPS (or the Pauli model if Clifford)


class Refused(Exception):
    """This circuit cannot run here (do-not-build list, no layout, spend cap)."""


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------------------------- backend
@dataclass
class Session:
    backend: object
    target: T.Target
    service: object | None            # None on the fake backend
    live: bool

    def label(self, job_id: str = "") -> str:
        if self.live:
            return f"hardware: {self.target.name}, job {job_id}"
        return f"dry run: {FAKE_BACKEND} noise on a local simulator (not hardware)"


_SESSION: dict[str, Session] = {}


def _target(b, live: bool) -> T.Target:
    props = None
    try:
        props = b.properties()
    except Exception:
        pass
    cal = {"backend": b.name, "last_update_date": str(getattr(props, "last_update_date", None)), "fake": not live,
           "qiskit_ibm_runtime_version": md.version("qiskit-ibm-runtime")}
    tg = T.from_backend(b.name, b, "", cal, {"live": live})
    tg.meta["lattice"] = "square lattice" if max(dict(tg.graph.degree()).values()) >= 4 else "heavy-hex"
    tg.label = f"{b.name} ({'' if live else 'fake, '}{b.num_qubits} q {tg.meta['lattice']})"
    return T.register(tg)


def session(ctx: Ctx) -> Session:
    key = str(ctx.run_dir)
    if key in _SESSION:
        return _SESSION[key]
    if not ctx.live:
        from qiskit_ibm_runtime import fake_provider as fp
        b = getattr(fp, FAKE_BACKEND)()
        s = Session(b, _target(b, False), None, False)
    else:
        from qiskit_ibm_runtime import QiskitRuntimeService
        service = QiskitRuntimeService()                           # pre-saved account, never a token
        saved = runio.load_json(ctx.run_dir / "backend.json")
        name = saved["name"] if saved else ctx.backend
        if name == "auto":
            b = service.least_busy(operational=True, simulator=False, min_num_qubits=100)
        else:
            b = service.backend(name)
        s = Session(b, _target(b, True), service, True)
        log(f"backend {b.name}: {b.num_qubits} qubits")
    runio.save_json(ctx.path("backend.json"), {"name": s.target.name, "live": s.live, "label": s.target.label,
                                               "calibration": s.target.calibration})
    _SESSION[key] = s
    return s


# ---------------------------------------------------------------------------------------------- jobs
def qpu_seconds(isa: list[QuantumCircuit], b, shots: list[int]) -> float:
    tot = 0.0
    for c, sh in zip(isa, shots):
        try:
            d = float(c.estimate_duration(b.target, unit="s"))
        except Exception:
            d = c.depth() * 1e-7 + 3e-6
        tot += sh * (d + REP_DELAY_S)
    return tot


def fit_shots(ctx: Ctx, key: str, isa: list[QuantumCircuit], shots: list[int], scalable: bool = True) -> list[int]:
    """Spend guard for a live job: cut the shots to the QPU-s left in the run."""
    s = session(ctx)
    if not s.live:
        return shots
    est, left = qpu_seconds(isa, s.backend, shots), MAX_QPU_SECONDS - ctx.qpu_spent
    if est > left:
        scale = max(left, 0.0) / est
        if not scalable or min(shots) * scale < MIN_SHOTS:
            raise Refused(f"{key}: ~{est:.1f} QPU-s needed, {left:.1f} left under the cap of {MAX_QPU_SECONDS:.0f}")
        shots = [max(1, int(sh * scale)) for sh in shots]
    return shots


def run_isa(ctx: Ctx, key: str, isa: list[QuantumCircuit], shots: list[int], dd: bool = True, twirl: bool = False,
            wide: bool = False):
    """Submit (or fetch) one SamplerV2 job; returns (result, job id, label)."""
    from qiskit_ibm_runtime import SamplerV2

    s = session(ctx)
    pubs = [(c, None, int(sh)) for c, sh in zip(isa, shots)]
    if not s.live:
        from qiskit_aer import AerSimulator
        sim = AerSimulator.from_backend(s.backend, method="matrix_product_state" if wide else "automatic")
        return SamplerV2(mode=sim).run(pubs).result(), "", s.label()
    job_file = ctx.path("jobs", f"{key.replace('/', '_')}.json")
    saved = runio.load_json(job_file)
    job = s.service.job(saved["job_id"]) if saved else None
    if job is not None and "CANCELLED" in str(job.status()):   # cancelled by hand: nothing to fetch, submit again
        log(f"{key}: job {saved['job_id']} was cancelled, submitting a new one")
        job = None
    if job is not None:
        log(f"{key}: fetching the job submitted earlier, {saved['job_id']}")
    else:
        sampler = SamplerV2(mode=s.backend)
        sampler.options.dynamical_decoupling.enable = dd
        if dd:
            sampler.options.dynamical_decoupling.sequence_type = "XX"
        sampler.options.twirling.enable_measure = twirl
        job = sampler.run(pubs)
        est = qpu_seconds(isa, s.backend, shots)
        runio.save_json(job_file, {"job_id": job.job_id(), "backend": s.target.name, "circuits": len(isa),
                                   "shots": shots if len(set(shots)) > 1 else shots[0], "qpu_seconds_estimate": est})
        ctx.qpu_spent += est
        log(f"{key}: SUBMITTED job {job.job_id()} on {s.target.name} ({len(isa)} circuits, ~{est:.1f} QPU-s)")
    t0, last = time.time(), None
    while True:
        try:
            st = str(job.status())
        except Exception as e:                             # transient API error: keep waiting
            st = f"status unavailable ({e.__class__.__name__})"
        if st != last:
            log(f"job {job.job_id()}: {st} (waited {int(time.time() - t0)} s)")
            last = st
        if any(k in st for k in ("DONE", "ERROR", "CANCELLED")):
            break
        time.sleep(30 if "QUEUED" in st or "RUNNING" in st else 5)
    return job.result(), job.job_id(), s.label(job.job_id())


def bits(pub, reg: str = "c") -> np.ndarray:
    """(shots, n_clbits) uint8; column k = classical bit k of register `reg`."""
    return np.array([[int(ch) for ch in w[::-1]] for w in getattr(pub.data, reg).get_bitstrings()], dtype=np.uint8)


def execute(ctx: Ctx, key: str, circuits: list[QuantumCircuit], shots: int | list[int], opt: int = 1,
            scalable: bool = True) -> tuple[list[np.ndarray], dict]:
    """Run compact circuits (circuit qubit k = physical qubit metadata["layout"][k]; one classical register "c").
    Raw counts: dynamical decoupling on, no measurement twirling, no readout mitigation.
    Dry run of a Clifford job wider than WIDE qubits: the Pauli-twirled model of the fake backend (stabilizer).
    -> (bits per circuit as (shots, n_clbits) uint8, info)."""
    for qc in circuits:
        hit = L._rule1(qc)
        if hit:
            raise Refused(f"lint rule 1 (no mid-circuit measure / reset / feed-forward): {hit}")
    s = session(ctx)
    per = list(shots) if isinstance(shots, (list, tuple)) else [int(shots)] * len(circuits)
    isa = [transpile(qc, backend=s.backend, initial_layout=(qc.metadata or {}).get("layout"), optimization_level=opt,
                     seed_transpiler=1) for qc in circuits]
    per = fit_shots(ctx, key, isa, per, scalable)
    g2 = s.target.gate_2q
    info = {"backend": s.target.name, "circuits": len(isa), "shots": per[0] if len(set(per)) == 1 else per,
            "two_qubit_gates_max": max(c.count_ops().get(g2, 0) for c in isa)}
    log(f"{key}: {len(isa)} circuits, up to {info['two_qubit_gates_max']} {g2} each, on {s.target.name}")
    wide = max(qc.num_qubits for qc in circuits) > WIDE
    if not s.live and wide and all(PN.is_clifford(qc) for qc in circuits):
        seed = runio.derive_seed(runio.config_seed(ctx, key), "sim") % (2 ** 31)
        out = []
        for c, sh in zip(isa, per):
            res = PN.run([PN.delays_to_pauli(c, s.target.name)], s.target.name, int(sh), seed)
            out.append(np.array([[int(ch) for ch in w.replace(" ", "")[::-1]] for w in res.get_memory(0)], np.uint8))
        return out, info | {"job_id": "", "label": f"dry run: Pauli-twirled {FAKE_BACKEND} noise, stabilizer "
                                                   f"simulation (not hardware)"}
    res, job_id, label = run_isa(ctx, key, isa, per, wide=wide)
    return [bits(res[i]) for i in range(len(isa))], info | {"job_id": job_id, "label": label}


# ---------------------------------------------------------------------------------------------- claims
def binom_sigma(p: float, n: int) -> float:
    return math.sqrt(max(p * (1 - p), 1e-12) / max(n, 1))


def claim(ctx: Ctx, name: str, cfg: dict, value, sigma, passed: bool, label: str, note: str = "") -> dict:
    """One claim row. A dry-run pass is never a hardware claim (honesty gate)."""
    lvl = cfg["level"] if ctx.live else f"{cfg['level']} (dry run: not a claim)"
    return {"config": name, "family": name, "claim_level": lvl, "witness": cfg["witness"], "value": value,
            "sigma": sigma, "bound": cfg.get("bound"), "bound_rigour": cfg.get("rigour"), "passed": bool(passed),
            "label": label, "pass_rule": cfg.get("pass"), "note": (cfg.get("adversary", "") + ". " + note).strip(". ") + "."}


def rng(ctx: Ctx, name: str, label: str) -> np.random.Generator:
    """Seeded by the run (roll job id or run name) and the circuit name: a continued run rebuilds the same circuits."""
    return runio.rng(runio.config_seed(ctx, name), label)


def save(ctx: Ctx, name: str, result: dict) -> None:
    runio.save_json(ctx.path("qhard", name, "result.json"), result)


def run_circuit(ctx: Ctx, name: str, cfg: dict) -> list[dict]:
    """Run one named circuit of a section's CIRCUITS table; a refusal is printed and recorded, never raised."""
    from importlib import import_module

    log(f"--- circuit {name}")
    if not ctx.live:                       # dry run tests the pipeline: the circuit's small "dry" sizes, no refusals
        cfg = {k: v for k, v in cfg.items() if k != "refuse"} | cfg.get("dry", {})
    try:
        target = session(ctx).target.name.lower()
        for frag, why in cfg.get("refuse", {}).items():
            if frag in target:
                raise Refused(f"do-not-build list for {target}: {why}")
        mod, fn = cfg["run"].split(":")
        claims = getattr(import_module(mod), fn)(ctx, name, cfg)
    except Refused as e:
        log(f"{name}: not run: {e}")
        save(ctx, name, {"status": "not run", "reason": str(e)})
        return [{"config": name, "family": name, "claim_level": "not run", "witness": cfg.get("witness", name),
                 "value": None, "sigma": None, "passed": False, "label": "not run", "note": f"Not run: {e}"}]
    for c in claims:
        log(f"{name}: {c['witness']}: {c['value']} (passed {c['passed']}, {c['claim_level']})")
    return claims
