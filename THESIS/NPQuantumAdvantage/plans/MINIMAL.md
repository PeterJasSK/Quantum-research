# MINIMAL — Obscure NP Query Advantage

Absolute minimal proof of concept. Pure simulation, no hardware. Proves the headline theorem is demonstrable by oracle-counting on ONE problem.

## Claim to demonstrate
Dürr–Høyer / Grover-minimum solves the optimization version in ~`2^(n/2)` cost-oracle calls vs `2^n` brute force — the quadratic query speedup, shown by counting, before any survive/collapse map.

## Pick ONE problem
**P2 — Numerical Matching with Target Sums.** Reuses the number-partitioning sum-to-target penalty almost verbatim → least new code.

## Minimal pipeline (single file `poc.py`, ~100 lines)
1. **Instance gen** — random small P2 instance, size `n` from 4..14.
2. **Cost oracle** — `cost(assignment) = sum over targets (achieved_sum - target)^2`. Wrap in a call counter.
3. **Brute force** — enumerate all `2^n` assignments, record oracle-call count = `2^n`.
4. **Grover-minimum (simulated by counting, NOT full statevector)** — implement Dürr–Høyer control loop over an *ideal* Grover subroutine whose expected call count is the `~1.3·2^(n/2)` bound; tally oracle calls. (No qubits simulated — just the query-model accounting the theorem lives in.)
5. **Fit** — plot/print oracle calls vs `n` for both; fit exponent. Expect classical slope ≈1.0, quantum ≈0.5 on log2 axis.

## Pass condition
Fitted quantum exponent ≈ 0.5·(classical exponent) across the `n` sweep. That is the theorem, demonstrated.

## Explicitly out of scope for POC
Other 4 problems, best-known-classical baseline survey (the real thesis work), fault-tolerant T-count, QAOA hardware arm, full statevector Grover.

## Deps
`numpy` only. No Qiskit needed for the query-count POC.
