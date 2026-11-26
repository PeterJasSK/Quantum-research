D2 - QeMCMC vs a tuned parallel-tempering baseline, and QeMCMC as one move inside PT
(QHop QeMCMC applied review, Wave 4, agent D2, 2026-11-21). Plain text. All numbers are own simulation, ideal (noiseless)
proposal, unless labelled otherwise.

WHAT WAS RUN (reproduce)
  gcc -O3 -march=native -fopenmp -shared -fPIC ckern.c -o libckern.so -lm
  python test_d2.py          # correctness checks (output in test_d2_output.txt; its speed lines are from the FIRST,
                             # slower kernel; current speeds are listed below)
  bash run_all.sh            # 30 instances, 2 workers, OMP_NUM_THREADS=1 -> results/<fam>_n<N>_s<seed>.json, logs/
  python analyze.py          # summary.txt, all_runs.csv, step_advantage.csv, fig_*.png
Files: ckern.c (C: Metropolis, PT, Houdayer, Chebyshev statevector, decohered walk), d2lib.py (samplers, ladder tuning,
chains, equilibration), run_instance.py (all samplers on one instance), analyze.py, run_all.sh, test_d2.py.
Machine was heavily oversubscribed (load 17-66 on 8 cores) during runs; wall times are not meaningful as benchmarks.

INSTANCES (fixed seeds)
  SK (qmc.sk_instance, J,h ~ N(0,1) unscaled): n=12 seeds 1200-1204, n=14 1400-1404, n=16 1600-1604, n=18 1800-1804.
  2D EA Gaussian periodic, h=0: 4x4 (n=16) seeds 500-504; 3x4 (n=12) seeds 520-524 (substitute for quantum runs, see CUTS).
  beta_c = specific-heat peak, exact enumeration for every n (2^18 states is cheap). LOW = 3 beta_c, MED = beta_c,
  HIGH = 0.3 beta_c (per instance). Local-collapse marker: Metropolis tau_E on a beta grid (0.3..3 beta_c) stored in each
  JSON as metro_tau_grid. beta_c values per instance are in summary.txt (SK n=12 median 0.41, n=14 0.35, n=16 0.32,
  n=18 0.29; EA 4x4 0.72; EA 3x4 0.80; SK n=12 seed 1202 is an outlier with beta_c = 1.27).

SAMPLERS AND HOW DETAILED BALANCE IS KNOWN
 (1) single-spin Metropolis (C).  (2) PT, ladder from 0.3 beta_c to the target beta: geometric start (4 rungs), then up to
 8 rounds of re-spacing to equal -log(swap acceptance) per gap with rung count set for ~25% (d2lib.tune_ladder); every
 ladder and its swap-rate history is in the JSON. HIGH: no ladder needed (R=1, PT == Metropolis).
 Cost: one sweep = n flips x R replicas (x copies).  (3) EA only: PT + Houdayer, two copies per temperature, Houdayer cluster
 move between copies at every temperature after every sweep (rejection-free, preserves the two-replica product measure);
 counted as 2nR + nR flips per sweep.  (4) pure QeMCMC chain at the target beta.  (5) PT where each of the k = min(2,R)
 coldest replicas does one quantum move with probability p_q per sweep, p_q in {0.01, 0.1, 0.5, 1}.  (6) the same with
 the decohered proposal, p_q in {0.1, 1} (reduced, see CUTS). Pure decohered chains were also run as a control for (4).
 Quantum proposal: Layden H = (1-g) alpha diag(E) + g sum X, alpha = sqrt(n)/std(E). A FIXED pool of 16 (g,t) pairs
 (4 g ~ U[.25,.6] x 4 t ~ U[2,20], seed 0) - the same finite-pool convention as qmc.quantum_Q with m=16. Each H real
 symmetric -> U = U^T -> pooled proposal symmetric -> Metropolis exact. No Q matrix is built: the statevector
 exp(-iHt)|s> is computed by Chebyshev propagation (real recursion, C) and one outcome is sampled; states revisited >= 4
 times get an exact cached row with a reservoir of iid draws (same law). Checked vs qmc.quantum_Q at n=8: max abs error
 1.8e-14; single-shot sampling TV distance 0.036 at the 20000-draw noise floor.
 Decohered control: same generator, full Z dephasing every dt = t/round(t/0.25) (qmc.decohered_Q convention), each
 substep computed on the Hamming ball of radius 3 (leak < 1e-16 per substep at n=8). Symmetric -> exact. Checked vs
 qmc.decohered_Q at n=8: TV 0.034 vs noise floor 0.035.
 Inside PT the quantum/decohered moves are Metropolis moves at the replica's own beta with a symmetric proposal -> each
 move preserves the joint product measure.

