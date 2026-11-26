D8 CONSERVING-MIXER QeMCMC (fixed-composition / Kawasaki sampling)  -- ideas B3-07, B3-09, K15 (C3 nomination N3)
Date 2026-11-21. All numbers: own simulation, ideal (noiseless), exact 924-state matrices unless marked otherwise.

SETUP
 State space: n=12 sites (3x4 periodic square lattice), exactly k=6 occupied -> 924 states (sector built directly).
 Quantum proposal: U=exp(-iHt), H=(1-g) alpha diag(E) + g c H_XY, H_XY = sum_edges (XX+YY)/2 restricted to the sector
   (0/1 hopping between configurations differing by one particle moved along a mixer edge). alpha = sqrt(n)/std_sector(E);
   c = sqrt(n/mean degree of H_XY) so the mixer has the same rms row norm as P1's sum X (degree n). g from grid
   {0.25,...,0.6}, t~U[2,20], m=24 draws, draw seed = instance seed. Temperature-independent proposal (as P1).
   Mixer graphs: grid = 24 NN bonds of the torus; ring = 12-site snake Hamiltonian cycle; complete = all 66 pairs.
 Decohered control: same generator, full Z-dephasing every dt=0.25 (classical kernel |e^{-iH dt}|^2 composed t/dt times).
 Classical (exact, symmetric): nn Kawasaki (random NN bond, swap if unlike); any-pair swap (uniform over the 36 unlike pairs,
   standard canonical MC move); 50/50 mixture; uniform over 924 states. "Best swap" = max(nn, any-pair, mixture);
   "best all" adds uniform (uniform is only competitive because 924 is tiny; its gap ~1/C(n,n/2) at scale).
 Energy families (5 instances each, seeds 0-4; spin form s=2x-1, E = sum_{i<j} J_ij s_i s_j):
   cuau:    AF NN J1=1 + ferro NNN J2 (seed0 -0.5, else U[-0.7,-0.3]), 10% bond noise for seeds>0; frustrated by odd L=3.
   coulomb: screened Coulomb exp(-r/2)/r between +-1 charges (6+6, charge balanced), minimum image on the 3x4 torus;
            seed0 perfect lattice, seeds>0 random site displacements (std 0.15 lattice units).
   sk:      J_ij ~ N(0,1)/sqrt(n) at fixed magnetisation 0, no field (frustrated control).
 Tc = exact canonical specific-heat peak per instance. Regimes: LOW T/Tc=0.3-0.5, MEDIUM 0.9-1.1, HIGH 3-5.
   T/Tc grid 0.3,0.5,0.7,0.9,1.0,1.1,1.5,2,3,5. Exact IATs (E, NN-SRO = unlike-bond fraction, ground-state overlap |q|)
   at T/Tc=0.5,1.1,3 via eigendecomposition of the reversible MH matrix.

COMMANDS (OMP_NUM_THREADS=1, PYTHONPATH=.../qmcmc/common)
 python run_gaps.py <cuau|coulomb|sk> 12 5     -> results/gaps_<fam>_n12.jsonl   (~200-480 s/instance on the loaded box)
 python run_symmetry.py                        -> results/symmetry.json          (~23 min)
 python run_pt.py <fam> 5                      -> results/pt_<fam>.jsonl         (PT R=8, 2e5 rounds, seeds 100+s)
 python run_cz.py                              -> results/cz.json (PARTIAL, see CUT)
 python analyze.py                             -> results/gaps_all_n12.csv, S_table_n12.csv, pt_table.csv,
                                                  summary_n12.txt, plots/gap_vs_T_n12.png, plots/S_vs_T_n12.png
 queue.sh = the sequential queue actually used (<=2 own processes).

RESULTS
Tc (per seed 0-4): cuau 2.96, 2.88, 2.98, 3.16, 3.43 | coulomb 0.495, 0.399, 0.428, 0.438, 0.408 | sk 0.774, 0.680, 0.841,
 0.817, 0.767 (energy units of each family).

S = gap(best quantum mixer)/gap(best swap mixture), median [IQR] over 5 instances (best quantum mixer in brackets):
 family   LOW T/Tc=0.5          MEDIUM T/Tc=1.1        HIGH T/Tc=3
 cuau     10.4 [8.9,10.9] grid   1.72 [1.68,1.93] ring   1.24 (ring; deco_grid 1.7 beats it)
 coulomb  91 [82,106] grid       4.28 [3.78,4.51] grid   1.57 (ring)
 sk       323 [310,374] grid     11.5 [10.1,11.6] grid   2.32 (grid ~= deco 2.24)
 vs best of all incl. uniform: cuau 6.8 / 1.72; coulomb 10.1 / 4.28; sk 9.8 / 5.3 (T/Tc 0.5 / 1.1).
 Complete-graph XY mixer is consistently WORSE than the lattice (grid/ring) XY mixer (cuau 1.1: 0.86x of best swap).
 Decohered control (best deco mixer) vs best swap at 1.1: cuau 1.13, coulomb 1.01, sk 2.15. q/deco at 0.5/1.1/3:
   cuau 6.0/1.5/0.7, coulomb 11.5/4.2/1.6, sk 16.8/5.2/1.2 -> coherence contributes at LOW/MEDIUM only.
 Best classical swap at 1.1 is nn Kawasaki for cuau and coulomb (screened), any-pair for sk.

