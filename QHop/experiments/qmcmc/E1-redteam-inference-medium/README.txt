E1 RED TEAM - inference window (D6 claim A) and MEDIUM-T cluster moves (D1 claim B)
Agent E1, 2026-11-21. Exact, ideal (noiseless) linear algebra on the full 2^n space (or K*2^n for tempering).
All numbers are own simulation (ideal) unless marked speculation. Gap = relaxation gap 1-lambda_2 for claim A
(D6 convention), absolute gap 1-max|lambda_k| for claim B (D1 convention). Machine shared (load 13-15), so runs were cut;
see NOT RUN.

FILES
 e1lib.py      library: extra proposals, simulated tempering (ST) operator + exact target IAT, overlap distribution,
               basin masses, EXACT Swendsen-Wang / Wolff for dense graphs with field (ghost spin) via a vertex-subset DP
 claimA.py     claim A attack (reuses D6 exp1_planted.instance, d6lib.QKern, layden_draws(0): same instances and quantum kernel)
 claimB.py     claim B attack (reuses D1 sk_instance seeds 1000n+i, d1lib.QKern, layden_draws(inst), D1 tuning windows)
 claimB_mix.py classical side of B strengthened with SW/Wolff + local/uniform mixtures
 analyze.py    -> results/summary.txt, results/claimA_cells.csv, results/claimB_rows.csv
 results/claimA_n8.json, claimA_n10.json, claimA_n12.json, claimB_n{6,8,9,10,11}.json, claimB_mix_n*.json,
 results/claimB_mix_summary.txt; logs/*.log

COMMANDS (from this folder, OMP/OPENBLAS/MKL_NUM_THREADS=2)
 python claimA.py --n 8 --inst 10 --snrs 3,6,10,14 --betas 0.5,0.71,1,1.41,2,4 --stbetas 0.5,1,2 --iat --out results/claimA_n8.json   (7 min)
 python claimA.py --n 10 --inst 6 --snrs 3,6,10,14 --betas 0.5,1,2 --stbetas 1 --out results/claimA_n10.json   (killed after inst 0-2, 11 min)
 python claimA.py --n 12 --inst 2 --snrs 10 --betas 1 --stbetas 99 --lean --out results/claimA_n12.json
 python claimB.py 6 10 tune ; claimB.py 8 10 tune ; claimB.py 9 10 ; claimB.py 10 10 tune (killed after inst 0-5) ;
 python claimB.py 11 5 (killed after inst 0-2) ; python claimB_mix.py N for N=6,8,9,10,11 ; python analyze.py
Validation: my code reproduces D6 exactly (n=8 inst 0, 10 dB, matched: g_Q 0.021667, g_U 0.006073, S 3.568 = D6 JSON) and
D1 exactly (n=6 exact SW, Wolff and Layden gaps equal D1's ghost-spin Edwards-Sokal numbers to 4 decimals, 3 instances x 3 betas).
Exact SW/Wolff kernels: row sums 1 to 6e-15, symmetrised-operator asymmetry <= 1.2e-15 (reversible).

=====================================================================================================================
CLAIM A: "QeMCMC beats the best classical gap in the overloaded CDMA window alpha=0.5, SNR>=3 dB, S 2.7-5.3 at n=10"
=====================================================================================================================
STRONGEST ATTACK. Same instances (D6 seeds), same quantum kernel, matched beta, plus classical kernels D6 did not have
(all exact, detailed balance by construction - symmetric proposals + Metropolis, or computable independence proposals
+ Hastings; mixtures of reversible kernels with fixed weights):
 PTmulti  local + independence draws from pi at beta_h in {0.5,0.25,0.1} x beta, each hot draw CHARGED 1/gap of the best
          of L/U/LU at beta_h (cost of producing it), weights 0.5/0.2.
 ST       simulated tempering with EXACT log Z weights, tuned ladder (K in {3,4,6,8} x beta_min/beta in {.3,.1,.03}),
          local moves per level (+uniform at the hottest), charged gap/K. At n=8 the exact worst-case target IAT was
          computed: it is 0.33 [0.13,0.72] of the charged bound, so gap/K is pessimistic for ST by ~3x (still loses).
 L+Pw     single flips + pair flips (i,j) chosen with weight |G_ij|, G = A^T A (strongly (anti)correlated columns);
          L+Pw+U adds uniform; L+HM(rho) random multi-flip masks with P(mask) ~ rho^|mask|.
 MF       independence proposal = mixture of product measures at naive-MF / TAP fixed points (2n random starts),
          clipped magnetisations; exact q(s) -> Hastings. (AMP-style guided proposal.)
 MODE     mode-jumping independence proposal: mixture of product measures (flip prob 0.05/0.15) centred on the local
          minima found by 2n steepest-descent runs from random starts (realisable; found 2-8 of the 3-10 minima),
          weights exp(-beta E(min)); mixed with local moves 50:50 or 10:90.
 Oracles reported separately (not in "best"): MODEall (all local minima enumerated), EXMARG (exact-marginal product).

RESULTS (median [IQR] over instance x SNR cells; alpha=0.5; S = gap_Q / gap_best)
 n=8 (10 inst x SNR 3,6,10,14), matched beta:
   S vs D6 cheap set (L,U,LU)          3.47 [1.98,4.39]   (reproduces D6)
   S vs best realisable without MODE   0.35 [0.17,1.33]
   S vs best realisable incl. MODE     0.17 [0.07,0.58]   ; Q/D (coherence) 2.35
   per kernel (median gap_Q / gap_kernel): PTmulti 2.3, L+Pw+U 1.9, L+Pw 2.1, ST 8.0, MF 0.35, MODE 0.25, MODEall 0.25,
   EXMARG 0.49. By SNR: S_best 0.49 / 0.35 / 0.16 / 0.06 at 3/6/10/14 dB (S_D6 2.2 / 3.1 / 3.6 / 4.6).
 n=10 (inst 0-2 x SNR 3,6,10,14 = 12 cells; D6 had 6 inst), matched beta:
   S vs D6 cheap set                   3.9 [2.8,10.2]
   S vs best realisable without MODE   1.46 [0.65,1.61]
   S vs best realisable incl. MODE     0.20 [0.04,0.71]
   per kernel: PTmulti 2.8, L+Pw+U 2.85, L+Pw 4.1, ST 8.0, MF 1.46, MODE 0.20, MODEall 0.11, EXMARG 1.19.
   By SNR: S_best 1.04 / 0.69 / 0.04 / 0.03 at 3/6/10/14 dB; only 3 dB (2/3 cells) has S_best > 1, and there by 1.04x.
 n=12 (lean set: L,U,LU,PTmulti,L+Pw,MODE,MF; inst 0-1, 10 dB, matched; 18 min): S vs D6 cheap set 8.9 / 17.7 (grows with n),
   but S vs best realisable 0.02 / 0.15 (S without MODE 0.07 / 0.15; MF alone beats Q). Q/D 4.5-9.3.
 TEMPERATURE: S vs D6 cheap set rises smoothly with beta (n=8: 2.5, 2.7, 3.5, 3.6, 3.7, 3.7 at beta/bm .5,.71,1,1.41,2,4)
   - matched beta is not cherry-picked, nothing special happens there. Against the new best it FALLS smoothly
   (n=8: 0.38, 0.26, 0.17, 0.14, 0.07, 0.07; n=10: 0.54, 0.20, 0.04 at 0.5, 1, 2).
 MULTIMODALITY. The window is NOT a many-distant-modes posterior. At matched beta the posterior sits on 1-4 basins
   (basins with >5% mass: n=8 2.5/2/1.5/1, n=10 4/3/3/1 at 3/6/10/14 dB), the top two minima are only 2.5-4 flips apart,
   and P(q12<0.5) falls from 0.27-0.66 (3 dB) to 0.00-0.03 (14 dB). The local gap collapses (1e-6 .. 1e-13) because
   nearby minima are separated by high single-flip barriers (large 1/sigma^2), not because modes are far apart: pair
   flips alone recover ~half the D6 advantage, and any proposal that knows where the few minima are (MODE, MF) wins by
   3-25x. In D6's own data, across all alphas, Spearman(var_q12, S) = 0.37 (n=8, N=240): S does track overlap spread,
   but the alpha=0.5 window at high SNR is the LOW-spread end within that alpha.
 VERDICT A: KILLED as a "beats the best classical" claim. With realisable classical proposals that exploit the
   structure (mode-jumping from greedy-descent minima, MF/TAP-guided independence), S = 0.17 (n=8) and 0.20 (n=10)
   at matched beta, S < 1 in 36/40 (n=8), 10/12 (n=10), 2/2 (n=12) cells. Without the mode-jumping move it is weakened to
   S ~ 0.35 (n=8) / ~1.5 (n=10) / ~0.1 (n=12); S_noMODE > 2 in only 3/40 and 1/12 cells. The coherence result (Q/D 2.3-2.7) survives but is only
   "better than its own dephased walk". Caveat (speculation): MODE needs the relevant minima to be findable by local
   search; at large n the number of minima grows and this proposal may degrade - but nothing here shows QeMCMC scaling
   better, and n=12 (below) gives no sign of a reversal.

=====================================================================================================================
CLAIM B: "MEDIUM T belongs to cluster moves, not QeMCMC" (D1: S = 0.46 on SK n=6 incl. SW/Wolff)
=====================================================================================================================
STRONGEST ATTACK (fairness to quantum). D1 could compute SW/Wolff only at n=6 (2^21 bond subsets). I replaced the
bond-subset enumeration with an exact vertex-subset DP (connectivity probability Pc(S) and random-cluster weight Z(S)
with q=1/2 per state; SW: P(s->s^F) = cut(F) Z(F) Z(V\F); Wolff: (|F|/nv) Pc(F) cut(F)), which is exact and fast for dense
graphs, so EXACT SW and Wolff (ghost spin for the field, Z2-lumped) were computed on SK n=6, 8, 9, 10, 11 - no sampling
noise. MEDIUM = beta/beta_c in {0.68, 1, 1.47} (D1 grid, beta_c = specific-heat peak), per-instance geometric mean.
Quantum side: Layden draws, plus a wider tuning grid than D1 (gamma {.2,.381,.556,.7} x 4 t-windows up to 96 x alpha
multiplier {0.5,1,2}) at n=6, 8, 10. Classical side also strengthened: best of mixbest, SW, Wolff, SW/Wolff+local/uniform
mixtures, SW+Wolff.

RESULTS (median [IQR] over instances; S = Layden gap / best classical incl. exact SW, Wolff and cluster mixtures)
   n     inst  beta_c   S_MEDIUM (all classical incl. mixtures)  tuned/best   SW/mix@bc  Wolff/mix@bc  S at beta/bc .68 / 1 / 1.47
   6     10    0.50     0.43 [0.30,0.85]                         0.67         1.79       3.11          0.21 / 0.38 / 1.02
   8     10    0.49     0.94 [0.56,1.38]                         1.22         1.17       2.20          0.30 / 0.91 / 2.34
   9     10    0.43     1.09 [0.72,1.51]                         -            1.10       2.04          0.38 / 1.18 / 3.00
   10    6     0.40     1.02 [0.76,1.35]                         1.20         1.23       2.23          0.27 / 0.83 / 4.05
   11    3     0.34     1.03 [0.73,1.07]                         -            see summary              0.27 / 0.96 / 3.47
 (results/claimB_mix_summary.txt; cluster+local/uniform mixtures raise best classical by at most 1.8x in single cells,
  median gain ~1.0 over max(single kernels); decohered control / best 0.26-0.35 at all n.)
 Tuning: tuned/Layden 1.35 (n=6), 1.17 (n=8), 1.21 (n=10); the alpha x2 cell wins most often. So Layden's parameters are
 not badly off at MEDIUM; tuning buys ~1.2x, same as D1 reported.
 Structure: below beta_c Wolff wins 3-5x (S 0.2-0.4 at 0.68 beta_c, all n); at beta_c roughly parity (0.4-1.2, no trend);
 at 1.47 beta_c SW/Wolff percolate and QeMCMC wins 1.2x (n=6) -> 2.4-4.6x (n=8-10). The n=6 number 0.46 was the most
 cluster-friendly size: SW's edge over the best local/uniform mixture shrinks from 1.8x (n=6) to 1.1-1.2x (n=8-10) at beta_c.
 VERDICT B: WEAKENED. "MEDIUM T belongs to cluster moves" is true only for the lower half of the MEDIUM band
 (beta < beta_c, S 0.2-0.4, robust in n). Over the full MEDIUM band defined in D1 the exact larger-n result is parity,
 S ~ 0.94-1.09 (n=8-11), not 0.46; above beta_c the cluster moves die and QeMCMC is 2-5x ahead (in steps). It is not a
 QeMCMC win either: the best-classical set still lacks parallel tempering, which the n=8-10 D1 data and A3/A5 literature
 suggest is the real MEDIUM/LOW tool for SK; and all S here are 6-8 orders below the break-even S* ~ 1e6-1e8.

BREAK-EVEN: unchanged - every energy is cheap (t_C ~ 30 ns dense), S* ~ 1e6 (D-Wave) to 7e7 (IBM). Largest S found
 anywhere in this red-team: ~4.6 (SK n=10, 1.47 beta_c, vs exact clusters). No wall-clock route.

NOT RUN / LIMITS
 - Claim A n=10: 3 of D6's 6 instances (machine load); n=12 only 2 instances at 10 dB, reduced kernel set, no ST.
 - Real multi-replica PT was not simulated; ST with exact weights stands in (idealised, generous to classical in the
   weights, pessimistic in the /K charge). PT ladder was not added to claim B's classical set.
 - Claim B n=11: 3 instances, no tuning; n=12 SW/Wolff not run (DP is feasible, quantum n=12 was the cost).
 - Mode-jumping proposal cost model: one-time 2n greedy descents, then O(Kn) per proposal; counted as one step.
