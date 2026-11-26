D7 QUANTUM-INSPIRED CG-QeMCMC (implementation idea 10): classical statevector simulation of the coarse-grained
group proposal, compared in CPU time against exact block heat-bath on the same groups, single-spin Metropolis
and tuned parallel tempering (PT, and PT + Houdayer for 2D EA). Date 2026-11-21. Agent D7.

VERDICT (shown by own simulation, ideal/noiseless, plus an own proof):
 (a) vs exact block Gibbs (block heat-bath, HB) on the SAME group: NEVER better. Per step the quantum group move
     is provably at most 2x better than HB (theorem below). Measured exact at n=10 it is 3-9x WORSE per step
     (gap ratio q/HB 0.11-0.35, all 30 cases). Per CPU second it is 10x (k=4) to 130x (k=12) more expensive
     per move on top of that. In the large-n runs there are 18 apparent per-step wins over HB (ratio 1.1-360x, all
     k=4, MEDIUM/LOW). The 15 cases above 2x violate the proved bound, so they are short-run IAT artifacts. The 3
     cases at or below 2x are within noise. Per second they all lose except where the IAT is a short-run artifact.
 (b) vs tuned PT / Metropolis (best of the two, per regime): NEVER better per CPU second. The quantum move was faster in 0 of 720 censoring-aware
     comparisons (6 sizes x 3 regimes x 5 instances x 4 quantum configs x {E, Hamming}). It lost 702 and 18 were
     undetermined. The decohered control lost 173 of 180, with 7 undetermined. Typical factor: 1e2-1e4 slower.
 => Idea 10 as a "quantum-inspired only" sampler: KILL. The classical part of the idea (state-independent group
    moves) is valid, but its best form is exact block heat-bath. Even that loses to Metropolis/PT per CPU second
    on SK and 2D EA at these sizes. HB is never best here; the closest case is the cluster partition on EA at
    LOW/MEDIUM, where it is the best group move but still 2-30x slower than PT+Houdayer.

THEOREM (own calculation, rigorous): fix any state-independent group distribution p_g. For each g let P_g be any
kernel that changes only the spins in g and is reversible with respect to pi. That covers the quantum proposal plus MH, the
decohered control, and any mixture over (gamma,t). On each fiber (rest of the spins frozen), P_g is a reversible stochastic matrix whose eigenvalues lie in [-1,1]. It fixes
functions of the frozen spins. Block heat-bath is the orthogonal projection Pi_g onto those functions. Hence
I - P_g <= 2 (I - Pi_g) as operators on L2(pi). Summing over g: Dirichlet form E_Q(f) <= 2 E_HB(f). So
gap(CG-Q) <= 2 gap(CG-HB), and for every observable f, tau_f(Q) >= (tau_f(HB) - 1)/2 (operator monotonicity of
the inverse). So no group proposal, quantum or not and in hardware or in simulation, can beat exact block
Gibbs on the same groups by more than 2x per step. Exact Gibbs on a k-spin group costs O(k 2^k), which is about
1 / 10 / 150 us for k = 4 / 8 / 12 on this CPU. This also bounds the hardware CG-QeMCMC (P2): at k <= ~25 its step
advantage over classical block Gibbs is <= 2, so the break-even S* vs block Gibbs can never be reached
(hardware t_Q ~ 0.03-3 s per step vs ~1e-4 s for 12-spin HB).
Detailed balance of all moves used here: single group per step, groups chosen independently of the state
(random consecutive block, random k-subset, or a fixed partition computed once from |J|). The quantum
proposal is symmetric: H_g is real symmetric, and the effective field depends only on the frozen spins, which
are identical in s and s'. alpha_g also depends only on those. The decohered proposal is symmetric because
|e^{-iH dt}|^2 is symmetric. Checked numerically: the energy distribution matches exact Boltzmann (SK n=8),
z-scores < 0.7 (results/validate*.txt/json). The P2 fixed-order multi-group sweep was NOT used.

CPU TIME PER MOVE (single thread, scalar C -O3, i5-1135G7. results/timing_iso.json is one process, re-timed
at the end. results/timing.json was taken earlier under heavy load. The two agree within ~1.5x.)
 Metropolis sweep: 5 us (SK64), 14 us (SK128), 8 us (EA16), i.e. ~30-110 ns per spin attempt.
 PT sweep (all replicas): 11-250 us. Houdayer roughly doubles it (2 replica sets).
 Block heat-bath:   k=4: 1.6-1.9 us    k=8: 10 us     k=12: 150-175 us
 Quantum CG move:   k=4: 18-31 us      k=8: 0.6-0.8 ms  k=12: 15-18 ms   (Chebyshev, ~60/~140/~250 terms;
                    scipy expm_multiply in Python is ~1e3x slower at k=4 and ~1-2x slower at k=12)
 Decohered control: k=4: 0.2-0.3 ms    k=8: 6-10 ms   (one evolution per dt=0.25 slice)
 Cost ratio q/HB on the same group: ~12x (k=4), ~60x (k=8), ~110x (k=12).

