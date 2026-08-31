# Proof of Concept — Certified-Quantum Artificial Life You Can Poke

Two files, one honest claim: a Darwinian quantum population whose aliveness is
**certified quantum** by an entanglement witness a classical system cannot forge —
and which you can **poke and watch recover**.

| File | Role |
|---|---|
| `classical_life.py` | Best *classical* control: a measure-and-resend Darwinian population running the identical loop. Defines the NULL band the quantum arm must beat. |
| `quantum_life.py` | *Quantum* population on real IBM hardware: entangled GHZ genome, closed-loop selection, a poke, and the entanglement witness `⟨X^⊗W⟩`. |

## The distinguishing observable
The genealogical entanglement witness
```
W = ⟨X^⊗n⟩   (X on every genome qubit at once)
```
→ **+1** for a genuinely entangled GHZ genome, → **0** for any classical
population. That gap is the certificate: it separates quantum aliveness from
classical stochastic dynamics wearing a quantum costume.

## Why the quantum method is better (measured, both on Aer sim)

| | Classical surrogate | Quantum population |
|---|---|---|
| Witness `⟨X^⊗4⟩` | stays in null band `±0.047` (max `0.033`) | `+1.000`, **29/30** generations above band |
| Certifies quantumness | **no** — cannot produce the X-basis correlation | **yes** — witness far above classical null |
| Poke response | flat noise | gen 15 poke → `−0.03` (dips into null) → gen 16 `+1.000` (recovers) |

The classical arm runs the *same* mutate/select/reproduce loop and the *same*
readout — it simply cannot lift the witness off zero, no matter how it
self-organizes. The quantum arm holds it near the ceiling and shows the
poke-and-recover signature. That contrast is the contribution.

## The one honest caveat (do not skip)
This is the **toy DRAFT kill-gate**, not the thesis. On NISQ hardware, readout and
2-qubit error pull the witness down, so the hardware pass condition is "witness
stays above the classical null band", not "witness = 1". Small `W` keeps the GHZ
shallow enough to survive. The full study scales width, adds the criticality
metrics (branching σ≈1, avalanche exponent α≈1.5), inter-run state persistence,
and the yoked-vs-closed-loop adaptation gap — plan:
`../../plans/thesis-5-critical-quantum-life.md`.

## Run
```bash
python classical_life.py                 # classical null baseline
python quantum_life.py                    # quantum population on Aer sim
python quantum_life.py --backend auto     # least-busy real IBM device
python quantum_life.py --backend ibm_fez
```
Deps: `qiskit`, `qiskit-aer`, `numpy`; hardware also needs `qiskit-ibm-runtime` + saved IBM Quantum account.

RUN : (base) peter@home:~/PycharmProjects/Quantum-research/THESIS$ python CriticalQuantumLife/proof_of_concept/quantum_life.py --backend ibm_kingston
backend : ibm_kingston (156 qubits)
quantum population — W=4, 30 generations
gen  witness  note
  0  +0.876  
  1  +0.864  
  2  +0.863  
  3  +0.861  
  4  +0.882  
  5  +0.867  
  6  +0.855  
  7  +0.867  
  8  +0.866  
  9  +0.866  
 10  +0.874  
 11  +0.875  
 12  +0.874  
 13  +0.860  
 14  +0.868  
 15  -0.014  <-- POKE
 16  +0.861  recover
 17  +0.859  recover
 18  +0.876  recover
 19  +0.865  recover
 20  +0.852  recover
 21  +0.891  
 22  +0.881  
 23  +0.868  
 24  +0.858  
 25  +0.866  
 26  +0.867  
 27  +0.858  
 28  +0.866  
 29  +0.870  

classical null band : ±0.047
generations with witness above band : 29/30
post-poke recovery  : gen 15 = -0.014 -> gen 20 = +0.852
=> witness stays above the classical null => aliveness certified QUANTUM;
   poke dips it, selection recovers it — the 'life you can poke' signature.
(base) peter@home:~/PycharmProjects/Quantum-research/THESIS$ python CriticalQuantumLife/proof_of_concept/classical_life.py 
classical surrogate population — W=4, 30 generations
gen  witness  note
  0  +0.017  
  1  +0.006  
  2  +0.013  
  3  -0.021  
  4  -0.004  
  5  -0.014  
  6  -0.033  
  7  -0.030  
  8  +0.003  
  9  +0.018  
 10  +0.001  
 11  +0.024  
 12  -0.014  
 13  -0.027  
 14  +0.020  
 15  -0.018  <-- POKE
 16  -0.014  
 17  +0.014  
 18  -0.007  
 19  -0.018  
 20  -0.026  
 21  -0.002  
 22  +0.005  
 23  +0.011  
 24  -0.004  
 25  +0.015  
 26  +0.004  
 27  +0.004  
 28  +0.015  
 29  -0.007  

null band (|W| < 3/sqrt(shots)) : ±0.047
max |witness| over run          : 0.033
=> classical population stays inside the null band the whole run.
   It CANNOT certify quantum aliveness. quantum_life.py must beat this band.
(base) peter@home:~/PycharmProjects/Quantum-research/THESIS$ 
