# RUNLOG — verifying the star (P4 Kernel of a Digraph)

How to reproduce and stress-test the borderline verdict for **P4 Kernel of a Digraph**,
the one problem in the map that sits *on* the √2 line. Run everything from the project
root `THESIS/NPQuantumAdvantage/`.

- **Deps:** `python≥3.11`, `numpy`, `qiskit`, `qiskit-aer` (statevector demo only). No
  hardware account needed — the headline is query-count.
- **What "the star" claims:** best-known-classical exponent `c ≈ 0.5`, i.e. the kernel
  problem's exact solver runs at almost exactly Grover's `2^{n/2}` — so the quadratic
  query advantage neither cleanly survives nor cleanly collapses. **The seed sweep
  (Step 4) is the real result: `c` straddles 0.5.** The single ledger row (seed 7) is
  one sample of a borderline point, not a clean survivor.

---

## Step 0 — the theorem axis (undeniable part)
```
python -m problems.p4_kernel_digraph.classical_bruteforce --n 10 --seed 7
python -m problems.p4_kernel_digraph.quantum_grover        --n 10 --seed 7
```
Expect: classical `verifier calls == 2^n == 1024` (exact); quantum
`Grover/DH oracle calls ≈ 41.6 (~1.3·√|S|)`, `theorem-axis slope ≈ 0.500`. This is the
BBBV-optimal quadratic **query** speedup — true for every problem, proven by counting.

## Step 1 — the hunt (the verdict axis)
```
python -m problems.p4_kernel_digraph.best_classical --seed 7 --no-emit
```
Expected output (seed 7):
```
  n          |S|        brute   grover(DH)    hunt work
  6           64           64         10.4           50
  8          256          256         20.8          154
 10         1024         1024         41.6          230
 12         4096         4096         83.2          463
 14        16384        16384        166.4         1140

theorem axis : classical slope 1.0 (R²=1.0) | quantum slope 0.5 (R²=1.0)
verdict axis : best-classical c = 0.531  (√2 line at 0.5, margin +0.031)
VERDICT      : SURVIVES  mechanism=None  [measured — branch-and-reduce exact exponent vs the √2 line]
```
`c` is the fitted slope of `log2(hunt work)` vs `n` — the exponent of the exact
branch-on-vertex kernel solver's recursion-node count. `0.531 > 0.5` ⇒ SURVIVES *by a
hair*. `--no-emit` fits + classifies without touching the ledger.

## Step 2 — correctness cross-check (the solver is exact)
The branch-and-bound must return the true minimum violation. Compare against brute force:
```
python - <<'PY'
from problems.p4_kernel_digraph import instance as m
from problems.p4_kernel_digraph.best_classical import algorithm
from framework.bruteforce import brute_force_min
from framework.oracle import OracleCounter
for n in [6, 8, 10, 12]:
    inst = m.generate(n, 7); c = OracleCounter()
    _, opt, _ = brute_force_min(m.enumerate(n), lambda x: m.cost(x, inst), c)
    best, nodes = algorithm(inst)
    print(f"n={n} brute_opt={opt} brancher_min={best} match={opt==best} nodes={nodes}")
PY
```
Expected: `match=True` for every `n` (optimum `0` — a kernel exists on these seeds). If
`match` is ever `False` the fitted `c` is meaningless — the solver is not exact.

## Step 3 — Grover actually works here (feasibility, not the claim)
```
python -m problems.p4_kernel_digraph.quantum_grover --n 8 --seed 7 --statevector
```
Expect `marked-state probability ≈ 1.0` vs `uniform floor = 0.004`. Grover amplifies the
kernel state — it *works*; the map question is only whether it *beats the best classical
method*, which is Step 4.

## Step 4 — the real finding: `c` straddles the √2 line
One seed is a single sample. Sweep seeds and watch the verdict flip:
```
for s in 1 3 7 11 42; do
  python -m problems.p4_kernel_digraph.best_classical --seed $s --no-emit 2>/dev/null \
    | grep "verdict axis" | sed "s/^/seed $s: /"
done
```
Observed:
```
seed 1 : best-classical c = 0.453  (margin -0.047)   COLLAPSES
seed 3 : best-classical c = 0.455  (margin -0.045)   COLLAPSES
seed 7 : best-classical c = 0.531  (margin +0.031)   SURVIVES
seed 11: best-classical c = 0.437  (margin -0.063)   COLLAPSES
seed 42: best-classical c = 0.564  (margin +0.064)   SURVIVES
```
**Interpretation (the honest headline):** `c` ranges ≈ **0.44–0.56 around 0.5**. P4 does
not sit cleanly on either side — the independence constraint (pulls `c → 0.288`,
collapse) and the domination/absorption constraint (pulls `c → 0.598`, survive) very
nearly cancel, so the kernel problem lands **on the √2 line**. The seed-7 ledger row reads
SURVIVES with a +0.031 margin, but that margin is inside the seed-to-seed spread — so the
defensible verdict for the map is **borderline / on-the-line**, not a robust survivor.
3-SAT (`c = 1.0`) remains the one clean reference survivor.

## Step 5 — re-emit the ledger row + re-render the map (optional)
```
python -m problems.p4_kernel_digraph.best_classical --seed 7        # writes the row
python -c "from framework.ledger import load,validate,render_markdown; \
from framework import map_figure; l=load(); validate(l); render_markdown(l); \
map_figure.render('research_runs/ledger.json', out='research_runs/map'); print('map re-rendered')"
```
`validate` must pass; `research_runs/ledger.md` + `map.{png,svg}` update.

---

### Caveats a reviewer should note
- `c` is an **empirical** base-fit of a hand-rolled branch-and-reduce solver (OQ-3: no
  drop-in library exact kernel solver was available). A stronger measure-and-conquer
  analysis could shift the exponent — most likely *downward* (toward collapse), since
  better pruning lowers the node-count base.
- Small `n` (6–14): the fit is a finite-size slope, not an asymptotic proof. The claim is
  "sits on the line at these sizes," consistent with the cited asymptotic anchors (indep
  set `2^{0.288n}`, dominating set `2^{0.598n}`).
- The verdict is **measured, not assumed** — that is the point of the star. Report it with
  its margin and the seed spread, never as a clean survivor.