INSTANCES AND REGIMES
 SK: qmc.sk_instance(n, seed), J,h ~ N(0,1) unscaled, n = 32, 64, 128, seeds 1-5. beta_c := 1/sqrt(n) by design.
   Verified with the Metropolis specific heat (results/calib_partial.csv, 2 s runs, seeds 1-3): the C/n peak sits at
   beta/beta_c ~ 1.2 for n = 32, 64 (and the n=128 curve was still rising at 1.2 when the run was stopped), C peak ~0.43.
   So T_c ~ 0.8 sqrt(n) at these sizes, and the field shifts it. The local energy IAT starts growing at beta/beta_c ~ 1.5-2.
   Targets: HIGH beta/beta_c = 0.5, MEDIUM = 1.0 (near the C peak, but Metropolis IAT(E) is still only 2-3 sweeps
   at these n), LOW = 3.0 (the Hamming-to-ground-state IAT of Metropolis is long or unresolved).
 2D EA Gaussian, periodic, L = 8, 12, 16, seeds 1-5, T_c = 0. Calibrated Metropolis IAT(E): T=2: 2 sweeps,
   T=1.0: 12-17, T=0.8: 23 (L=8) / 90 (L=12) / 80 (L=16), T<=0.6: hundreds to >1e3 and unresolved.
   Targets: HIGH T=2.0, MEDIUM T=0.8 (Metropolis IAT ~100 sweeps at L=12-16), LOW T=0.4.
 PT ladders: geometric in beta from 0.3 beta_c (SK) or T=2.0 (EA) to the target. R is the smallest value with min swap
   rate >= 0.2 in a 2 s pilot (results/pt_tuning_*.json): SK R = 4/6 (n=32), 4/8 (64), 6/12 (128) for MED/LOW.
   EA R = 4/6, 6/10, 6/10. The EA MEDIUM R was tuned at T=1.0 and rescaled to T=0.8 at constant d(ln beta), giving R=6/8/8.
   Houdayer acts at all temperatures with beta >= 1. HIGH uses Metropolis only (PT is unnecessary there).
 Reference state for the Hamming observable: the lowest-energy state of a 7.5 s PT(+Houdayer) run (results/refs).

