E2 RED TEAM (cost model) - attacks on D7 (2x bound), D5 (surrogate dominance), D9 (classical basin-difference library).
Agent E2, 2026-11-21. All numbers: own simulation, ideal/noiseless, exact matrices unless stated (CPU benchmark = sampled chains).
Env for every run: OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2; at most 2 own python processes.
Machine shared (load 13-16 during the runs). Commands are run from this folder.

FILES
 c1_bound.py      claim 1 numerical attack         -> results/c1_bound.csv, results/c1_summary.txt
 c2_finiteK.py    claim 2 finite-K tempered DA     -> results/c2_finiteK_n{8,10}.jsonl, results/c2.log
 c2_analyze.py    claim 2 S tables                 -> results/c2_S_table.csv, results/c2_summary.txt
 c3_n12.py        claim 3(c) exact n=12 ratio      -> results/c3_n12_s{1,2,3}.json, results/c3_n12.log
 e2mc.c, libe2mc.so, c3_bench.py, queue3.sh   claim 3(a) CPU-time benchmark -> results/c3_bench.jsonl, results/c3_bench.log
 c3_analyze.py    claim 3(a) table                 -> results/c3_table.txt
 Build: gcc -O3 -march=native -fPIC -shared -o libe2mc.so e2mc.c -lm

==== CLAIM 1 (D7 theorem): gap(any reversible group kernel mixture) <= 2 gap(exact block heat-bath, same group law)
PROOF CHECK (own calculation). D7 proof: Pi_g f = E_pi[f | spins outside g] is an orthogonal projection on L2(pi); P_g changes
 only spins in g, so P_g Pi_g f = Pi_g f; P_g self-adjoint (reversible) -> cross terms <Pi_g f,(I-P_g)u> = 0 for u = f - Pi_g f;
 spec(P_g) in [-1,1] -> <u,(I-P_g)u> <= 2||u||^2 = 2 E_HB,g(f). Average over the SAME state-independent p_g (any weights, any
 mixture over (gamma,t), any group sizes): E_Q <= 2 E_HB -> 1-lambda_2(Q) <= 2(1-lambda_2(HB)). CORRECT.
 Absolute gap: the HB mixture is a convex combination of projections -> PSD -> its absolute gap equals its right gap; the absolute
 gap of Q is <= its right gap. So the bound also holds for the absolute gap (the convention used by qmc/P1). CORRECT.
 IAT form tau_f(Q) >= (tau_f(HB)-1)/2: follows from I-Q <= 2(I-HB) on 1-perp and operator-monotone inversion. CORRECT.
 The constant 2 is sharp (one spin, uniform pi: HB gap 1, deterministic flip gap 2).
 NOT COVERED: (i) fixed-order (systematic) sweeps such as P2's sequential multi-group sweep - product kernels are not reversible
 and the Dirichlet-form argument does not apply; (ii) state-dependent group choice; (iii) non-reversible lifted kernels.
