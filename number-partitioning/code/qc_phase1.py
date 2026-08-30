"""Phase 1 QAOA for SK number partitioning — linear SWAP network routing.

Twin of qc_simplified.py (same physics, same scoring) but replaces the bare
all-to-all cost layer with a LINEAR SWAP NETWORK so the dense K_n coupling maps
onto a chain with NO added routing SWAPs. That is the fix for the n=60 depth
wall recorded in RUNLOG_MONTH1.md: bare routing inserts O(n^2) SWAP chains to
bring far qubits adjacent and blows past coherence; the swap network does every
pairwise ZZ in n odd-even layers at O(n) depth.

Problem: H = (sum_i a_i s_i)^2. Coupling J_ij = 2 a_i a_j on every pair.

SWAP-network idea (Kivlichen 2018). Keep n logical qubits on a line. Run n
odd-even layers; each adjacent-pair gate fuses the ZZ of whatever logical pair
currently sits on those two wires WITH a SWAP that permutes them. After n layers
every logical pair has been adjacent exactly once -> all n(n-1)/2 interactions
applied, zero routing SWAPs added. Fused ZZ+SWAP = 3 CX (the SWAP's closing CX
cancels the ZZ's closing CX):
    exp(-i theta ZZ) then SWAP  =  CX(p,q) . RZ(2 theta, q) . CX(q,p) . CX(p,q)
All gates act on physically ADJACENT wires -> a line embedding routes clean.

Encoding: |0> = spin +1, |1> = spin -1  (Qiskit little-endian bitstring).
Deps: qiskit, qiskit-aer (sim). Real QC path (--backend) also needs
qiskit-ibm-runtime and a saved IBM Quantum account. No project imports.
"""
from __future__ import annotations

from math import pi

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


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


def build_circuit(a: list[int], gamma: float, beta: float) -> QuantumCircuit:
    """One p=1 QAOA layer routed by a linear SWAP network (O(n) depth).

    wire[p] = logical qubit currently on physical wire p. Odd-even layers fuse
    ZZ + SWAP on adjacent wires; every logical pair meets exactly once.
    """
    n = len(a)
    J = couplings(a)                      # keyed by logical pair (i, j), i < j

    def jget(x: int, y: int) -> float:
        return J[(x, y)] if x < y else J[(y, x)]

    qc = QuantumCircuit(n, n)
    qc.h(range(n))
    wire = list(range(n))                 # wire[p] = logical qubit on physical wire p
    for layer in range(n):
        for p in range(layer % 2, n - 1, 2):   # even layers pair (0,1)..; odd (1,2)..
            i, j = wire[p], wire[p + 1]
            theta = gamma * jget(i, j)
            qc.cx(p, p + 1)
            qc.rz(2.0 * theta, p + 1)
            qc.cx(p + 1, p)
            qc.cx(p, p + 1)
            wire[p], wire[p + 1] = wire[p + 1], wire[p]
    for p in range(n):
        qc.rx(2.0 * beta, p)
    for p in range(n):                    # physical wire p holds logical wire[p]
        qc.measure(p, wire[p])
    return qc


def _counts_sim(qc: QuantumCircuit, shots: int) -> dict[str, int]:
    return AerSimulator().run(qc, shots=shots).result().get_counts()


def _counts_hw(qc: QuantumCircuit, shots: int, backend_name: str) -> dict[str, int]:
    """Submit to a real IBM Quantum backend. Needs a saved account (see runlog)."""
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    service = QiskitRuntimeService()
    backend = service.backend(backend_name)
    print(f"backend : {backend.name} ({backend.num_qubits} qubits)")
    pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
    isa = pm.run(qc)
    result = SamplerV2(mode=backend).run([isa], shots=shots).result()
    return result[0].data.c.get_counts()


def run(a: list[int], gamma: float, beta: float, shots: int,
        backend: str = "") -> dict:
    qc = build_circuit(a, gamma, beta)
    n2q = sum(1 for inst in qc.data if inst.operation.num_qubits == 2)
    counts = _counts_hw(qc, shots, backend) if backend else _counts_sim(qc, shots)

    total = sum(counts.values())
    # optimum via subset-sum DP -- O(n * sum), NOT the 2^n scan (dies past n~25).
    # worst energy is exact and free: all spins aligned -> (sum a)^2.
    opt = _optimum_energy(a)
    worst = float(sum(a) ** 2)

    # best-of-shots: a CLASSICAL scan of the sampled states. NOT a QAOA metric --
    # at small n with many shots, coverage alone finds the optimum (even from a
    # random/noisy distribution). Kept only to show that.
    best_bits = min(counts, key=lambda b: energy(b, a))
    best_e = energy(best_bits, a)

    # HONEST quantum-quality metrics: mean energy over the sampled distribution,
    # and how much of the distribution actually landed on the optimum.
    mean_e = sum(energy(b, a) * c for b, c in counts.items()) / total
    p_opt = sum(c for b, c in counts.items() if energy(b, a) == opt) / total
    # approx ratio in [0,1]; 1 = distribution sits at the optimum, 0 = at worst.
    approx = 1.0 if worst == opt else (worst - mean_e) / (worst - opt)
    return {
        "numbers": a,
        "best_bits": best_bits,
        "min_deviation": round(best_e ** 0.5),      # best-of-shots (classical)
        "optimum_deviation": round(opt ** 0.5),     # exact classical optimum
        "found_optimum": best_e == opt,             # near-trivial at small n
        "mean_deviation": round(mean_e ** 0.5),     # QAOA distribution centre
        "approx_ratio": round(approx, 3),           # the real QAOA quality number
        "p_optimum": round(p_opt, 4),               # frac of shots at the optimum
        "shots": shots,
        "logical_depth": qc.depth(),                # pre-transpile logical depth
        "two_qubit_gates": n2q,                     # logical 2q-gate count
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Phase 1 QAOA (linear SWAP network)")
    ap.add_argument("numbers", nargs="*", type=int,
                    help="explicit integers, e.g. 14 7 13 15; else use --n/--seed")
    ap.add_argument("--n", type=int, default=0, help="generate n random numbers")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--shots", type=int, default=20000)
    ap.add_argument("--gamma", type=float, default=pi / 8)
    ap.add_argument("--beta", type=float, default=pi / 4)
    ap.add_argument("--backend", type=str, default="",
                    help="IBM backend name for real QC (e.g. ibm_fez); empty = Aer sim")
    args = ap.parse_args()

    a = args.numbers if args.numbers else make_instance(args.n or 4, args.seed)
    res = run(a, args.gamma, args.beta, args.shots, backend=args.backend)
    print(f"numbers              : {res['numbers']}")
    print(f"routing              : swapnet  "
          f"(logical depth {res['logical_depth']}, 2q gates {res['two_qubit_gates']})")
    print(f"optimum deviation    : {res['optimum_deviation']}  (classical bar)")
    print("--- best-of-shots (CLASSICAL scan of samples; trivial at small n) ---")
    print(f"best partition bits  : {res['best_bits']}")
    print(f"min deviation        : {res['min_deviation']}")
    print(f"found optimum        : {res['found_optimum']}")
    print("--- QAOA distribution quality (the honest numbers) ---")
    print(f"mean deviation       : {res['mean_deviation']}")
    print(f"approx ratio [0..1]  : {res['approx_ratio']}")
    print(f"P(optimum sampled)   : {res['p_optimum']}")
