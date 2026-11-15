# Certified, Not Superior — paper build

IEEE conference format (`IEEEtran`). This machine has no LaTeX: compile on Overleaf or a TeX install.

```bash
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Upload: `main.tex`, `refs.bib`, `numbers.tex`, `prose.tex`, `tab_*.tex`, `fig1_map.pdf`, `fig2_twin.pdf`.

## Every number is generated

Do not edit `numbers.tex`, `prose.tex` or `tab_record.tex` / `tab_qal.tex` / `tab_roll.tex` / `tab_scan.tex`
by hand. They are written by `../analysis/paper_numbers.py` from the run JSONs in `../runs/`. `tab_audit.tex`
and `main.tex` use only those macros for results.

Rebuild order, from the repo root (no QPU anywhere):

```bash
PY=/home/peter/anaconda3/bin/python3
$PY THESIS/QuantumEvolutionFrontier/analysis/ledger.py                     # hardware numbers -> runs/ledger.json
cd QuantumPhantoms/code
$PY ../../THESIS/QuantumEvolutionFrontier/analysis/classical_cost.py --part all   # exact classical cost + ideals
$PY ../../THESIS/QuantumEvolutionFrontier/analysis/classical_cost.py --part extra
$PY ../../THESIS/QuantumEvolutionFrontier/analysis/qca_scan.py                     # ~1.5 h, guarded cells
for p in roll roll_noise seeds cohort render features; do
  $PY ../../THESIS/QuantumEvolutionFrontier/analysis/ct_twin.py --part $p          # seeds ~2 h, render ~30 min x 8
done
cd ../..
REPLAY_SHOTS=4096 $PY THESIS/QuantumEvolutionFrontier/analysis/teleport_replay.py
$PY THESIS/QuantumEvolutionFrontier/analysis/paper_numbers.py
$PY THESIS/QuantumEvolutionFrontier/analysis/figures.py
```

`runs/surrogate_check.json` and `runs/teleport_ideal_sign.log` were produced by the inline commands recorded in
the session; `paper_numbers.py` reads them.

## Before submission (open items)

- Affiliation, city and e-mail in the author block.
- Hardware experiment E1 (two-setting GHZ witness on the germ register) is not in this version; Section "The road
  from here" states it as the first milestone.
- Verify the bibliography entries against the publishers (all written from memory, not fetched).
- Compile and check the page count (estimate from word count: about 6 pages).
