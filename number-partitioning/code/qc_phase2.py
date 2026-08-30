"""Phase 2 QAOA for SK number partitioning — optimized conversion.

Phase 1 (qc_phase1.py) made the dense K_n circuit FIT on hardware (linear SWAP
network, O(n) depth). But its p=1 layer used fixed, UNNORMALIZED angles: with
J_ij = 2 a_i a_j ~ 5e5 and gamma = pi/8, every rz(2*gamma*J) wrapped mod 2*pi to
a garbage angle, so the cost layer encoded almost nothing about H. Result:
P(optimum) stuck on the floor (~1e-4 at n=156), best-of-shots found the answer
only by coverage of an exponentially degenerate optimum.

Phase 2 fixes the CONVERSION (odds that a single shot lands on the optimum), so
the same swap-network circuit finds the optimum with FAR fewer shots. Three
stacked levers, no extra circuit depth over Phase 1:

  1. gamma normalization. theta = gamma * (J_ij / Jmax), gamma dimensionless in
     ~(0, pi]. Every ZZ phase now lands in-range -> the cost layer actually tilts
     amplitude toward balanced (low-H) partitions.
  2. CVaR objective. Tune on the best-alpha tail of the energy distribution, not
     the mean. The tail is exactly what best-of-shots harvests, so this optimizes
     the metric we care about instead of a scale-inflated average.
  3. Classical angle optimization. (gamma, beta) found by grid + local refine on
     a SMALL-n statevector sim (exact, cheap). Because couplings are normalized,
     the dimensionless angles TRANSFER to large n on hardware (QAOA angle
     concordance) -- tune at n=14 in milliseconds, run at n=156 on the chip.

Goal: >= 90% probability of finding the optimum in <= 1000 shots. That target is
reachable in the dense-optimum regime (large n, perfect / near-perfect split)
where Phase 2's tilt + degeneracy compound. On real hardware at depth ~4n, add
error mitigation (dynamical decoupling, measurement mitigation) to hold it.

Encoding: |0> = spin +1, |1> = spin -1 (Qiskit little-endian). Deps: qiskit,
qiskit-aer, numpy. Real QC (--backend) also needs qiskit-ibm-runtime + account.
"""
from __future__ import annotations

from math import pi

import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


# -----------------------------------------------------------------------------
# problem
# -----------------------------------------------------------------------------
def make_instance(n: int, seed: int) -> list[int]:
    """n random 10-bit integers in [1, 1023], fixed by seed (matches other files)."""
    import random
    rng = random.Random(seed)
    return [rng.randint(1, (1 << 10) - 1) for _ in range(n)]


def couplings(a: list[int]) -> dict[tuple[int, int], float]:
    """J_ij = 2 a_i a_j for every pair i<j."""
    n = len(a)
    return {(i, j): 2.0 * a[i] * a[j] for i in range(n) for j in range(i + 1, n)}


def energy(bits: str, a: list[int]) -> float:
    """H = (sum a_i s_i)^2; s_i = +1 for bit '0', -1 for '1'. Little-endian."""
    b = bits[::-1]
    total = sum(a[i] * (1.0 if b[i] == "0" else -1.0) for i in range(len(a)))
    return total * total


def _optimum_energy(a: list[int]) -> float:
    """Exact min energy = (min deviation)^2 via subset-sum DP. O(n * sum a)."""
    total = sum(a)
    reachable = {0}
    for x in a:
        reachable |= {s + x for s in reachable}
    best_d = min(abs(2 * s - total) for s in reachable)
    return float(best_d * best_d)


# -----------------------------------------------------------------------------
# circuit: Phase 1 swap network + NORMALIZED gamma (lever 1)
# -----------------------------------------------------------------------------
def _final_perm(n: int, p: int = 1) -> list[int]:
    """Logical qubit on each physical wire after p swap-net sweeps.

    Angle-independent, so callers precompute it once to map a physical-basis
    statevector back to logical spins. One sweep fully reverses the wires; p
    sweeps compose (even p = identity, odd p = reversal).
    """
    wire = list(range(n))
    for _ in range(p):
        for layer in range(n):
            for q in range(layer % 2, n - 1, 2):
                wire[q], wire[q + 1] = wire[q + 1], wire[q]
    return wire