OBSERVABLES
 tau = integrated autocorrelation time (qmc.iat, Sokal window) of E and of q = overlap with the exact ground state
 (|q| for EA, which has h=0). tau_max = max(tau_E, tau_q) is used for S and costs. Classical tau in single-spin-flip
 proposals, quantum tau in quantum steps, hybrids in sweeps. Equilibration: ensemble mean of E over 32 (classical) or
 16/8 (QeMCMC) random-start chains, dyadic windows, t_eq = first window after which every window mean is within 1% of
 the exact <E>. A chain counts as "equilibrated" if its run-mean E is within 1% of exact (trapped chains report a fake
 small tau). Run lengths: Metropolis 4e7 n/16 flips (HIGH 2e6, recorded every flip), PT 2e5 sweeps, pure QeMCMC up to
 20000 steps, hybrids up to 5e4 sweeps (time capped; N for every run is in all_runs.csv).

QUANTUM PROPOSAL SPEED (one core, machine load ~17)
 single-shot (one (g,t), one outcome) / full 16-pair row:  n=12 0.008 s / 0.05 s; n=14 0.08 s / 0.7 s;
 n=16 0.65 s / 2.6 s; n=18 3.2 s / 37 s. At load ~60 the n=16 pure chain got only 90-180 steps in 4 min.
 => quantum runs stopped at n=14 (SK). n=16 and n=18 are classical-only.

RESULTS (median [IQR] over 5 instances; full table in summary.txt)
PT ladders: LOW 3-4 replicas, swap 0.19-0.40 (SK12 0.19-0.35, SK14 0.32-0.39, SK16 0.29-0.35, SK18 0.25-0.40,
 EA3x4 0.22-0.29, EA4x4 0.32-0.37); MED 3 replicas, swap 0.34-0.58 (above the 30% goal: with only two gaps the next
 smaller ladder drops below 20%); HIGH R=1. Example SK n=16 seed 1600 LOW: betas 0.096 0.22 0.377 0.964, swap 0.30 0.34 0.30.
tau_max per sampler (classical in flips, quantum in steps):
 regime  sampler        SK12        SK14        SK16      SK18      EA3x4(12)   EA4x4(16)
 LOW     Metropolis     1.8e4*      106         208       1.1e3     3.8e3       2.1e4
 LOW     PT             1.0e3       225-490     766       1.5e3     632         1.0e3
 LOW     PT+Houdayer    -           -           -         -         927         1.3e3
 LOW     QeMCMC [st]    20-130      25-40       cut       cut       33-51       cut
 LOW     decohered [st] 248         246         cut       cut       170         cut
 MED     Metropolis     242         272         269       889       111         146
 MED     PT             251         224         303       638       155         221
 MED     QeMCMC [st]    46-60       44-68       cut       cut       41-47       cut
 MED     decohered [st] 207         126         cut       cut       126         cut
 HIGH    Metropolis     29          36          37        47        14          19
 HIGH    QeMCMC [st]    24          10          cut       cut       17          cut
 (* SK12 Metropolis LOW is dominated by outlier seed 1202, beta=3.8; 4/5 instances equilibrate.) Ranges = tau_E..tau_q.
 At these sizes plain Metropolis is often as good as PT in flips (PT pays for R replicas); PT matters only for the hard
 instances (heavy tail: SK12 s1202, EA4x4 LOW).