RUN PROTOCOL (results/runs/*.json, 1,086 runs)
 Each (instance, regime, method) run has an equal CPU budget of 3 s (sk32 seed 1 and part of sk64 seed 1: 4 s) and
 starts from a random state. Records: Metropolis every sweep, PT every PT sweep, group moves every round(n/k) moves (one
 "CG sweep"). IAT uses the Sokal window (qmc.iat) after discarding 25%. "Resolved" means N_post/tau >= 50 AND
 N_post >= 1000 records. Equilibration t_eq = first CPU time at which E <= <E>_ref, where <E>_ref is the
 second-half mean of the PT+H / PT / Metropolis run.
 Methods: metro; pt; pth (EA); hb k=4 block, k=8 block/subset/cluster, k=12 block (sk32 also has all 9 hb
 combinations); q k=4 block, k=8 block/cluster, k=12 block; dec k=8 block (sk32 also has dec k=4).
 Gamma ~ U[0.25,0.6] and t ~ U[2,20] are drawn per move. alpha_g = sqrt(k)/sqrt(sum J_g^2 + sum h_eff^2) (Layden form).
 Censoring rule (verdict_clean.py): a ratio counts FOR the quantum move only if the quantum run is resolved, and AGAINST
 it only if the competitor is resolved. Otherwise the pair is UNDETERMINED.

RESULTS (medians over 5 instances, full table in results/compact_table.txt and results/table_medians.csv)
 IAT(E) per move [per CPU second], largest sizes:
  SK128 HIGH  : metro 1.3 sweeps [3.4e-5 s] | HB k8 31 [3.5e-4 s] | Q k4 357 [6e-3 s] | Q k8 125* [8e-2 s] | Q k12 7* [0.13 s]
  SK128 MEDIUM: metro 2.7 [4.5e-5] | PT 2.3 [3.4e-4] | HB k8 cl 106 [1.1e-3] | Q k4 675 [1.3e-2] | Q k8 cl 124* [7.9e-2]
  SK128 LOW   : metro 5.0 [3.5e-5] (Hamming 1.7e-2 s) | PT 3.7 [6.9e-4] (H 1.1e-2) | HB k8 cl 117 [1.2e-3]
                | Q k4 3.6e3 [6.1e-2] (H 0.24*) | Q k8 375* [0.23]
  EA16 HIGH   : metro 1.9 [2.3e-5] | HB k8 cl 69 [8e-4] | Q k4 920 [1.7e-2] | Q k8 cl 140* [0.11]
  EA16 MEDIUM : metro 63 [6.9e-4] | PT+H 3.2 [5.7e-4] (H 1.0e-2) | HB k8 cl 370 [4.0e-3] | Q k4 2.0e3 [3.9e-2] | Q k8 325* [0.24]
  EA16 LOW    : metro 3.0e3 [2.3e-2] | PT+H 3.6 [8.7e-4] (H 1.1e-2) | HB k8 cl 3.0e3 [3.1e-2] | Q k4 9.9e3* [0.17] | Q k8 383* [0.26]
  (* = unresolved in most instances. Since tau_sec > ~budget/50 ~ 0.05 s for those, they are still >= 30x slower than
   the best classical method.)
 Per step, same group, both runs resolved (results/perstep_both_resolved.txt): HB/Q ratio median 0.2-0.3 for k=4
   (HB is 3-5x better per step) and 0.25-0.6 for k=8, consistent with the exact n=10 result. The few resolved-pair
   ratios > 2 (k=12, dec, LOW) have quantum chains of only ~10^3 records, which never visit the slow mode, and they break the
   theorem. They are treated as artifacts.
 Exact n=10 SK (exact_bound.py, 5 instances, groups = all 10 consecutive blocks with wrap, m=16 (gamma,t)
   draws, results/exact_bound_n10.*): gap(Q)/gap(HB) median 0.29/0.27/0.29 (k=4) and 0.23/0.18/0.18 (k=6) at
   beta/beta_c = 0.5/1/3. Decohered/HB 0.29/0.20/0.12 (k=4) and 0.19/0.11/0.04 (k=6). So interference does help the
   quantum move over its decohered control by 1-4.5x at LOW, but both remain far below block Gibbs.
 Group choice: the cluster partition (from |J|) helps HB most on EA LOW/MEDIUM (k=8 cluster is 5-10x better per
   second than a k=8 block). On SK, block, subset and cluster are within ~2x.
 Equilibration (first passage to <E>_ref): Metropolis/PT 1e-3 to 3e-2 s; HB 1e-3 to 0.2 s; Q k4 2e-3 to 0.15 s;
   Q k8 0.1-2.5 s; Q k12 0.3-2.7 s or not reached in 3 s.

WHAT WAS ONLY REASONED (not run): the theorem above (a proof, checked numerically at n=10). The statement that the
 bound also applies to hardware CG-QeMCMC (it follows from the proof; noise only makes the hardware move worse). No GPU or SIMD
 tuning of any method was done. A vectorised HB and Metropolis would widen the gap further.
CAVEATS: the machine was heavily oversubscribed (load 18-66). Times are thread CPU time, which is robust to time
 slicing, but SMT and cache contention inflate them by up to ~1.5x for all methods alike. Budgets of 3 s leave most
 Q k>=8 IATs unresolved. That cannot change the per-second verdict because the gap is >= 30x. SK sizes are small
 (n <= 128), and at MEDIUM Metropolis already mixes E in 2-3 sweeps.
BREAK-EVEN (BRIEF-screening convention): vs exact block Gibbs on the same group S <= 2 (proved), while S* = t_Q/t_HB
 >= 0.03 s / 1.5e-4 s ~ 2e2 even for the optimistic D-Wave latency and a k=12 group. Hardware cannot break even, at any noise level.

REPRODUCE (from this folder; OMP_NUM_THREADS=1):
 gcc -O3 -march=native -fPIC -shared -o libcgmc.so cgmc.c -lm
 python validate.py ; python validate_long.py          # kernel correctness (Bessel, expm, Boltzmann)
 python exact_bound.py                                 # exact n=10 gap/IAT ratios vs block heat-bath
 python timing.py ; python timing_iso.py               # CPU time per move
 python calib.py sk ; python calib.py ea               # regime calibration (runs were stopped early; partial -> calib_partial.csv)
 python tune_pt.py sk ; python tune_pt.py ea           # PT ladder sizes
 ./queue.sh   (= python run_exp.py {sk 32|64|128, ea 8|12|16} 3.0)   # main runs, seeds 1-5
 python analyze.py ; python verdict_clean.py           # tables, verdict, plots
FILES: cgmc.c (C kernels: Metropolis, PT+Houdayer, CG heat-bath / quantum (Chebyshev-Bessel exact statevector)
 / decohered moves), cg.py (ctypes driver, cluster partition), config.json, results/*.csv|json|txt, plots/*.png
 (cpu_per_move, iatE/iatH_per_cpu_second, exact_gap_ratio_vs_hb).
Seeds: instances 1-5. Chain seeds 10*seed+{1,2,3}. Ref PT 999+seed. Calibration 100+seed. Tuning 77+seed.
