D1 TEMPERATURE MAP - exact spectral gap vs beta for every proposal type (QeMCMC applied review, Wave 4)
Date 2026-11-21. All numbers: own simulation, ideal (noiseless), exact linear algebra on the full 2^n space,
unless marked "sampled". Plain text. Full numeric summary: results/summary.txt.

WHAT WAS RUN (commands, from this folder, with OMP/OPENBLAS/MKL_NUM_THREADS=2)
  python validate.py                       -> results/validate.json, logs/validate.log
  python run_family.py FAMILY INSTANCE     -> results/fam_<FAMILY>_i<k>.json  (FAMILY sk10, ea33, fe33, fe34, ea34)
  python run_scaling.py N INSTANCE         -> results/scal_n<N>_i<k>.json
  python run_sk_clusters.py exact6         -> results/sk_clusters_exact_n6.json
  python run_sk_clusters.py s10 INSTANCE   (sampled SK n=10 clusters; NOT completed, see CUTS)
  python analyze.py                        -> results/summary.txt, gaps_long.csv, S_table.csv, scaling_fits.csv, plots/*.png
  run_queue.sh + logs/jobs.txt = the job list actually used (2 workers).
Code: d1lib.py (library), run_family.py, run_scaling.py, run_sk_clusters.py, analyze.py, validate.py. common/qmc.py not edited.

INSTANCES AND SEEDS
  SK: qmc.sk_instance(n, 1000*n+i), J,h ~ N(0,1) unscaled (T_c ~ sqrt(n)). Gap-vs-beta at n=10, i=0..9.
  EA: qmc.ea_instance(3,3, 500+i, dist="pm") 2D +-J, periodic, zero field, i=0..5 (6 instances).
  Ferromagnet: qmc.ferro_instance(3,3) and (3,4), periodic, J=1, zero field (one instance each; no disorder -> no IQR).
  Quantum draws: layden_draws(seed=i): gamma~U[0.25,0.6] stratified at 4 strata midpoints x 4 jittered t-strata in
  U[2,20] (16 draws; same expectation as Layden's per-step draws, lower variance). Checked against i.i.d. draw_params
  (validate.log): high-T gaps agree within 1%, low-T within ~5-30% (finite-draw variance of a 16-draw estimate).
  alpha = sqrt(n)/std(E) (harness convention).

PROPOSALS (all detailed balance verified: symmetric Q -> Metropolis exact; SW/Wolff reversible by construction,
checked numerically: row sums 1e-15, stationarity 1e-15, symmetrised-operator asymmetry < 2e-16, validate.log)
  uniform; single-spin local; best classical mixture = best per beta of local+uniform weights {0..1} and, for zero-field
  families, local+global-flip(+uniform); Swendsen-Wang and Wolff EXACT transition matrices (lattices; SK n=6 via ghost spin
  for the field, Z2-lumped), bond activation p=1-exp(-2 beta |J|) on satisfied bonds, computed by an Edwards-Sokal
  factorisation over all 2^m bond subsets (m<=21 here); exact vs Monte-Carlo agree to <1e-3 (validate.log);
  QeMCMC Layden (above); QeMCMC tuned = best per beta of 32 cells (gamma in {.1,.2,.294,.381,.469,.556,.7,.85} x
  t-window in {[.3,1.5],[1.5,6],[6,24],[24,96]}, 3 log-stratified t each) plus 4 Layden-gamma bands = 36 candidates;
  decohered control = same generator with full Z-dephasing every dt=0.25 (Layden draws; and best-of decohered cells for
  n<=10, 16 cells); coarse-grained P2-style: random cyclic block of k consecutive spins chosen state-independently each step
  (the symmetric single-group variant), frozen rest as effective field, Layden draws inside the group: k=3,5 (n=10),
  k=3 (n=9), k=3,4,6 (n=12). Gap = absolute spectral gap 1 - max|lambda_2| (P1 convention).
  Fe34 tuned used a reduced grid (4 gammas x 3 windows x 2 t) and 9 betas (machine overload).

REGIMES (per instance; beta_c = specific-heat peak of the exact C(beta))
  HIGH beta <= 0.5 beta_c; MEDIUM 0.5 beta_c < beta <= 2 beta_c; LOW beta > 2 beta_c. Grid beta/beta_c = 10^(-1..1), 13 pts.
  beta_c: SK n=10 median 0.411 [0.323-0.546]; EA 3x3 0.645 [0.554-0.951]; ferro 3x3 0.403; ferro 3x4 0.409.
  Local-gap collapse (gap < 10% of its maximum): SK 0.360, EA 0.512, ferro 3x3 0.359 -> consistent with C-peak placement.

RESULTS: S = gap ratio, geometric mean over the regime's betas per instance, median [IQR] over instances
  SK n=10 (10 inst.)          HIGH                 MEDIUM               LOW
   Layden / local             2.07 [1.92,2.47]     8.5 [4.6,12.8]       4.9e5 [1.9e3,2.5e6]
   Layden / uniform           1.26 [1.13,1.34]     7.8 [6.8,8.5]        27 [18,30]
   Layden / best mix          0.90 [0.81,0.96]     3.0 [2.3,3.4]        9.9 [8.7,18.6]
   tuned  / best mix          1.27 [1.19,1.33]     3.6 [2.8,4.1]        15 [13,25]
   decohered / best mix       0.86                 0.65                 0.44
   Layden / decohered         1.04                 4.5                  23
   SK n=6 exact incl. SW/Wolff (10 inst.): Layden/best classical 0.26 [0.24,0.28] | 0.46 [0.31,0.86] | 1.8 [1.7,3.1];
     tuned/best classical 0.45 | 0.66 [0.42,1.04] | 2.6 [2.1,4.2]. SW beats best mix 2.1x HIGH, 1.5x MEDIUM, dies LOW.
  EA +-J 3x3 (6 inst.)
   Layden / local             1.78                 8.0                  1.6e6
   Layden / uniform           0.88                 3.0                  4.2
   Layden / best mix          0.72                 1.00                 1.21 [1.02,1.31]
   Layden / best incl SW,Wolff 0.22 [0.22,0.23]    0.42 [0.36,0.61]     1.21
   tuned  / best incl SW,Wolff 0.35                0.57 [0.48,0.84]     1.65 [1.49,1.72]
   best classical: SW at HIGH, Wolff/SW/mix at MEDIUM, mixture at LOW (SW/Wolff gap ~1e-5 x mix at LOW).
  Ferromagnet 3x4 (1 inst.) / 3x3 (1 inst.)
   Layden / best incl SW      0.11 / 0.12          0.026 / 0.036        0.024 / 0.034
   tuned  / best incl SW      0.19 / 0.26          0.031 / 0.059        0.022 / 0.063
   SW / best mix              4.3 / 3.3            13.5 / 8.1           41 / 5.4   (SW is best everywhere)
  Coarse-grained (P2 single group): always below best classical: SK k=3 0.31/0.37/0.005, k=5 0.53/0.75/0.024
   (HIGH/MED/LOW); EA k=3 0.10/0.06/2e-6; ferro 3x4 k=3,4,6 <= 0.11 HIGH, <=0.005 MEDIUM, ~0 LOW (trapped in Z2 mode).
  Decohered control is >= the coherent proposal only at HIGH T on lattices (ferro: Layden/decohered 0.5-0.6); at MEDIUM
  and LOW coherence is worth 3-5x (MED) and 20-400x (LOW) over its own decohered kernel, but not over SW on the ferro.
  Note: Wolff's absolute gap -> 0 at LOW on the ferro because it deterministically flips the whole lattice (period 2);
  this is an artefact of the absolute-gap convention, SW (flip prob 1/2) is the relevant cluster number there.

SK SCALING gap ~ 2^(-k n), n = 6..11 (10 inst. for n<=10, 5 at n=11), 95% bootstrap CI over instances
                    HIGH (0.5 bc)          MEDIUM (1 bc)          LOW (3 bc)
   local            0.25 [0.18,0.31]       0.36 [0.21,0.50]       0.79 [0.18,1.37]
   uniform          0.53 [0.43,0.63]       0.79 [0.67,0.90]       0.97 [0.88,1.05]
   best mix         0.27 [0.22,0.33]       0.46 [0.39,0.53]       0.82 [0.69,0.95]
   Layden QeMCMC    0.13 [0.09,0.17]       0.24 [0.16,0.30]       0.35 [0.24,0.46]
   tuned QeMCMC     0.19 [0.15,0.22]       0.25 [0.19,0.31]       0.30 [0.21,0.39]
   CG k=ceil(sqrt n) 0.16 [0.10,0.21]      0.32 [0.20,0.44]       0.95 [0.35,1.51]
  Trustworthiness: LOW (uniform 0.97, Layden 0.35) roughly reproduces P1 (0.95 / 0.26). Elsewhere NOT trustworthy:
  R^2 0.1-0.7, split fits n6-9 vs n9-11 differ by up to 4x (e.g. tuned MEDIUM 0.33 -> 0.08, CG HIGH 0.29 -> 0.02), and
  at HIGH/MEDIUM the gaps are O(0.01-0.5), i.e. not yet in an asymptotic exponential regime. Treat HIGH/MEDIUM k as
  descriptive of n<=11 only.

COMPARISON WITH BREAK-EVEN S* (BRIEF-screening convention)
  Cheap dense Ising (t_C ~30 ns): S* ~ 1e6 (D-Wave 0.03 s) / 1e8 (IBM 3 s) / 5e8 (pessimistic, F~0.2).
  Sparse lattice (t_C ~0.15 ns/flip CPU): S* ~ 2e8 / 2e10 / 1e11 (own arithmetic, same convention).
  Largest measured S vs best classical: ~10-25x (SK LOW, n=10), ~1.2-1.7x (EA LOW), <1 at HIGH and MEDIUM everywhere
  once SW/Wolff are included (SK n=6 exact, EA, ferro). Gap to S*: 4-10 orders of magnitude. No wall-clock case here.
  Quantum-inspired fact: every quantum and CG kernel here was computed classically and exactly (n=10: seconds; n=12:
  ~20 s per eigh, ~6 s per evolution time). At these n a classical emulator precomputes Q and samples a row per step in
  ~1 us, so even the LOW-T step advantage is realisable classically at no hardware cost (QUANTUM-INSPIRED ONLY at n<=12).
  Tuning favours quantum: the tuned kernel picks the best of 36 (gamma,t) candidates per beta using the exact gap
  (an oracle unavailable in practice); classical mixtures get only ~10 weights. Tuning gains are modest (1.2-1.6x over
  Layden) and longest windows (t 6-96) win on SK, t 1.5-6 on EA.

CUTS (machine overloaded, coordinator instructions to cap at 2 processes and then finalize)
  - EA +-J 3x4 (n=12): all 5 instances CUT (runs killed after ~3 CPU-h each without finishing). EA family = 3x3 only;
    2x5 not run.
  - SK scaling n=12: CUT (fits use n=6..11).
  - SK n=10 sampled SW/Wolff (2e4 moves/state + bootstrap): CUT; SK cluster evidence = EXACT n=6 (ghost spin) only.
    SK n=10 "best classical" in the table is therefore the best local/uniform mixture (no SW/Wolff); n=6 shows SW/Wolff
    beat that mixture by 1.5-2x at HIGH/MEDIUM and are useless at LOW (percolating clusters, gap ~1e-4 -> 0).
  - EA 3x3: 6 instances instead of 10. Ferro: single instance per size (no disorder).
  - Ferro 3x4 used a reduced tuning grid and 9 betas; no decohered-tuned at n=12.
  - The SK percolation plot (largest SW cluster fraction) needs the sampled run, so plots/sk_cluster_moves.png has the
    n=6 exact panel only.

PLOTS
  plots/gap_vs_beta_all_families.png   gap vs beta/beta_c, median over instances, all proposals, MEDIUM shaded
  plots/S_vs_beta_all_families.png     S (Layden, tuned, decohered vs best classical / best mix), median + IQR
  plots/sk_scaling_k_vs_regime.png     log2 gap vs n per regime, fitted k with 95% CI vs regime
  plots/sk_cluster_moves.png           SK n=6 exact SW/Wolff vs other proposals
DATA: results/gaps_long.csv (every family/instance/beta/proposal gap), S_table.csv, scaling_fits.csv, *.json raw.

CONCLUSION (shown by own simulation, ideal; n<=12, small-size caveat applies to everything)
  HIGH T: no quantum step advantage against the best classical kernel in any family (S 0.1-0.45 once SW/Wolff are
  included; even vs simple mixtures S ~0.9 Layden, 1.3 tuned on SK); decohered control is as good or better on lattices.
  MEDIUM T (around the C peak): on SK the coherent proposal beats local/uniform mixtures by ~3-4x, but exact n=6 SW/Wolff
  already beat Layden (S 0.46); on 2D EA S = 0.4-0.6 vs Wolff/SW and on the 2D ferromagnet S ~ 0.03 vs SW. MEDIUM T is
  cluster-move territory, not QeMCMC territory. The only regime with S>1 vs the best classical is LOW T (SK ~10-25x at
  n=10, EA ~1.2-1.7x), still 4-10 orders below S* and classically emulable at these n.
  Speculation: none of the MEDIUM/HIGH results suggests the ordering would flip at larger n (k fits at HIGH/MEDIUM are
  unreliable, so this is not shown).