NUMERICAL ATTACK: python c1_bound.py (~9 min). SK n=6 (seeds 1-5) and n=8 (seeds 1-3), beta 0.1/0.3/1/3, k=1,2,3, groups =
 consecutive blocks or n random k-subsets, p_g uniform or Dirichlet(0.5) (non-uniform). Per-fiber kernels: Metropolized Gibbs
 (MGS, Liu 1996: the textbook kernel that beats heat-bath, most negative spectrum), MH with random symmetric proposal (Sinkhorn),
 MH with random perfect-matching involution proposal (adversarial, pushes eigenvalues to -1), and the real coarse-grained quantum
 proposal (qmc.coarse_grained_Q, n=6, k=2,3, 8 (gamma,t) draws). Cases with gap_HB < 1e-9 (beta=3 underflow) dropped.
 Random scan (the theorem's setting), 852 cases:  max gap ratio  MGS 1.885 | INV 1.885 | SYM 1.721 | QCG (quantum) 0.721
   (medians 1.15 / 0.24 / 0.50 / 0.31). No violation. The quantum CG move never exceeds 0.72x of HB (D7 measured 0.11-0.35).
 Systematic scan (fixed block order, one sweep = product), 243 cases: (1-SLEM) ratio max 2.24, asymptotic-rate ratio
   log|l2_Q|/log|l2_HB| max 2.78 (MGS/INV, n=6, k=1, beta=0.3 and 1.0). So the factor 2 FAILS for fixed-order sweeps.
VERDICT CLAIM 1: TRUE WITH CAVEAT (proved for random-scan / state-independent group choice, absolute gap included, any p_g).
 Caveat: it does not cover P2's fixed-order sequential sweep; there a group kernel can beat a heat-bath sweep by >2x (2.2-2.8x
 found). This does not rescue quantum: the classical side can run the same sweep with Metropolized block Gibbs (same O(2^k) cost
 as HB), which is the kernel that produced the >2x, and the quantum CG kernel was 0.72x of HB at best even in random scan.
 Corrected statement: "no random-scan group move beats exact block Gibbs by >2x per step; for fixed-order sweeps the bound is
 not proved, and the right classical comparator is Metropolized block Gibbs (or HB), not HB alone."

