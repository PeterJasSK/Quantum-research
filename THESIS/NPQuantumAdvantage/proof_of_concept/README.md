# Proof of Concept — Quantum Query Advantage on an NP Verifier

Two files, one instance, one honest claim.

| File | Role |
|---|---|
| `classical_bruteforce.py` | Best *classical* solver for an unstructured NP verifier: exhaustive search. Provably optimal in the query model (adversary bound). |
| `quantum_grover.py` | *Quantum* counterpart: Grover search for the same satisfying assignment, runnable on real IBM hardware. |

## The instance
A 9-clause 3-SAT verifier over 4 variables with **exactly one** satisfying assignment (`0101`) — a true needle in a 16-cell haystack. The verifier `V(x)` is a black box: you may only *evaluate* it.

## Why the quantum method is better

The claim is precise — four qualifiers, no exceptions: **query model · over brute force · quadratic · not wall-clock.**

| | Classical (best possible) | Quantum (Grover) |
|---|---|---|
| Oracle calls | `O(2^n)` — this instance: **16** | `~(π/4)·√(2^n/M)` — this instance: **3** |
| Lower bound | `Ω(2^n)` (adversary argument) | `Ω(√(2^n))` (BBBV 1997) |
| Optimal? | yes, classically | yes, quantumly |
| Speedup | — | **quadratic**, `2^n → 2^(n/2)` |

Both the classical *upper* bound (brute force) and the classical *lower* bound (adversary) are `2^n`; both the quantum *upper* bound (Grover) and *lower* bound (BBBV) are `2^(n/2)`. The gap between them is the advantage, and it is **provable and unconditional** — it does not depend on P vs NP. Measured here: solution amplified to ~96% probability in 3 oracle calls, versus the 6.25% uniform-guess floor.

## The one honest caveat (do not skip)
On today's **NISQ hardware Grover does not win in wall-clock seconds** — noise degrades amplification and the oracle has real depth. The hardware run is a **feasibility demonstration**: it shows the marked state rises far above the `1/2^n` floor on a real device. The *advantage* is the oracle-**call** count, which is exact and device-independent. Presenting a hardware run as the advantage proof would be an overclaim; presenting the call count is the theorem.

## When this advantage COLLAPSES (the thesis map)
The advantage above **survives** only because the verifier is unstructured — best-known-classical == brute force. If a problem's verifier has exploitable structure, a smarter classical algorithm matches `2^(n/2)` and the quantum edge vanishes:
- **Number partitioning / subset-sum** → meet-in-the-middle already runs `~2^(n/2)` → **collapses**.
- **Generic random 3-SAT** (this POC) → no such shortcut → **survives**.

Mapping which of five forgotten 1970s NP-complete problems land on each side is the full thesis (`../../plans/thesis-4-obscure-np-query-advantage.md`). This POC proves the *survives* mechanism end to end.

## Run
```bash
python classical_bruteforce.py            # classical baseline + call count
python quantum_grover.py                   # Grover on Aer simulator
python quantum_grover.py --backend auto    # least-busy real IBM device
python quantum_grover.py --backend ibm_fez # named real device
```
Deps: `qiskit`, `qiskit-aer`; hardware also needs `qiskit-ibm-runtime` + a saved IBM Quantum account.


RUN : (base) peter@home:~/PycharmProjects/Quantum-research/THESIS$ python NPQuantumAdvantage/proof_of_concept/quantum_grover.py --backend ibm_kingston
search space   : 2^4 = 16
marked states  : ['0101']  (M=1)
Grover oracle calls (quantum) : 3
classical calls (brute force) : 16
speedup factor this instance  : 5.3x  (asymptotic: 2^(n/2))

backend : ibm_kingston (156 qubits)
top measured bitstrings:
  0101   51.9%  <-- SOLUTION
  0001    5.1%
  0100    4.5%
  0111    4.3%
  1101    4.3%

success probability (measured a solution): 51.9%
uniform-guess floor for comparison       : 6.2%
amplitude amplification worked if measured >> uniform floor.
(base) peter@home:~/PycharmProjects/Quantum-research/THESIS$ python NPQuantumAdvantage/proof_of_concept/classical_bruteforce.py 
problem     : 9-clause SAT verifier over 4 vars
search space: 2^4 = 16 assignments
solutions   : ['0101']  (M=1)
verifier calls (classical, worst case): 16  == 2^4
classical query cost scales as O(2^n).

COLLAPSE boundary: if the verifier decomposed additively (e.g. subset-sum
/ number partitioning), meet-in-the-middle splits the n bits into two
halves, sorts 2^(n/2) partial sums, and matches them in ~2^(n/2) time —
erasing Grover's edge. No such decomposition exists for a generic SAT
verifier, so here brute force stays optimal and the quantum edge SURVIVES.