def _cost_layer(qc: QuantumCircuit, a: list[int], gamma: float,
                wire: list[int], jmax: float,
                J: dict[tuple[int, int], float]) -> None:
    """One swap-network cost sweep with NORMALIZED gamma; mutates `wire` in place.

    theta = gamma * J_ij / Jmax keeps every ZZ phase in ~(0, gamma] so the layer
    imprints H coherently instead of wrapping to noise (the Phase 1 bug). One
    sweep = n odd-even layers => every logical pair adjacent exactly once, so the
    permutation `wire` is the SAME after every sweep (composes cleanly for p>1).
    """
    n = len(a)

    def jget(x: int, y: int) -> float:
        return J[(x, y)] if x < y else J[(y, x)]

    for layer in range(n):
        for p in range(layer % 2, n - 1, 2):
            i, j = wire[p], wire[p + 1]
            theta = gamma * jget(i, j) / jmax           # <-- normalization
            qc.cx(p, p + 1)
            qc.rz(2.0 * theta, p + 1)
            qc.cx(p + 1, p)
            qc.cx(p, p + 1)
            wire[p], wire[p + 1] = wire[p + 1], wire[p]


def build_circuit(a: list[int], gammas, betas,
                  measure: bool = True) -> QuantumCircuit:
    """p-layer QAOA, linear swap network, normalized gammas. p = len(gammas).

    Each sweep reverses `wire`; two sweeps restore identity, so we track `wire`
    across layers and measure through the net permutation at the end.
    """
    gammas = [gammas] if isinstance(gammas, (int, float)) else list(gammas)
    betas = [betas] if isinstance(betas, (int, float)) else list(betas)
    n = len(a)
    J = couplings(a)
    jmax = max(abs(v) for v in J.values())

    qc = QuantumCircuit(n, n) if measure else QuantumCircuit(n)
    qc.h(range(n))
    wire = list(range(n))
    for g, b in zip(gammas, betas):
        _cost_layer(qc, a, g, wire, jmax, J)
        for p in range(n):
            qc.rx(2.0 * b, p)
    if measure:
        for p in range(n):                              # physical p holds logical wire[p]
            qc.measure(p, wire[p])
    return qc


# -----------------------------------------------------------------------------
# exact objective on small n (lever 2 + 3 machinery)
# -----------------------------------------------------------------------------
def _energy_array(a: list[int], p_layers: int = 1) -> np.ndarray:
    """H for every 2^n basis state, indexed by the PHYSICAL-wire integer.

    Physical wire p carries logical qubit _final_perm(n, p_layers)[p], so we score
    with the permuted weights a_phys -- lets us read energies straight off a
    statevector (index = physical-wire integer, qubit 0 = LSB).
    """
    n = len(a)
    perm = _final_perm(n, p_layers)
    a_phys = np.array([a[perm[p]] for p in range(n)], dtype=np.float64)
    x = np.arange(1 << n, dtype=np.int64)
    total = np.zeros(1 << n, dtype=np.float64)
    for i in range(n):
        s = 1.0 - 2.0 * ((x >> i) & 1)                  # +1 if bit 0 else -1
        total += a_phys[i] * s
    return total * total


def _statevector_probs(qc: QuantumCircuit) -> np.ndarray:
    from qiskit.quantum_info import Statevector
    return np.asarray(Statevector(qc).probabilities())


def _cvar(probs: np.ndarray, energies: np.ndarray, alpha: float) -> float:
    """CVaR_alpha: mean energy over the best-alpha probability mass (lever 2)."""
    order = np.argsort(energies)
    e, p = energies[order], probs[order]
    acc, cost = 0.0, 0.0
    for ei, pi_ in zip(e, p):
        if acc >= alpha:
            break
        take = min(pi_, alpha - acc)
        cost += ei * take
        acc += take
    return cost / acc if acc > 0 else float(e[0])


