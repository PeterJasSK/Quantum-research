D9  V24 mask library (state-independent quantum flip masks)  --  own simulation, ideal (noiseless), exact matrices
Date 2026-11-21. Agent D9. Folder QHop/experiments/qmcmc/D9-mask-library/

QUESTION
Is V24 real, and is it quantum or quantum-inspired? Move s -> s XOR m, m drawn from a mask law M that does not
depend on s, Metropolis accept. Q(s'|s) = M(s XOR s') = Q(s|s') -> symmetric -> exact (any M, including a finite
fixed library reused forever). Checked numerically: stationarity and detailed-balance error < 3e-17 (n=6, L=32).

WHAT WAS RUN (exactly)
  export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
  python d9_run.py sk N SEED          N in {6,8,10}, SEED 1..10           (full set)
  python d9_run.py ea 12 SEED --lite  SEED 1..3 (2D EA 3x4 periodic, Gaussian J, h=0)
  python d9_libcost.py                (classical library build times)
  python d9_analyze.py                (tables, k fits, plots)
  Scripts: d9lib.py (laws, libraries, gaps), d9_run.py (one instance), d9_analyze.py, d9_libcost.py,
  run_small_a.sh / run_small_b.sh / run_n12.sh (queues). qmc.py used unmodified.
Parameters: SK J,h ~ N(0,1) unscaled (qmc.sk_instance(n, seed)). Quantum proposal = P1 Layden: 16 draws,
  gamma ~ U[0.25,0.6] snapped to a 4-point grid {0.25,0.367,0.483,0.6} (eigh caching), t ~ U[2,20],
  draw seed = instance seed. Decohered control: same draws, full Z dephasing every dt=0.25.
  Betas SK: 0.1 (HIGH), 0.3, 0.5, beta_c (MEDIUM), 1, 3 (LOW). EA: beta_c, 1, 3.
  beta_c = specific-heat peak on a 41-point geomspace(0.05,5) grid, per instance:
    SK n=6 0.56 [0.35,0.79], n=8 0.50 [0.32,0.79], n=10 0.45 [0.25,0.79]; EA 3x4 1.00 [0.71,1.12] (median [min,max]).
  Local-gap collapse curve stored per instance (local_gap in raw json, n<=10); local gap at n=10 drops from 8e-2
  (beta 0.1) to 1.8e-2 (0.3) and 7e-4 (1), so MEDIUM = 0.3..0.5 and LOW >= 1 are consistent with the C peak.
  Gap = absolute spectral gap 1 - max_{k>=2} |lambda_k| (P1 / qmc convention); dense eigvalsh n<=10, deflated
  Lanczos (eigsh) n=12. Zero mask dropped from every law (renormalised), same for all laws.
Mask laws (all state-independent, all exact):
  qFull_P1  reference: full state-dependent P1 QeMCMC (latency mode, NOT a library)
  qA_unifref (a) M(m) = mean over uniform r of Q(r XOR m | r)              [the V24 library law, non-circular]
  qC_piref  (c) same with r ~ pi_beta                                     [CIRCULAR: needs an equilibrated donor]
  qD_decoh  (d) (a) built from the decohered kernel                        [mechanism check]
  cE_DEpi   (e) differential evolution r1 XOR r2, r1,r2 ~ pi_beta exact   [CIRCULAR, ideal population]
  cF_basin  (f) XOR of two greedy-descent local minima from uniform random starts (exact basin weights)
  cG_perc   (g) state-independent bond percolation p_ij = 1-exp(-2 beta |J_ij|), flip cluster of random site
              (law estimated from 65,536 draws)
  cH_wtmatch (h) Hamming weight distribution of (a), uniformly random positions
  uniform, local (i)
  Libraries: L in {32,128,1024,8192} iid masks from (a),(e),(f),(g),(h), fixed seeds, Q = empirical frequencies.
  Mixtures: 50% single-spin local + 50% mask law, for every law and library (EA: infinite and L=1024 only).
Run times: SK n=6 ~10 s, n=8 ~40-100 s, n=10 ~10-15 min, EA n=12 1-2 h per instance (machine load 50-70).

