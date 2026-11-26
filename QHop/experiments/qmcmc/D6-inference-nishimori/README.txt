D6 - Nishimori transfer test for the Bayesian-inference vertical (B4-04 / B4-03, B6-01, B6-18, K14)
Agent D6, 2026-11-21. Exact, ideal (noiseless) simulation. Machine was heavily overloaded (load 50-66), so scope was cut;
see "NOT RUN".

QUESTION
On a planted posterior sampled at the matched temperature (Nishimori line; Zdeborova & Krzakala arXiv:1511.02476 sec II.7:
no static RSB), is the QeMCMC step advantage small, and does it only appear colder or in first-order windows?

METHOD (own code; harness common/qmc.py not edited; QKern copied from D1)
- d6lib.py: exact symmetrised MH operators. Gap = relaxation gap 1-lambda_2 (primary; same as the lazy-chain gap, so it
  is not distorted by near-periodic single flips at high T). Absolute gaps are also stored (ga_*).
- Quantum: Layden QeMCMC, H_prob = the exact posterior energy vector, alpha = sqrt(n)/std(E), gamma ~ U[.25,.6],
  t ~ U[2,20] (16 stratified draws, seed 0). D = decohered control (dephasing every dt = 0.25). Detailed balance: exact
  for the ideal kernel (real symmetric H -> symmetric Q).
- Classical "best" = max of
  C1 (one cheap proposal per step): local L, uniform U, L+U, and the structured moves when they apply: ghost 2x2
     rectangle flip G (tomography); add/delete + uniform swap S and LD-weighted swap W (genomics; W uses Hastings).
  PT proxy: (1-w) M + w H, with H = independence proposal from pi at beta_h = 0.5 (0.25) x beta_peak (HIGH regime),
     each H draw charged 1/gap_L(beta_h) steps. This is a weak stand-in for a real PT ladder (single hot temperature).
  SW: exact Swendsen-Wang with field (heat-bath cluster sign) for K14. Validated vs Monte Carlo (max err 1.5e-3 at 1e5
     samples), reversible to 1.6e-15.
  An uncharged ORACLE (free exact samples from pi_{beta/2}) beats QeMCMC everywhere (S_oracle 0.02-0.5 in the n=8 runs);
  it is reported but kept out of "best".
- S = gap_Q / gap_best_classical. S_C1 = against C1 only. S_dec = gap_D / best. Q_over_D = gap_Q / gap_D.
- Exp1 planted BPSK: y = A x0 + sigma w, A ~ N(0,1/m) dense (or sparse: 3 nonzeros per row), alpha = m/n
  (alpha 0.5 = CDMA load 2, overloaded), SNR_dB = -10 log10 sigma^2, E = |y-As|^2/(2 sigma^2), beta in {1,2,4,8} x beta_match.
- Exp2 binary tomography 3x3 (n=9): ray sums over rows, columns, diagonals, anti-diagonals (V = 2,3,4); x0 ~ Bern(1/2);
  sigma in {0.25, 0.5, 1}.
- Exp3 fine-mapping, 10 SNPs (blocks of 4,4,2), haplotype genotypes with within-block LD r = 0.8-0.98 (empirical mean
  0.91), N = 1000; g-prior closed-form marginal likelihood (Liang et al. 2008), pi = 1/8, g = 30; all 1024 models.
- Exp4 K14: 3x4 open-grid Ising MRF, J = 1, data term h = 0.5 o / sn^2, sn = 1; beta in {0.5,1,2} x beta_peak (specific heat).

