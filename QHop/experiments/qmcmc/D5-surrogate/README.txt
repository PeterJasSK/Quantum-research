D5 SURROGATE-DRIVEN QeMCMC VERSUS CLASSICAL DELAYED ACCEPTANCE WITH THE SAME SURROGATE
Experiment agent D5, QeMCMC applied review, Wave 4. Run 2026-11-21. Exact linear algebra, ideal (noiseless) proposals.
All numbers below: shown by own simulation (ideal, exact transition matrices), unless labelled otherwise.

QUESTION
Main team path to non-Ising, expensive energies: put a cheap Ising/QUBO surrogate H_sur inside U = exp(-iHt) and use
the true energy E_true in the Metropolis accept. B1 claims (_reports/B1-optimization.txt, item 3):
 (i) the chain is exact for any real H_sur; (ii) equilibrium acceptance ~ 2 Phi(-beta sigma / sqrt 2);
 (iii) it is dominated by classical surrogate-transition / delayed acceptance (DA) (Liu 2001; Christen and Fox 2005)
 using the same surrogate. We test all three and measure S = gap(quantum, H_sur in U) / gap(best classical with the same
 surrogate and the same number of true-energy calls).

SETUP (what was run exactly)
Instances: SK, J,h ~ N(0,1) unscaled (qmc.sk_instance, seed 1000 n + inst), E_SK centred. Same SK base for all families.
True energies, all rescaled to std(E_true) = std(E_SK) so beta is comparable across rho:
 (a) E_true = sqrt(1-rho^2) E_SK + rho sd u34; u34 = dense random 3-body + 4-body terms (all triples and quadruples,
     N(0,1) coefficients, seed +500), unit std. Surrogate = least-squares quadratic Ising fit on ALL states. Because the
     Walsh basis is orthogonal on the full cube, the fit is exactly sqrt(1-rho^2) E_SK and residual/std = rho exactly.
 (b) same, with u34 replaced by i.i.d. N(0,1) per state (seed +700), projected orthogonal to the quadratic space (this
     is exactly the LS residual of SK + iid noise; the O(n^2/2^n) projected part is absorbed into the SK instance).
 (c) "smooth" non-Ising: E_true = norm[ g_a(z) + 0.1 sd(g) u34 ], z = E_SK/sd, g_a(z) = (1 - exp(-a z))/a (monotone,
     = z at a = 0); surrogate = LS quadratic fit; a solved (brentq) so that residual/std = rho. rho >= 0.1 by construction.
 rho grid (a,b): 0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9; (c): 0.1, 0.2, 0.3, 0.5, 0.7. sigma_abs = rho * std(E_true).
Sizes / instances: n=8 (8 instances, all families), n=10 (5 instances, all families), n=12 (family a only,
 rho 0.1/0.3/0.6, oracle only at rho 0.3, no decohered control, nested K=1 only, see results/log_n12_*.txt for how many
 instances finished).
Regimes per (instance, family, rho): beta_c = argmax of exact specific heat of E_true on logspace(-2.5,1,141);
 HIGH = beta_c/3, MEDIUM = beta_c, LOW = 3 beta_c. Also beta_loc = beta where the local-proposal gap falls below 0.1x
 its beta->0 value (results/regime_table.txt). SK n=10 at rho=0: beta_c ~0.40 [0.32,0.56], beta_loc ~0.63.
Quantum proposal: qmc.quantum_Q, m=16 draws per instance (seed 7+inst), gamma from the grid {0.275,0.375,0.475,0.575}
 (bin midpoints of U[0.25,0.6], for eigh caching), t ~ U[2,20], alpha = sqrt(n)/std(E_in_U). Q symmetrised (Q+Q^T)/2 to
 remove roundoff (exactly symmetric in exact arithmetic).