Versus PT (R=8, T_target..5Tc geometric, any-pair swaps, simulated IAT at target replica; quantum = exact IAT of best
 mixer; ratio = PT IAT / quantum IAT, worst of E, SRO, |q|; median [IQR] over 5 seeds):
   per proposal (PT round x 8):  cuau 0.95 [0.84,0.97] @1.1, 1.47 [1.37,1.53] @0.5 | coulomb 1.60 [1.57,1.72] @1.1,
                                 1.02 [0.66,1.07] @0.5 | sk 1.48 [1.32,1.55] @1.1, 0.93 [0.90,1.62] @0.5
   per PT round (PT counted as 1 step): 0.12-0.20 everywhere (quantum chain 5-8x WORSE).
 Cross-check simulated vs exact IAT (seed 0): energy IAT agrees within ~5-10% (one any-pair case at 0.5 off 2x: finite run).

SYMMETRY / STATIONARITY (cuau and sk seed 0, g=0.425, t=10, ring and complete mixers)
 Exact U: max|U-U^T| <= 1.2e-15, max|Q-Q^T| <= 1.7e-15, |pi P - pi|_inf <= 1.1e-16, stationary TV <= 2e-13. All 30
   exact proposals in the sweep: max|Q-Q^T| <= 1.1e-16.
 2nd-order palindromic Trotter (r=10,30): max|Q-Q^T| <= 5e-15 -> exactly symmetric (machine precision), pi exact.
 Non-palindromic first-order (fixed layer order, or one fixed random "transpiled" gate order): max|Q-Q^T| = 0.015-0.13,
   relative asymmetry (mean|Q-Q^T|/mean Q) 0.3-1.0, |pi P - pi|_inf 2e-4 to 1e-3, stationary TV bias 0.002-0.07 at T/Tc=1.1
   and 0.003-0.17 at 0.5 (shrinks with r). Reversed gate sequence gives exactly Q^T (checked, <=7e-15); the
   forward/reverse 50/50 fix restores symmetry to <=4e-15 and pi exactly (|pi P - pi| <= 1e-16).
 Trotter accuracy: row TV vs exact at t=10 is ~0.5 at r=10 and 0.06-0.11 at r=30 (palindromic) -> need r ~ 3t, i.e.
   r ~ 6-60 for t in [2,20].

CZ COUNT (own transpile, qiskit 2.3.1, FakeMarrakesh heavy-hex, opt level 3, best of 3 seeds; energy RZZ on all CE pairs)
 per palindromic Trotter step: ring XY + CuAu 48 pairs 717 CZ; ring + dense 66 pairs 728; grid 865 / 910; complete+CuAu 975.
 Routing of the NNN/dense ZZ terms dominates (the XY ring alone would be ~36 CZ). Useful r ~30 (t~10) -> ~2.2e4 CZ per
 proposal (ring), F=(1-2e-3)^2.2e4 ~ 1e-19. All-to-all native (Helios-like, analytic): ~130-170 2q gates/step -> ~5e3.
 Break-even (BRIEF-screening convention, t_C ~30 ns any-pair swap): S* = 3e6 / 1e8 / ~1e27 (opt/real/pess, N_2q 2.2e4).

CUT (machine overload, coordinator rule <=2 processes, then finalize order)
 - n=14 (3432 states): not run.
 - FakeNighthawk square-lattice transpile and heavy-hex complete+dense: not run (cz.json is partial).
 - Trotter checks only for seeds 0 of cuau and sk, one (g,t), r in {10,30}; no Trotter-gap sweep.
 - PT with one ladder (R=8 to 5Tc) and one schedule; no ladder tuning (tuned PT would only be stronger).
 - No noisy simulation; no cluster / Wang-Landau baselines.

CONCLUSION
 Shown by own simulation (ideal): conserving XY mixers give an exactly symmetric proposal inside the composition sector
 (exact unitary and palindromic Trotter); non-palindromic compiled orders bias the stationary distribution by up to ~0.07-0.17
 TV, removed exactly (ideal) by forward/reverse randomisation. Gap advantage vs the best swap mixture grows towards LOW T
 and with frustration/density (cuau < coulomb < sk), but at the engineering point T/Tc=1.1 it is 1.7x (CuAu, below the
 C3 kill threshold 2) and 4-12x for dense couplings, while against PT with the same any-pair swaps the quantum chain is
 0.9-1.6x per proposal and 5-8x worse per PT round. Kill rule (S<2 @1.1 AND <1.5x vs PT): met for CuAu-type alloys (B3-07,
 K15 binary CE) -> KILL. Coulomb/SK: not killed by the literal rule (S=4.3/11.5 @1.1) but confirm rule fails (vs PT 1.0x
 at 0.5 for coulomb) -> QUANTUM-INSPIRED ONLY (B3-09): no wall-clock case (S* >= 3e6 vs measured <= 1.6x vs PT,
 ~2e4 CZ per proposal on heavy-hex).
 Speculation: the lattice-XY advantage at LOW T is a small-n (924-state) effect whose scaling vs n is untested here.