COMMANDS (OMP_NUM_THREADS=1-2)
 python exp1_planted.py --family dense --n 8 --inst 10 --out results/exp1_dense_n8.json
 python exp1_planted.py --family dense --n 10 --alphas A --snrs 0,3,6,10,14 --inst 6 --lean --out results/exp1_dense_n10_aA.json  (A=0.5,1,1.5,2)
 python exp1_planted.py --family sparse --n 8 --alphas 1,2 --snrs 0,6,10,14 --inst 6 --out results/exp1_sparse_n8.json
 python exp2_tomo.py --R 3 --C 3 --views 2,3,4 --sigmas 0.25,0.5,1.0 --inst 6 --lean --out results/exp2_tomo_3x3.json
 python exp3_genomics.py --P 10 --rs 0.8,0.9,0.95,0.98 --gs 30 --inst 6 --out results/exp3_gen_P10.json
 python exp4_mrf.py --inst 6 --out results/exp4_mrf.json
 python analyze.py   -> results/summary_tables.txt, results/exp*_all.csv, plots/*.png
Run times under load: exp1 n8 13 min; exp1 n10 20-42 min per alpha; exp2 6 min; exp3 20 min; exp4 2.5 h.
Seeds are fixed through numpy default_rng tuples in each script.

RESULTS (own simulation, ideal). Median S [IQR]; full tables in results/summary_tables.txt
Exp1 dense, pooled over alpha and SNR:
  n=8 : beta/bm 1: 1.10 [0.68,1.99] | 2: 1.18 | 4: 1.25 | 8: 1.29     (vs C1 only: 1.13 / 1.21 / 1.38 / 1.97)
  n=10: beta/bm 1: 1.31 [0.64,2.75] | 2: 1.35 | 4: 1.51 | 8: 1.65     (vs C1 only: 1.47 / 1.84 / 2.88 / 3.54)
  sparse n=8: 0.91 / 0.81 / 0.73 / 0.63
 Matched beta, by alpha (n=8 -> n=10): a0.5 1.88 -> 3.31 | a1 1.29 -> 1.34 | a1.5 0.78 -> 0.94 | a2 0.87 -> 0.67
 WINDOW S>2: alpha=0.5 (overloaded), SNR >= 3 dB, matched beta: n=10 S = 2.7 (3 dB), 3.8 (6), 5.1 (10), 5.3 (14 dB);
   rising from n=8 (2.1, 3.1, 3.0, 4.6). Q/D = 2.5-7.5, so the effect is coherent, not the dephased-walk component.
   Here the local gap collapses (2.8e-6 at 10 dB, 2e-13 at 14 dB) and the MAP equals x0 in only 0-50% of instances below
   14 dB: a finite-size first-order / hard window. Caveat: "best classical" there is uniform or the weak single-temperature
   PT proxy. Not tested against a real PT ladder, AMP with restarts or population annealing.
 Colder beta = 8, alpha=0.5, n=10: S = 4.3 [3.0,7.3]. For alpha >= 1.5, S <= 1.1 at every beta.
 Nishimori check: at beta=1, mean planted overlap m equals replica overlap q (n=8: 0.657 vs 0.656; n=10: 0.700 vs 0.709;
   sparse 0.738 vs 0.736). Colder, q > m (0.93 vs 0.77 at beta 8). The matched setup is right. The specific-heat peak
   sits BELOW beta_match (median 0.44-0.55), i.e. it marks the collapse onto x0, not a glass transition.
Exp2 tomography 3x3, by views (beta 1 / 8): V2 1.13 / 1.21 (best = local+ghost) | V3 0.98 / 0.63 | V4 0.64 / 0.47.
   No (V, sigma) cell has median S > 2. The largest is V2 at sigma 0.25 with S = 1.45; S against weak baselines there is
   6.3, which the ghost move removes.
Exp3 fine-mapping 10 SNPs: S = 0.33 [0.24,0.54] at beta 1, and 0.33 at beta 8. Q / (local + swap) = 0.46-0.49;
   Q / (local + LD-weighted swap) = 0.48-0.53. S > 2 in 0% of cells. Against weak baselines only: 0.9 (beta 1) to 6.8 (beta 8).
Exp4 K14 control, against exact SW: beta = 0.5 beta_peak: 0.10 | beta_peak (MEDIUM): 0.14 [0.12,0.16] | 2 beta_peak (LOW):
   2.13 against SW (1.9 against SW + local). Control passes: below 1.5 at the usual medium temperature, so the harness is fine.

BREAK-EVEN: every energy here is cheap (t_C ~ 30 ns dense, n <= 100), so S* ~ 1e6 / 7e7 / 3e8 (optimistic / realistic /
pessimistic, BRIEF-screening convention, N_2q ~ 800). The best measured S is ~5. No wall-clock route.

CONCLUSIONS
- Shown by own simulation (ideal): at the matched temperature, the pooled median S is 1.1-1.3 (< 2). For alpha >= 1 it does
  not grow with n (alpha 1.5 and 2 give S < 1). The Nishimori prediction holds for typical loads. It FAILS in the
  overloaded (alpha = 0.5, CDMA load 2) high-SNR window: S 3-5 at n=10, growing with n, with genuine coherence.
- Speculation: that window is the known first-order hard phase of CDMA detection. Whether S survives a tuned PT ladder or
  AMP is open.
- Verdicts:
  B4-04: done. Telecom/inference at typical load = KILL for matched-temperature use.
  B4-03 (overloaded NOMA window): SIMULATE MORE as science only (n = 12-14, against real PT and AMP); no product value.
  B6-01: KILL (local + ghost moves match QeMCMC).
  B6-18: KILL (swap moves beat QeMCMC by ~2-3x).
  K14: control passed (S = 0.14 against SW at medium T).

NOT RUN / LIMITS
 - n=12 for exp1 (started at alpha 0.5 / 2, SNR 10, but killed unfinished because of the machine load). The 3x4
   tomography, 12-SNP genomics and the g / SNR sweeps in exp3 were also not run.
 - No real PT ladder; no noise model; 6-10 instances per cell.
 - Gaps below ~1e-12 are at numerical precision (only local gaps at 14 dB reach that; they are never the best classical).