def tune_angles(a_tune: list[int], p: int = 1, alpha: float = 0.15,
                verbose: bool = True) -> tuple[list[float], list[float], float]:
    """Optimize 2p angles (gammas, betas) minimizing CVaR on an exact small-n sim.

    p=1 seeded by a coarse grid; higher p bootstrapped by INTERP (ramp the p=1
    winner into p slots) then polished with Nelder-Mead. Normalized couplings let
    the dimensionless angles transfer to larger n (lever 3).
    Returns (gammas, betas, p_optimum_at_tune_n).
    """
    energies = _energy_array(a_tune, p)
    opt = energies.min()
    opt_mask = np.isclose(energies, opt)

    def cvar_of(vec) -> float:
        g, b = list(vec[:p]), list(vec[p:])
        probs = _statevector_probs(build_circuit(a_tune, g, b, measure=False))
        return _cvar(probs, energies, alpha)

    def p_opt_of(vec) -> float:
        g, b = list(vec[:p]), list(vec[p:])
        probs = _statevector_probs(build_circuit(a_tune, g, b, measure=False))
        return float(probs[opt_mask].sum())

    # p=1 coarse grid to seed
    best1 = (pi / 4, pi / 4, float("inf"))
    e1 = _energy_array(a_tune, 1)
    for g in np.linspace(0.05, pi, 16):
        for b in np.linspace(0.05, pi / 2, 10):
            probs = _statevector_probs(build_circuit(a_tune, [g], [b], measure=False))
            c = _cvar(probs, e1, alpha)
            if c < best1[2]:
                best1 = (g, b, c)
    g1, b1, _ = best1

    # seed p slots: gamma ramps 0->g1, beta ramps b1->0 (standard QAOA schedule)
    if p == 1:
        seed = np.array([g1, b1])
    else:
        gs = np.linspace(g1 / p, g1, p)
        bs = np.linspace(b1, b1 / p, p)
        seed = np.concatenate([gs, bs])

    from scipy.optimize import minimize
    res = minimize(cvar_of, seed, method="Nelder-Mead",
                   options={"maxiter": 400 * p, "xatol": 1e-3, "fatol": 1e-3})
    vec = res.x
    if cvar_of(seed) < cvar_of(vec):        # keep seed if polish regressed
        vec = seed
    gammas, betas = [float(x) for x in vec[:p]], [float(x) for x in vec[p:]]
    po = p_opt_of(vec)
    if verbose:
        print(f"tuned on n={len(a_tune)} p={p} (alpha={alpha}): "
              f"P(opt)@tune={po:.4f}")
        print(f"  gammas={[round(x, 3) for x in gammas]}  "
              f"betas={[round(x, 3) for x in betas]}")
    return gammas, betas, po


# -----------------------------------------------------------------------------
# sampling paths
# -----------------------------------------------------------------------------
def _counts_sim(qc: QuantumCircuit, shots: int) -> dict[str, int]:
    return AerSimulator().run(qc, shots=shots).result().get_counts()


def _counts_hw(qc: QuantumCircuit, shots: int, backend_name: str) -> dict[str, int]:
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService()
    backend = service.backend(backend_name)
    print(f"backend : {backend.name} ({backend.num_qubits} qubits)")
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    isa = pm.run(qc)
    result = SamplerV2(mode=backend).run([isa], shots=shots).result()
    return result[0].data.c.get_counts()


def run_target(a: list[int], gammas, betas, shots: int,
               backend: str = "") -> dict:
    """Sample the tuned circuit at the target size; score against exact optimum."""
    qc = build_circuit(a, gammas, betas, measure=True)
    n2q = sum(1 for inst in qc.data if inst.operation.num_qubits == 2)
    counts = _counts_hw(qc, shots, backend) if backend else _counts_sim(qc, shots)

    total = sum(counts.values())
    opt = _optimum_energy(a)
    worst = float(sum(a) ** 2)
    best_bits = min(counts, key=lambda b: energy(b, a))
    best_e = energy(best_bits, a)
    mean_e = sum(energy(b, a) * c for b, c in counts.items()) / total
    p_opt = sum(c for b, c in counts.items() if energy(b, a) == opt) / total
    approx = 1.0 if worst == opt else (worst - mean_e) / (worst - opt)
    # predicted odds of catching the optimum in `shots` given the per-shot rate
    predict = 1.0 - (1.0 - p_opt) ** shots if p_opt > 0 else 0.0
    return {
        "numbers": a,
        "best_bits": best_bits,
        "min_deviation": round(best_e ** 0.5),
        "optimum_deviation": round(opt ** 0.5),
        "found_optimum": best_e == opt,
        "mean_deviation": round(mean_e ** 0.5),
        "approx_ratio": round(approx, 3),
        "p_optimum": round(p_opt, 5),
        "predicted_success_at_shots": round(predict, 4),
        "shots": shots,
        "logical_depth": qc.depth(),
        "two_qubit_gates": n2q,
    }