RESULTS (all: shown by own simulation, ideal; n <= 10 for SK, so k fits are 3-point fits, weak evidence)
Raw: raw/*.json, results/gaps.csv; tables results/summary.txt, kfits.csv, S_table.csv, S_per_instance.csv,
  libcost.txt; plots plots/gap_vs_beta_sk.png, k_vs_law_sk.png, S_vs_L_sk.png.

k (gap ~ 2^-kn, SK n=6..10, median of 10 instances, 95% bootstrap CI), infinite library, pure mask moves:
  beta     qFull   qA(lib)  qC(pi,circ) qD(decoh) cE(DE,circ) cG(perc)  cH(wt)   uniform  local
  0.1      0.06    0.31     0.30        0.25      0.35        0.22      0.33     0.38     0.30
  0.3      0.21    0.67     0.51        0.55      0.47        0.97      0.68     0.78     0.49
  beta_c   0.26    0.63     0.42        0.58      0.26        1.20      0.58     0.78     0.41
  1        0.25    0.82     0.47        0.83      0.79        reducible 0.72     1.00     0.99
  3        0.22    0.81     0.50        0.94      2.36        reducible 0.79     1.03     2.69
  CI widths ~ +-0.15-0.25. cF pure is reducible (few minima -> masks span a subspace); it only works mixed.
  50% local mixtures: k qA 0.23/0.48/0.46/0.64/0.81 (beta 0.1/0.3/bc/1/3) vs cF_basin mix 0.08/0.24/0.19/0.23/0.27.
Fraction of the full QeMCMC gap kept by the library qA: beta=1: 0.58 (n=6), 0.30 (n=8), 0.14 (n=10);
  beta_c: 0.78/0.43/0.22; EA n=12: 0.13-0.27. The library gain decays with n: k_qA (0.6-0.8) sits much closer
  to uniform (0.8-1.0) than to full QeMCMC (0.21-0.28).

S = gap(qA library)/gap(best classical library at equal L, incl. uniform/local), median [IQR], SK n=10:
  pure masks, non-circular classical set (f,g,h,uniform,local):
    HIGH 0.1:    L=1024 0.77, L=8192 0.79, inf 0.79 (winner: percolation)
    MEDIUM 0.3:  1.03 / 1.01 / 1.03 (local);   beta_c: 1.04 / 1.08 / 1.10 (weight-matched)
    LOW 1:       1.04 / 1.18 / 1.24 (weight-matched);   3: 1.03 / 1.11 / 1.31 (weight-matched)
  pure, incl. circular DE: MEDIUM 0.29-0.50 (DE wins), LOW same as above.
  50% local mixtures (the practical form): HIGH 0.94, MEDIUM 0.54-0.77, LOW 0.08-0.23, winner basin-difference.
  EA 3x4 (3 instances): pure vs non-circular 1.3-1.6x (weight-matched / percolation); mixtures 0.05-0.32
    (basin-difference wins); pure vs circular DE 0.3-1.0 at MEDIUM.
  Classical basin-difference library + local reaches 0.72-0.83 of the FULL latency-mode QeMCMC gap at SK n=10
  (EA n=12: 0.76-1.14), with k 0.19-0.27 vs qFull 0.21-0.28.
Effect of L: L=32/128 lose badly at LOW (masks too few: chain near-reducible, S ~ 0-0.3); L >= 1024 is within
  ~10% of the infinite law at n<=10 (note L=1024 = 2^10, so this says nothing about L needed at large n).
Decohered control gap(qA)/gap(qD): HIGH/MEDIUM 0.8-1.2 (no coherence effect), LOW 1.5-2.8x. So interference
  shapes the mask law at LOW T, but the weight-matched random masks (h) already match qA there (S 1.1-1.3):
  the quantum gain in the library is "right Hamming weight", not "right positions".
Circular qC (refs ~ pi) vs DE: MEDIUM 0.75-1.2 (DE equal or better); LOW 7x to 1e7x because DE pairs from a
  concentrated pi give mostly trivial masks. Both need an equilibrated population (circular on hard instances).

Library cost (own calculation, results/libcost.txt): quantum L=8192 = 2.0-7.0 s QPU (0.25-0.85 ms/circuit,
  A4 throughput) + 2-3 s job overhead, ~$1.6-11. Classical n=12, L=8192: basin-difference 0.6 s, percolation
  0.4 s numpy on this loaded laptop; weight-matched trivial; DE ~0.06 s C-estimate if PT already mixes.

DECISION (rules from the D9 task)
  Classical library within 1.5x of the quantum library at equal L in every regime (weight-matched or percolation
  for pure masks; basin-difference beats it 1.3-12x once local moves are mixed in) -> not quantum.
  k_qA moves toward the uniform exponent: library keeps 58% -> 14% of the full QeMCMC gap from n=6 to n=10 at beta=1.
  VERDICT: KILL as a quantum method (uniform-reference library). The cost-model change is real but buys a mask law
  that a classical Hamming-weight sampler reproduces. The circular r ~ pi version (qC) keeps more (k ~0.45) but
  needs an equilibrated donor and loses to classical DE at MEDIUM T. Side finding (own simulation): a classical
  basin-difference mask library mixed with local moves is a strong state-independent proposal (k ~0.2 at n<=10),
  worth a classical follow-up, unrelated to quantum hardware.

CUT / NOT RUN (machine overloaded, coordinator asked to finalise)
  SK n=12: not run (no results), so k fits use n=6,8,10 only. EA 3x4: 3 instances, not 5; EA run --lite
  (no decohered law, L in {32 (qA only),128,1024,8192}, mixtures for infinite and L=1024 only). Decohered control
  only n<=10. DE uses exact pi samples (idealised population), not a real PT run. No noise model.
  Reasoned only (not run): large-n behaviour, any wall-clock claim.