==== CLAIM 2 (D5): surrogate-in-U QeMCMC is dominated at n<=12 (S_ext < 1) by tempered surrogate DA with EXACT pi_sur draws
ATTACK: an exact pi_sur(beta') draw needs 2^n enumeration; replace it by a realistic sampler and re-score with the same
 one-true-energy-call-per-step accounting. Competitor T-DA(K): inner kernel = K steps of Metropolis on E_sur at beta' = f beta,
 f in {0.7,0.5,0.35,0.25}, inner proposal local (set B, the large-n-honest set: no uniform proposals anywhere) or 50/50
 local+uniform (set A), outer accept min(1, pi_t(s') pi'_sur(s) / (pi_t(s) pi'_sur(s'))) (exact: Liu 2001 surrogate transition,
 inner kernel pi'_sur-reversible; checked by construction as in D5 da_outer), plus its 50/50 mix with local Metropolis on E_true.
 Set A also contains D5's local/uniform/mix on E_true and same-beta DA with K' <= K; set B contains local and same-beta DA-local.
 q_sur gaps read from D5 raw jsonl (D5 instances, D5 code d5lib unmodified). K in {1,10,100,1000}, exact matrices.
 python c2_finiteK.py 8 0 1 2 3 4 5 6 7 ; python c2_finiteK.py 10 0 1 2 3 4 ; python c2_analyze.py   (~25 min under load)
 Cells: families a,b at rho 0.1/0.3/0.5, family c rho 0.3; MEDIUM and LOW; n=8 (8 instances), n=10 (5). n=12 NOT re-scored
 (compute budget). 182 instance-level cells (91 LOW).
 Results (instance-level cells with S = gap(q_sur)/gap(best realistic classical) > 1):
   K (surrogate steps per true call)   1          10         100       1000     | D5 S_free  D5 S_ext (exact draws)
   set A (local+uniform allowed)       177/182    25/182     4/182     4/182    | 56/182     3/182
     LOW only                          91/91      23/91      2/91      2/91     | 47/91      1/91
   set B (local only, no uniform)      180/182    89/182     4/182     4/182
     LOW only                          91/91      73/91      2/91      2/91
   max S at K=100: 1.43 (n=8 inst 6 fam b rho .5 LOW, beta*sigma 3.9; D5 S_ext there already 1.20).
   Median S at K=100 (set B): 0.18-0.19 (n=8, n=10, MEDIUM and LOW); per-cell medians 0.06-0.6 (results/c2_summary.txt).
   n=10 LOW, b rho .3: S_B = 1779 (K=1), 41.7 (K=10), 0.36 (K=100), 0.23 (K=1000). Same pattern in every LOW cell.
 K*_B (smallest K with S_B <= 1): n=8 LOW: K*=10 14/56, 100 40/56, >1000 2/56; n=10 LOW: K*=10 4/35, 100 31/35.
   K* drifts up from n=8 to n=10 (the surrogate chain at beta' ~ 1-2 beta_c is itself slowing down), but stays <= 100.
 Cost: 100 local surrogate flips ~ 3 us (30 ns each, A5) per true call; negligible next to any t_E for which a surrogate is used.
REVISED VERDICT CLAIM 2: VERDICT STANDS at n <= 10 (shown by own simulation). The fairness objection is correct in principle
 (exact draws are not available), but a 100-step local Metropolis chain on the surrogate at the hotter beta' recovers the
 exact-draw result in 178/182 cells; quantum wins in a LOW cell only if the classical inner budget is cut to K <= 10.
 The open (speculative) case is unchanged and now sharper: q_sur can win only where the local/PT mixing time of the SURROGATE at
 beta' ~ 0.35-0.7 beta exceeds the affordable inner budget t_E / t_flip (~1e4-1e7 steps for t_E = 0.3 ms - 0.3 s). That needs n
 well beyond exact simulation, and the classical side would then use PT on the surrogate, not plain Metropolis.

==== CLAIM 3 (D9 side finding): classical basin-difference mask library + 50% local ~ 0.72-0.83 of full QeMCMC gap
(a) CPU-SECOND BENCHMARK (own simulation, sampled chains, single thread scalar C). ./queue3.sh (runs python c3_bench.py
 {sk 32|sk 64|ea 8|ea 12} 2.0) then python c3_analyze.py. Instances qmc.sk_instance(n, 1..5), qmc.ea_instance(L, L, 1..5)
 (2D Gaussian periodic). Regimes as D7: SK MEDIUM beta=1/sqrt(n), LOW 3/sqrt(n); EA MEDIUM T=0.8, LOW T=0.4. PT = D7 tuned
 ladders (geometric from 0.3 beta_c (SK) / T=2 (EA); R = 4/6 (SK32), 4/8 (SK64), 6/6 (EA8), 8/10 (EA12); measured swap rates
 0.37-0.56). Library: 256 steepest-descent minima from uniform random starts, 1024 random pairs -> XOR masks (the D9 law,
 sampled); build cost 0.045-0.052 s CPU (counted, reported, not needed to make the verdict). Mask move: flip the mask set,
 Metropolis accept, revert (exact: mask law state-independent -> symmetric proposal). 2 s CPU budget per run, random start.
 Observables per sweep: E and |q| = |overlap with reference| (reference = lowest E of a 3 s PT run and the 256 minima).
 Censoring as D7 (win only if mask resolved, lose only if competitor resolved, resolved = N/tau >= 50 and N >= 1000).
 Results (medians over 5 instances, tau in CPU seconds; full table results/c3_table.txt):
   cell        metro tauE / tauq     PT tauE / tauq      MASK tauE / tauq     mask accept  mask len  distinct minima
   SK32  MED   1.1e-5 / 1.9e-5       3.4e-5 / 5.3e-5     2.1e-4 / 2.6e-4      0.042        15.9      84/256
   SK32  LOW   2.1e-5 / 5.7e-4       5.1e-5 / 3.4e-4     3.2e-4 / 6.7e-4      0.008
   SK64  MED   3.4e-5 / 6.6e-5       1.3e-4 / 2.5e-4     2.5e-3 / 4.4e-3      0.002        31.4      229/256
   SK64  LOW   6.0e-4 / 5.8e-3       5.2e-4 / 2.0e-3     9.3e-3 / 8.9e-2(1/5) 0.000
   EA8   MED   2.1e-4 / 2.9e-3       1.1e-4 / 5.5e-4     1.3e-3 / 2.6e-3      0.001        32.1      256/256
   EA8   LOW   5.4e-3 / 7.0e-2(1/5)  2.0e-4 / 2.2e-3     6.8e-3 / 3.8e-2(0/5) 0.000
   EA12  MED   2.0e-3 / 1.4e-2       6.0e-4 / 5.5e-3     5.3e-2 / 0.15 (0/5)  0.000        72.3      256/256
   EA12  LOW   7.6e-3 / 8.8e-2(1/5)  4.6e-4 / 1.5e-2     3.8e-2 / 0.13 (0/5)  0.000
 Mask+local vs best of (Metropolis, PT) per CPU second: WIN 0, LOSE 80, UNDETERMINED 0 (8 cells x 5 instances x {E,|q|});
 median slowdown 7-68x per cell, range 1.3-450x. PT whose replicas use the mask mix (ptmask) is also slower than plain PT in
 every cell (13-57x on tau_E). Mechanism: two random local minima differ in ~n/2 spins, so the masks are near-uniform large flips; the
 acceptance collapses 0.04 (n=32) -> 0.002 (n=64) -> 0 (n>=64 at LOW, EA). At n<=10 (D9) there are only a handful of minima, so
 the "library" is effectively a list of jumps between ALL the minima of the instance; that does not survive n=32.
(b) NOVELTY (literature, verified by web search): it is a known family, not new. Closest: Houdayer cluster move (flip the
 cluster of sites where two replicas disagree; J. Houdayer, EPJB 22, 479 (2001), arXiv:cond-mat/0101116) and its isoenergetic
 generalisation (Zhu, Ochoa, Katzgraber, PRL 115, 077201 (2015), arXiv:1501.05630) - the state-DEPENDENT, connected-cluster
 version of "XOR of two configurations", which is why it keeps acceptance where a fixed library does not; differential-evolution
 MCMC (ter Braak, Stat. Comput. 16, 239 (2006), doi 10.1007/s11222-006-8769-1; discrete version DREAM(D), Vrugt and ter Braak,
 HESS 15, 3701 (2011)) - proposal from the difference of two population members; mode-jumping proposals with local optimisation
 (Tjelmeland and Hegstad, Scand. J. Stat. 2001; binary version Hubin and Storvik arXiv:1604.06398). The fixed basin-difference
 library is a state-independent, non-adaptive special case of these (independent idea, but no new mechanism).
(c) FINITE SIZE n=12 EXACT: python c3_n12.py 1 2 3 (D9 d9lib unmodified, Lanczos gaps, 16 Layden draws; ~7 min/instance;
 seeds 4-5 cut for compute). Gap ratio (basin-difference law with exact basin weights + 50% local) / (full P1 QeMCMC):
   beta     0.3    beta_c   1      3
   seed 1   0.66   0.69     1.74   5.56
   seed 2   0.65   0.63     0.55   0.61
   seed 3   1.09   1.08     1.08   1.05
   (L=1024 sampled library within 2% of the infinite law.) Number of local minima: 9, 10, 14 (n=10: 4-9).
 So at n=12 the ratio does NOT decay (median 0.66-1.08; N=3, weak); the D9 number holds at n=12. But this is exactly the small-n
 regime where the instance has ~10 minima and the "library" enumerates all jumps between them; (a) shows it collapses by n=32-64.
REVISED VERDICT CLAIM 3: FALSE as "a useful classical sampler today". True only as a small-n (n<=12) exact-gap statement.
 Per CPU second it lost to Metropolis/PT in 80/80 comparisons at SK n=32,64 and EA L=8,12 (median 7-68x slower), because its
 acceptance goes to ~0 once minima are many and ~n/2 apart. Not novel either: a fixed, state-independent special case of
 Houdayer / ICM replica-difference cluster moves and discrete DE-MC, which are the versions that work.
 Implementation slack (own estimate): my mask move costs O(|m| deg) with revert; an O(|m|^2) energy check would make it ~2x
 cheaper per rejected move. That cannot close a 7-68x gap with acceptance <= 0.002.

COMPUTE USED: ~65 CPU-min of own processes (c1 9 min, c3_n12 21 min, bench 11 min, c2 ~25 min), at most 2 at a time.
SEEDS: c1 rng 2024, quantum draws qmc.draw_params(5,8); c2 D5 instances/draws; c3 bench library seed 1000+s, ref PT 999+s and
 5000+s, chains 10 s + method index + 1; c3_n12 D9 seeds.