def validate(a: list[int], gammas, betas, shots: int,
             trials: int) -> dict:
    """Empirical success rate: fraction of `trials` where best-of-`shots` == optimum.

    Sim only (needs many independent shot batches). Direct measurement of the
    '>= 90% at 1000 shots' goal at a size the statevector sim can still reach.
    """
    opt = _optimum_energy(a)
    sim = AerSimulator()
    qc = build_circuit(a, gammas, betas, measure=True)
    hits = 0
    p_sum = 0.0
    for _ in range(trials):
        counts = sim.run(qc, shots=shots).result().get_counts()
        tot = sum(counts.values())
        best_e = min(energy(b, a) for b in counts)
        p_sum += sum(c for b, c in counts.items() if energy(b, a) == opt) / tot
        hits += int(best_e == opt)
    return {
        "optimum_deviation": round(opt ** 0.5),
        "trials": trials,
        "shots_each": shots,
        "success_rate": round(hits / trials, 3),
        "mean_p_optimum": round(p_sum / trials, 5),
    }


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Phase 2 QAOA number partitioning (normalized + CVaR + tuned)")
    ap.add_argument("numbers", nargs="*", type=int,
                    help="explicit integers; else use --n/--seed")
    ap.add_argument("--n", type=int, default=0, help="target problem size")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--shots", type=int, default=1000)
    ap.add_argument("--p", type=int, default=1, help="QAOA layers (depth ~ p*4n)")
    ap.add_argument("--optimize-n", type=int, default=14,
                    help="size to tune angles on (exact statevector sim)")
    ap.add_argument("--alpha", type=float, default=0.15, help="CVaR tail fraction")
    ap.add_argument("--gammas", type=float, nargs="*", default=None,
                    help="skip tuning, use these p dimensionless gammas")
    ap.add_argument("--betas", type=float, nargs="*", default=None,
                    help="skip tuning, use these p betas")
    ap.add_argument("--trials", type=int, default=0,
                    help=">0: sim-validate empirical success rate over N batches")
    ap.add_argument("--backend", type=str, default="",
                    help="IBM backend for real QC (e.g. ibm_fez); empty = Aer sim")
    args = ap.parse_args()

    a = args.numbers if args.numbers else make_instance(args.n or 4, args.seed)

    # angles: tuned on a small same-family instance, or taken from flags
    if args.gammas is not None and args.betas is not None:
        gammas, betas = args.gammas, args.betas
        print(f"using given angles: gammas={gammas} betas={betas}")
    else:
        a_tune = make_instance(args.optimize_n, args.seed)
        gammas, betas, _ = tune_angles(a_tune, p=args.p, alpha=args.alpha)

    if args.trials > 0:
        v = validate(a, gammas, betas, args.shots, args.trials)
        print("--- empirical validation (sim) ---")
        print(f"optimum deviation    : {v['optimum_deviation']}")
        print(f"trials x shots       : {v['trials']} x {v['shots_each']}")
        print(f"SUCCESS RATE         : {v['success_rate']}  "
              f"(fraction of batches whose best-of-shots hit the optimum)")
        print(f"mean P(optimum)      : {v['mean_p_optimum']}")
    else:
        res = run_target(a, gammas, betas, args.shots, backend=args.backend)
        print(f"numbers              : {res['numbers']}")
        print(f"routing              : swapnet+normalized  "
              f"(logical depth {res['logical_depth']}, 2q gates {res['two_qubit_gates']})")
        print(f"optimum deviation    : {res['optimum_deviation']}  (classical bar)")
        print("--- best-of-shots ---")
        print(f"best partition bits  : {res['best_bits']}")
        print(f"min deviation        : {res['min_deviation']}")
        print(f"found optimum        : {res['found_optimum']}")
        print("--- conversion quality ---")
        print(f"mean deviation       : {res['mean_deviation']}")
        print(f"approx ratio [0..1]  : {res['approx_ratio']}")
        print(f"P(optimum sampled)   : {res['p_optimum']}")
        print(f"pred. success @ {res['shots']:>5} shots : "
              f"{res['predicted_success_at_shots']}")
