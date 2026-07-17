# Quantum Algorithms Explained

A hands-on tour of 15 standard quantum algorithms, from the absolute basics to
the exponential-speedup capstones. Each lesson is self-contained: read the
explanation, run the code, look at the numbers it produced.

**Everything runs on a local simulator** (Qiskit's built-in
`StatevectorSampler`) — no quantum hardware, no IBM account, no cost, and fully
reproducible (a fixed random seed pins the numbers).

## Layout
```
QuantumAlgorithmsExplained/
├── NN_name.md      ← the lesson: what it is, why it matters, how to read the result
├── code/           ← runnable Python (one script per algorithm) + _common.py helper
├── result/         ← JSON output produced by each run (counts + probabilities)
└── graph/          ← measurement histogram PNG for each run
```
Each lesson `.md` links to its `code/`, `result/` JSON and `graph/` PNG.

## The 15 lessons (easy → hard)

| # | Algorithm | Concept | Speedup vs classical |
|---|---|---|---|
| [01](explenation/01_coin_flip.md) | Quantum Coin Flip | superposition (`H`) | — (true randomness) |
| [02](explenation/02_bell_state.md) | Bell State | entanglement (`CNOT`) | — (foundation) |
| [03](explenation/03_ghz_state.md) | GHZ State | multi-qubit entanglement | — (foundation) |
| [04](explenation/04_teleportation.md) | Teleportation | move a state w/ entanglement | — (protocol) |
| [05](explenation/05_deutsch_jozsa.md) | Deutsch–Jozsa | phase kick-back, interference | exponential (promise problem) |
| [06](explenation/06_bernstein_vazirani.md) | Bernstein–Vazirani | read a hidden string in 1 query | `n` → 1 |
| [07](explenation/07_superdense_coding.md) | Superdense Coding | entanglement as bandwidth | 2 bits per 1 qubit |
| [08](explenation/08_bb84.md) | BB84 Key Distribution | measurement disturbance | secure key exchange |
| [09](explenation/09_quantum_adder.md) | Quantum Half-Adder | reversible arithmetic, Toffoli | — (building block) |
| [10](explenation/10_w_state.md) | W State | 2nd entanglement class, ctrl-`Ry` | — (foundation) |
| [11](explenation/11_chsh.md) | CHSH / Bell Game | quantum advantage as a number | beats classical bound 2 |
| [12](explenation/12_grover.md) | Grover's Search | amplitude amplification | quadratic (`N` → `√N`) |
| [13](explenation/13_qft.md) | Quantum Fourier Transform | the quantum FFT | exponential gate count |
| [14](explenation/14_phase_estimation.md) | Phase Estimation | extract an eigenvalue phase | engine of Shor |
| [15](explenation/15_simon.md) | Simon's Algorithm | period finding | exponential |

## How to run everything
```bash
cd code
for f in [01]*_*.py; do python3 "$f"; done   # runs 01..15 in order
```
Re-running overwrites the JSON + PNG in `result/` and `graph/`. Same seed → same
numbers every time.

## Requirements
- `qiskit` (2.x)
- `matplotlib`, `numpy`

No `qiskit-aer` or IBM Runtime needed — the built-in `StatevectorSampler` is an
ideal, noise-free local simulator.

## Suggested learning path
1. **01–03** build the two pillars: superposition and entanglement.
2. **04** shows those pillars doing real work (teleportation).
3. **05–06** introduce the phase-kick-back + interference template.
4. **07–11** are the practical bridge: entanglement as a channel (superdense),
   real crypto (BB84), reversible arithmetic + the Toffoli gate (adder), a
   second entanglement class (W), and quantum advantage as a measurable number
   (CHSH). These build the gates and intuition Grover needs.
5. **12** is the most practically useful algorithm (search).
6. **13–14** are the reusable machinery (QFT, phase estimation)...
7. **15** ...which combine into period finding — the road to Shor's algorithm.
