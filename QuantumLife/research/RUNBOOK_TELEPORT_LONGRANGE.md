# RUNBOOK — Teleport-Grown Tree

```
cd QuantumLife/code
```

## Phase 1 — Spectacle (sim, free, pretty long-range trees)

Non-physical preview trees; vary bond-dist/anchors/seed for different shapes.
```
python research_qtree_teleport.py --generations 11 --shots 16384 --seed 100 --repeats 1 --layers 1 --bond-dist 6 --anchors 0  --herald --backend ibm_kingston --name tel_herald_hw

python research_qtree_teleport.py --generations 11 --shots 16384 --seed 100 --repeats 1 --herald --backend ibm_kingston --bond-dist 6 --anchors 0,3,6 --name web_d6

python research_qtree_teleport.py --generations 11 --shots 16384 --seed 100 --repeats 1 --herald --backend ibm_kingston --bond-dist 9 --anchors 0,4,7 --name web_d9

python research_qtree_teleport.py --generations 11 --shots 16384 --seed 100 --repeats 1 --herald --backend ibm_kingston --bond-dist 12 --anchors 0,3,4 --name web_d12
```

> **Register size note (2026-08-17): genome cut 108 → 102 qubits (18 → 17 slots).**
> No clean 108-long SWAP-free line was available on live hardware — marrakesh
> calibration was poor and the other Heron r2 backends were booked out for weeks;
> the longest reliable low-error line was ~106 qubits. 106 is not a multiple of
> `SLOT_BITS=6`, so it cannot hold whole genome slots (it would leave a broken
> 4-bit slot). We therefore dropped the last slot: `N_SLOTS=17`, `N_BITS=102`,
> which fits comfortably inside the ~106 line and keeps the chain **SWAP-free** —
> the whole point of the study. Running the 108-qubit circuit on a 106 line was
> rejected: the transpiler would insert SWAPs (`initial_layout` unpinned when
> `len(qubit_list) != qc.num_qubits`), making distant qubits adjacent through the
> ladder and destroying the "bonded qubits are never physical neighbours →
> crosstalk cannot fake the signal" claim.
>
> **Why the earlier 108-qubit runs are still valid and comparable:**
> - The old `*_seed*_run.json` files are frozen and each embeds its own
>   `genome_spec`; the viewer decodes every run by its own spec, so nothing was
>   retroactively changed.
> - The **headline metric — per-bond `c(d)`** (`bonds[].c_at_d`) — is measured at
>   the exact two bonded angle qubits `qi=si*6, qj=sj*6` and normalised by C0. It
>   is register-length independent, so 102-qubit bonds compare directly to
>   108-qubit bonds at matched `--bond-dist`/`--anchors`.
> - Only the chain-averaged `C(d)/C0/xi` shift slightly (they average over `n-d`
>   pairs); the shape is unchanged, only absolute values move marginally with `n`.
>
> **Comparison rule:** every arm compared head-to-head (teleport / swap / null /
> brickwall) must share the SAME register size. Re-run all four at 102 — do not
> mix a fresh 102 teleport arm against an old 108 brickwall arm. With 17 slots the
> valid slot indices are 0..16, so keep `--anchors + --bond-dist ≤ 16` (e.g.
> `--bond-dist 12 --anchors 0,3` — the old `0,3,5` would drop the (5,17) bond).

## Phase 2 — Research (live hardware, herald on, 1 bond)

Null — classical herald control, must stay c(d)≈0 (proves herald honest).
```
python research_qtree_teleport.py --sim --herald --generations 8 --shots 16384 --seed 100 --repeats 1 --bond-dist 6 --anchors 0 --name tel_herald_null
```
Teleport — the headline arm, heralded long-range bond on hardware.
```
python research_qtree_teleport.py --herald --backend marrakesh --generations 8 --shots 16384 --seed 100 --repeats 1 --layers 1 --bond-dist 6 --anchors 0 --name tel_herald_hw
```
SWAP ladder — same bond, deep honest alternative teleport must beat.
```
python research_qtree_swaplr.py --backend marrakesh --generations 8 --shots 16384 --seed 100 --repeats 1 --layers 1 --bond-dist 6 --anchors 0 --name swap_hw
```
Neighbour chain — reference: reaches d=1, dies by d=36.
```
python research_qtree_brickwall.py --backend marrakesh --generations 8 --shots 16384 --seed 100 --repeats 1 --layers 1 --name bw_hw
```

## Read

`summary.json → per_generation[g].bond_c_at_d_mean` (signal) vs `logical_depth_mean` (cost); teleport wins if c(d) > null at depth ≪ swap. Per-shot survival: `run.json → generations[g].herald_frac`.