Proposals compared at each (sigma, beta), all with exactly ONE true-energy evaluation per outer step:
 (1) q_sur: quantum, E_sur in U, accept on E_true.                (2) q_true: quantum, E_true in U (oracle upper bound;
     NOT implementable for b, c: E_true has exponentially many terms).
 (3) local, uniform, 50/50 local+uniform mix on E_true (no surrogate).
 (4) classical DA: inner K-step Metropolis on E_sur at the same beta, inner proposal = local (DA_local) or local+uniform
     mix (DA_mix), K = 1, 10, ..., 1e6 (exact P_sur^K by repeated squaring), plus K = inf (exact Boltzmann draw from
     pi_sur). Outer accept min(1, pi_t(s') pi_s(s) / (pi_t(s) pi_s(s'))).
 (5) nested: inner kernel = Metropolis on E_sur with the quantum proposal (K = 1, 10, 100 quantum calls per true call).
 (6) extra classical stress test (tempered.py, MEDIUM/LOW only): Hastings independence sampler from pi_sur at a HOTTER
     beta' = f beta, f in {1, .7, .5, .35, .25, .15, .08, 0}, accept min(1, w(s')/w(s)), w = pi_t / pi_sur(beta'),
     and the 50/50 mixture of the best such kernel with local Metropolis on E_true. Same surrogate, one true call/step.
 control: decohered quantum proposal (qmc.decohered_Q, dt = 0.25) with E_sur in U.
Gap = 1 - max|lambda_2| of the pi_true-reversible P via A = sqrt(P o P^T) (= D^1/2 P D^-1/2, no under/overflow).

COMMANDS (from QHop/experiments/qmcmc/D5-surrogate, env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2)
 python verify.py                                   # (i),(iii) exactness + controls + analytic (ii); ~6 min
 python sweep.py --n 8 --inst 0 1 2 3 4 5 6 7       # ~1.5 min per instance (machine shared, load 20-50)
 python sweep.py --n 10 --inst 0 1 2 3 4            # 65 min total under load
 python sweep.py --n 12 --inst <i> --fams a --rhos 0.1 0.3 0.6 --oracle_rhos 0.3 --light
 python accept_curve.py --n 10                      # acceptance vs beta*sigma, 25 betas, 5 instances
 python tempered.py --n 8 --inst 0..7 ; python tempered.py --n 10 ; python tempered.py --n 12 --inst 0..4 --fams a --rhos 0.1 0.3 0.6
 python analyze.py                                  # tables + plots
FILES
 d5lib.py (families, fits, kernels, DA, gaps), sweep.py, verify.py, accept_curve.py, tempered.py, analyze.py
 results/raw_n{n}_i{inst}.jsonl (every gap, move rate, acceptance, per config), results/per_instance.csv,
 results/S_table.txt/.csv (median [IQR]), results/regime_table.txt, results/verify.json/.log,
 results/accept_curve_n10.csv, results/tempered_n*.csv, results/log_*.txt (run times)
 plots/acceptance_vs_beta_sigma.png, plots/S_vs_sigma_free.png, plots/S_vs_sigma_K1000.png, plots/S_vs_sigma_oracle.png,
 plots/S_condition_scatter.png

WHAT WAS CUT (machine overloaded, coordinator limit of 2 own processes, then finalize order)
 n=12: planned 5 instances; finished instance 0 fully (9 configs) and instance 1 partly (8 of 9 configs; rho=0.6 LOW
 missing). Tempered-DA stress test at n=12: instance 0 only. n=12 has no decohered control, no rho grid beyond
 0.1/0.3/0.6, oracle only at rho 0.3. n=12 rows are therefore indicative (N=1-2), below the >=5-instance rule.
 Not run at all: sample-based (not all-states) surrogate fits; PT or cluster moves as the inner classical surrogate chain;
 noisy quantum proposals.
 Run times (shared machine, load 20-65): n=8 ~80 s/instance; n=10 65 min for 5 instances; n=12 128 min for one instance;
 verify 6 min; accept_curve 33 min; tempered n=8+n=10 ~37 min.

RESULTS
(i) EXACTNESS of surrogate-in-U QeMCMC: CONFIRMED (own simulation, exact). verify.py, n=8 and 10, families a/b/c,
 HIGH/MEDIUM/LOW: ||pi_true P - pi_true||_1 <= 6e-16 and detailed-balance L1 <= 3e-16 for q_sur. Raw quantum_Q
 asymmetry before symmetrisation ~1e-16 (roundoff). Control with a T1-like 1->0 readout decay p=0.02 after the
 measurement (asymmetric Q): stationarity error up to 4e-2, TV(stationary, pi_true) up to 2.6e-2 -> exactness depends on
 Q being exactly symmetric, as P1 SI says (twirling needed on hardware).
(iii) EXACTNESS of classical DA / surrogate transition: CONFIRMED. DA with local inner K=1,10, K=inf (exact surrogate
 draw), and nested quantum-inner K=10: stationarity and detailed-balance L1 <= 6e-16. Control with the naive ratio
 pi_t(s')/pi_t(s) on the K=10 inner kernel: TV to pi_true 0.46 (exact matrix) and 0.45 (sampled chain, 2e5 steps), versus
 0.012 for the corrected ratio (i.i.d. noise floor 0.005; the remainder is chain autocorrelation).
(ii) ACCEPTANCE 2 Phi(-beta sigma/sqrt 2): analytic part CONFIRMED (own calculation): if s ~ pi_true and the proposal
 draws s' from the reference law under which the residual r is N(0, sigma^2) independent of the surrogate, then
 D = beta(r(s')-r(s)) ~ N(m, 2m), m = beta^2 sigma^2, and E[min(1,e^-D)] = 2 Phi(-sqrt(m/2)) exactly (quadrature matches
 to 1e-15, verify.json). This is exactly the acceptance of DA with K=inf, NOT of the quantum proposal.
 Numerically (accept_curve_n10.csv, plot acceptance_vs_beta_sigma.png), medians over 5 instances, 4 rho, 25 betas:
   beta*sigma        0-0.5   0.5-1   1-2    2-3    3-5
   2 Phi             0.944   0.618   0.313  0.086  0.009
   DA K=inf (b)      0.945   0.637   0.398  0.190  0.100
   quantum residual-only factor (b)  0.945  0.631  0.391  0.141  0.084
   quantum TOTAL acceptance (b)      0.878  0.383  0.150  0.043  0.018
   DA K=inf (a, structured residual) 0.944  0.640  0.420  0.300  0.274
 -> formula holds for Gaussian unstructured residuals up to beta*sigma ~1; above that finite 2^n (low-T concentration,
 max of 2^n Gaussians) puts a floor above 2 Phi. Structured residuals (a) decorrelate less and accept more. Family (c)
 (skewed, non-Gaussian residual) violates it in both directions. The quantum chain's TOTAL acceptance is 2-4x BELOW
 2 Phi because the surrogate energy difference also rejects (it is a symmetric proposal, not a draw from pi_sur).

S TABLE (median [IQR]; full table results/S_table.txt; S = gap ratio per true-energy call, surrogate steps free)
 S_free = vs best of {local, uniform, mix, DA local/mix inner K=1..1e6, DA K=inf}.
 S_ext  = additionally vs tempered-surrogate independence DA (beta_sur = f beta) and its mix with local (MEDIUM/LOW).
 n  fam regime rho  beta*sig  S_free              S_ext               S_vs_no_surrogate  S_oracle  S_decoh
 10 a  HIGH  0.1  0.09   0.20 [0.16,0.20]    -                   0.94   0.20  0.15
 10 a  HIGH  0.5  0.44   0.52 [0.39,0.60]    -                   1.02   0.51  0.38
 10 a  MED   0.1  0.28   0.13 [0.06,0.13]    0.08 [0.06,0.13]    2.26   0.14  0.03
 10 a  MED   0.5  1.32   0.89 [0.49,0.96]    0.60 [0.31,0.64]    1.95   1.14  0.23
 10 a  LOW   0.1  0.84   0.37 [0.17,0.56]    0.07 [0.02,0.07]    8.54   0.45  0.02
 10 a  LOW   0.3  2.37   4.42 [0.99,4.93]    0.04 [0.04,0.19]    6.39   5.73  0.23
 10 a  LOW   0.5  3.95   2.95 [2.94,4.57]    0.24 [0.08,0.44]    5.44  15.56  0.35
 10 b  MED   0.3  0.84   0.34 [0.28,0.51]    0.31 [0.15,0.34]    2.27   0.49  0.07
 10 b  LOW   0.1  0.84   0.33 [0.31,0.45]    0.09 [0.06,0.10]   11.29   0.39  0.02
 10 b  LOW   0.3  2.51   2.59 [1.78,4.18]    0.23 [0.12,0.41]   16.89   3.68  0.15
 10 b  LOW   0.5  4.43   6.79 [2.51,7.44]    0.26 [0.08,0.40]    7.44  10.69  0.17
 10 c  MED   0.3  0.40   0.17 [0.13,0.18]    0.17 [0.13,0.18]    1.85   0.11  0.06
 10 c  LOW   0.3  1.19   0.06 [0.05,0.09]    0.06 [0.05,0.09]   13.51   0.04  0.01
 8  a  LOW   0.3  2.69   2.09 [1.22,3.21]    0.22 [0.08,0.37]    2.76   2.62  0.68
 8  b  LOW   0.5  3.97   2.80 [2.39,3.23]    0.34 [0.07,0.49]    2.80   5.49  0.47
 12 a  MED   0.3  1.11   0.70 (N=2)          0.27 (N=1)          3.50   0.79  -
 12 a  LOW   0.3  3.32  15.6 (N=2)           0.10 (N=1)         35.0   23.0   -
 12 a  LOW   0.6  5.87   9.13 (N=1)          0.19 (N=1)          9.13   -     -
 All HIGH cells, all n, all families: S_free 0.19-0.85 (<1). Family c: S_free <= 0.33 everywhere (DA wins 3-20x).
 Cost version (surrogate step = 1e-3 true call, finite K only): within ~10% of S_free except HIGH (DA cheaper K wins).
 Nested quantum-inner DA never beats q_sur or the best classical by more than 1.45x and costs K QPU calls per true call.
 K* (inner local/mix steps for classical DA to match q_sur): 1-100 wherever DA can match at all; where q_sur beats
 same-beta DA, even K=inf (exact surrogate Boltzmann draw) does not match -> the loss is from the residual, not from
 the surrogate being hard to sample.
 Best classical in the cells where S_free > 1: mostly UNIFORM or local+uniform on E_true (small-n artefact), i.e. the
 same-beta surrogate is classically useless there; the quantum gain in those cells is the usual QeMCMC-vs-uniform gain.

INTERPRETATION
 1. Against DA that draws from the surrogate at the SAME beta (B1's (iii) exactly as stated), the surrogate-in-U quantum
    proposal wins only at LOW T with a bad surrogate: beta*sigma >~ 1.5-2 (DA acceptance 2 Phi <~ 0.2), families a/b,
    S_free ~1.5-7 at n=8-10, 9-16 at n=12 (N<=2). At HIGH and MEDIUM, and for any residual with beta*sigma < ~1.5,
    classical DA wins 1.2-10x. For the smooth monotone family (c) classical DA wins everywhere (the LS-fit surrogate
    in U is a poor driver, and even the E_true oracle in U is poor because of the skewed energy scale).
 2. B1's "no symmetric quantum proposal can beat the independence draw" is FALSE as stated (S_free > 1 cells exist):
    the independence sampler's gap is bounded by min pi_sur/pi_true, which collapses at large beta*sigma.
 3. But a better use of the SAME surrogate restores classical dominance at every size we could test: an independence
    proposal from pi_sur at a hotter beta' = 0.35-0.7 beta (exact Hastings ratio) or its mix with local moves gives
    S_ext = 0.04-0.6 in every MEDIUM/LOW cell, n=8, 10 and 12 (n=12 one instance). So B1's (iii) holds in spirit:
    classical surrogate-assisted MCMC dominates. Caveat (speculation): independence samplers degrade exponentially with n
    (weight degeneracy; at fixed rho, beta*sigma grows ~sqrt(n) for SK), and the q_sur gap fell more slowly from n=8 to
    12 (LOW rho .3: q_sur 3.8e-2 -> 1.4e-2, tempered DA 2.0e-1 -> 7.5e-2) - no crossover visible at n<=12; a crossover
    at n of tens is possible but untested; and at that size classical would use PT on the surrogate inner chain.
 4. Decohered control (E_sur in U, dephased) is 3-50x below q_sur at MEDIUM/LOW: the q_sur gains need coherence.
 5. Oracle gap: with an Ising-representable residual (a) the surrogate in U costs little at small rho; at rho 0.5 LOW
    the oracle is ~3-5x better than q_sur -> the surrogate loses much of the quantum gain where the quantum gain exists.

CONDITION UNDER WHICH THE QUANTUM SURROGATE PROPOSAL CAN WIN (from own simulation + labelled speculation)
 Needs ALL of: LOW T for E_true (local and uniform trapped); a surrogate that is good in shape but with residual
 beta*sigma >~ 1.5 (so same-beta DA collapses) and residual structured / Ising-like enough that the quantum moves keep
 acceptance; AND a size where no classical surrogate-based scheme (tempered independence DA, DA with PT on the
 surrogate) mixes - not observed at n<=12. Surrogate glassiness alone is NOT the condition: at n<=12 classical DA
 matched q_sur with K<=100 inner steps whenever DA could match at all, and with t_E expensive classical can afford
 K ~1e6-1e9 surrogate steps per true call. Verdict: SIMULATE MORE only as a scaling question (n 16-30 with tensor
 networks / sampled chains vs tempered DA + PT-inner DA); as an applied path at n<=12 it is classically dominated.

BREAK-EVEN (BRIEF-screening convention, own calculation). Expensive energy, one true call per step in both chains:
 S* = (t_Q + t_E)/(t_C + t_E), t_C (incl. up to 1e6 surrogate steps at 30 ns) <= 0.03 s.
 t_E = 1 s:  optimistic (Helios 0.1 s) 1.1 / realistic (IBM 3 s) 3.9 / pessimistic (F = 0.2, N_2q ~800) 19.5.
 t_E = 1 min: 1.002 / 1.05 / 5.2.
 Measured S vs the best classical with the same surrogate (S_ext) is 0.04-0.6 -> below break-even in every tested cell.