Step advantage S = tau_PT[flips] / tau_QeMCMC[steps] (= the largest cost R of one quantum step at which pure QeMCMC
 would break even with PT):
   LOW : SK12 7.9 [4.5,13], SK14 10 [8.0,19], EA3x4 18 [7.0,18]
   MED : SK12 4.2 [2.9,7.4], SK14 3.7 [2.6,5.7], EA3x4 5.9 [2.6,7.5]
   HIGH: SK12 2.1 [1.2,2.3], SK14 3.5 [3.3,3.7], EA3x4 1.1 [1.0,1.3]
 vs best classical (equilibrated Metropolis/PT/PT+Houdayer): LOW 7.7-18, MED 3.7-5.2, HIGH 0.8-3.3.
 Decohered control vs PT: LOW 1.1-4.0, MED 1.1-1.9, HIGH 1.4-2.5 -> part of the HIGH/MED "advantage" is classical
 large-jump proposals; quantum beats its own decohered control clearly only at LOW (tau 20-50 vs 170-250 steps, acc
 0.04-0.09 vs 0.007-0.011).
Hybrid PT + quantum move (tau_sweeps / tau_PT_sweeps): p_q=0.01 ~1.0, 0.1 ~0.9-1.0, 0.5 0.75-0.87, 1.0 0.58-0.73
 (LOW/MED). Decohered move: 0.6-1.0, i.e. comparable to the quantum move inside PT (best: SK12 LOW 0.61 for D1.0).
 Break-even cost per quantum move (max R at which PT+Q beats plain PT): median 2-23 flips for p_q >= 0.1, up to ~100
 flips for p_q = 0.01 (noise-dominated, IQR includes 0).
Best p_q per R: p_q = 0 (plain PT, no quantum move) for every family and regime at R = 1e3, 1e6 and 1e8 (one SK12
 instance picks 0.01 at R=1e3, within noise). Cost(best)/cost(PT) = 1.
Wall-clock: R=1e6 and R=1e8: zero (instance, regime, sampler) combinations beat the best classical method. R=1e3: 2 of
 ~90 (SK12 seed 1202 LOW, the outlier where every classical tau is large).
Equilibration (t_eq to 1%): classical PT 300-1200 flips LOW, 600-3500 MED; QeMCMC 64-128 steps at LOW n=12 (SK, EA);
 most other QeMCMC t_eq are nan because the capped ensembles (256/128 steps) never stabilised within 1% - not
 reliable, reported as not measured.

CONCLUSION (shown by own simulation, ideal, n <= 14 for quantum, n <= 18 classical)
 Against a tuned PT baseline the QeMCMC step advantage per regime is ~8-18x at LOW, ~4-6x at MED, ~1-3.5x at HIGH, i.e.
 the break-even cost of one quantum step is 1-20 single-spin flips. With realistic cost R >= 1e6 flips per quantum step
 (BRIEF-screening: IBM ~1e8) no sampler, pure or hybrid, ever wins; even R = 1e3 never wins except one outlier. As a
 move inside PT the quantum move reduces PT's tau by at most ~1.7x (p_q = 1) and the decohered control does about as
 well, so the optimal p_q is 0 for all R tested. Arithmetic bound (own calculation): S cannot exceed tau_PT[flips]
 (~1e2-1e3 here) since tau_Q >= 1 step, so R >= 1e6 is excluded at these sizes independent of noise.
 Speculation: S at LOW grows with n (8 -> 10 from n=12 to 14) but would need ~1e5-1e7x growth to matter at R=1e6-1e8.

CUTS / NOT RUN (machine overload, coordinator limits: max 2 processes, then finalize)
 - Quantum and decohered runs at n=16 (SK and EA 4x4) and n=18: cut (speed above). EA quantum runs done on 3x4 (n=12)
   instead; EA 4x4 has Metropolis/PT/PT+Houdayer only.
 - Decohered hybrid only p_q in {0.1, 1} (not 0.01, 0.5). No hybrid at HIGH for n=14 (pure QeMCMC only).
 - Quantum chains time-capped (n=12 45 s, n=14 75 s per hybrid; 2x for pure chains): p_q >= 0.5 hybrids have
   N = 1e3-2.5e4 sweeps; SK14 HIGH pure QeMCMC only 1260 steps. Overlap q is overlap with the ground state, not the
   two-replica overlap. No equilibration measure for hybrids. No noise model.
