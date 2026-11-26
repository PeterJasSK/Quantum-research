D3 NOISE SENSITIVITY OF THE QeMCMC PROPOSAL, PER TEMPERATURE REGIME (QHop applied review, Wave 4)
Date 2026-11-21. Plain text. Labels: [sim-ideal] / [sim-noisy] = own exact simulation, [model] = own global-depolarizing
model, [derived] = own derivation, [speculation].

WHAT WAS RUN (all from this folder; OMP/OPENBLAS/MKL_NUM_THREADS=2; machine heavily shared, run times below are under load)
  dmsim.py            exact density-matrix simulator. Q_noisy[a,b] = <b|E(|a><a|)|b> computed EXACTLY for every basis
                      input at once (no shots, no trajectories). Logical all-to-all circuit, native RZZ, virtual RZ.
                      Circuit = 2nd-order Strang Trotter, r = 2*round(t)+1 (odd) steps, built as a literal palindrome
                      (checked, is_palindrome). Ideal Trotter unitary: max|U - U^T| <= 1.4e-15 for all instances;
                      1st-order Trotter control: max|U-U^T| = 0.23 (n=6).
  symmetry_checks.py  n=4 (seed 1) and n=6 (seed 100), gamma=0.4, t=3: which noise keeps Q symmetric, gauge/twirl/readout
                      fixes, placement 'after' (Aer convention) vs 'split' (half channel before+after = noise during gate).
                      -> results/symmetry_checks.json, logs/symmetry.log
  sweep.py            one instance per call, cache/<fam>n<n>_s<seed>.npz. Commands actually run: see run_queue.sh (final;
                      run_all.sh / run_n8.sh were started and killed when the machine overloaded, their finished keys
                      were kept in the caches).
  aer_fake.py         (v) FakeMarrakesh (Heron r2) and FakeBoston (Heron r3): same logical circuit transpiled
                      (opt level 1, seed 7), AerSimulator density_matrix + NoiseModel.from_backend, save_probabilities
                      (exact, no shots); readout matrix applied analytically from backend properties; gauge pair for
                      Marrakesh. run_fake.sh / run_queue.sh.
  analyze.py          regimes, gaps, stationary bias, Hastings, global-depolarizing model (n=6,8,10 SK and 3x3 EA)
                      -> results/all_rows.csv (1455 rows), results/instances.json. 4 min.
  summarize.py, eps_half.py -> results/summary.txt, thresholds.json, fit_a.json, plots/S_vs_eps.png,
                      plots/bias_vs_eps.png, plots/afit.png.

PARAMETERS
  SK: qmc.sk_instance(n, seed), seeds 100-104 (5 instances) at n=6, 8, 10. EA 3x3 periodic gauss, seeds 200-204.
  Proposal grid: gamma in {0.3, 0.5} x t in {2, 6} (n=6 exact, all models); n=8 exact and fake backends: t=2 only
  (cost). Each grid point used with prob 1/4 (Q = grid mean). alpha = qmc.alpha_from_energy.
  N_2q (logical RZZ) per circuit: n=6 90/210 (t=2/6), n=8 168/392, n=10 270/630; N_1q = n*r.
  Transpiled heavy-hex n=6 t=2: 351 CZ per circuit (Marrakesh and Boston).
  Noise (eps = average 2q gate infidelity): dep: 2q depolarizing lambda=4/3 eps after every RZZ, 1q depolarizing at
  eps/10 after every RX. deph: Z-dephasing p=eps on both qubits of every RZZ, eps/10 per RX. ad: amplitude damping
  gamma=eps on both qubits per RZZ, eps/10 per RX (Heron: gamma = t_2q/T1 ~ 70 ns / 250 us ~ 3e-4 per gate, [derived]).
  readout: per-qubit flip, symmetric p or asymmetric p(0->1)=0.5p, p(1->0)=1.5p, p in {1e-3..5e-2}.
  eps grid {1e-4, 3e-4, 1e-3, 2e-3, 5e-3, 1e-2}.
  Regimes per instance: beta_c = specific-heat peak (SK n=6: 0.50-0.79, n=8: 0.35-0.71, n=10: 0.32-0.40, EA 3x3: 0.56-1.0; per
  instance in instances.json); beta_loc = where the local gap falls to half its maximum (SK 0.10-0.28, EA 0.18-0.22,
  i.e. local mixing starts to collapse well before the C peak). LOW = 3 beta_c, MEDIUM = beta_c, HIGH = beta_c/3.
  Best classical = max gap over {local, uniform, 0.25/0.5/0.75 local+uniform mixtures} (PT and cluster moves not
  implemented here: they are multi-chain/non-comparable at gap level; so "best classical" is weak, as in P1).
  Decohered control: qmc.decohered_Q on the same grid.

IDEAL STEP ADVANTAGE (S = gap_q / gap_best_classical, median [IQR], 5 seeds) [sim-ideal]
  n=6 Trotter grid: LOW 1.69 [1.39,2.30]  MEDIUM 1.44 [1.04,1.47]  HIGH 0.73 [0.71,0.90]
  n=8 Trotter grid t=2 only: LOW 1.26 [1.11,1.78]  MEDIUM 1.29 [1.13,1.39]  HIGH 0.76
  n=8 grid t in {2,6}: LOW 2.81 [2.1,3.16] MEDIUM 1.67 HIGH 0.81; n=10: LOW 4.50 [3.99,6.21] MEDIUM 1.91 HIGH 0.86
  EA 3x3: LOW 2.45 MEDIUM 2.12 HIGH 1.05.  P1-style continuous (m=16 draws): n=6 LOW 2.29, n=8 LOW 4.04.
  Decohered control: S = 0.02-0.53 everywhere (the gain is coherent).
  At these n the ideal S is small (1.3-4.5x); HIGH regime has no ideal advantage at all (S<1).

THRESHOLDS (median over seeds; S from PLAIN Metropolis with Q_noisy) [sim-noisy] / [model]
  eps* = S falls to 1;  eps_half = excess (S-1) halved.
  noise            n   LOW: eps* / eps_half         MEDIUM: eps* / eps_half      HIGH
  dep  exact       6   8.7e-3 / 2.6e-3               >1e-2 (S=1.09) / 5.7e-3      S<1 ideal; noise RAISES S toward 1
  dep  exact       8   9.4e-3 / 2.3e-3 (t=2 grid)    9.7e-3 / 3.1e-3              same
  dep  model       10  >1e-2 (S->1 from above) / 1.2e-3   3.1e-3 / 1.2e-3         same
  deph exact       6   >1e-2 (S=1.11)                >1e-2                        same (only 2-5 seeds per eps, noisy median)
  ad   exact       6   6.6e-3 / 2.8e-3               >1e-2 (S=1.12) / 7.6e-3      same
  ad gauge pair    6   >1e-2 / 6.6e-3                >1e-2 / 7.4e-3
  ad Pauli twirl   6   >1e-2 / 3.4e-3                >1e-2 / 7.6e-3
  readout sym/asym 6,8 never in 1e-3..5e-2 (S 1.45 at p=5e-2, n=6 LOW): readout alone barely costs gap
  FakeMarrakesh n=6 (351 CZ, F_eff 0.55): S LOW 0.93 [0.83,1.11], MEDIUM 1.09, HIGH 0.92 -> advantage gone (ideal t=2
     grid S LOW 1.14, MEDIUM 1.04). FakeBoston (Heron r3, F_eff 0.70): LOW 1.12, MEDIUM 1.17, HIGH 0.89 (2 seeds only).
  Indistinguishable from uniform (row TVD(Q,U) < 0.1): model n=8 eps 6.6e-3, n=10 4.3e-3; not reached at n=6 by 1e-2.
  Key structural point: when uniform (or a uniform-heavy mixture) is the best classical proposal (LOW/MEDIUM at n>=8),
  depolarizing noise pulls Q to uniform and S tends to 1 FROM ABOVE; S<1 needs the best classical to be local-heavy.
  So eps* is soft; eps_half ~ 1.2e-3 - 3e-3 is the more useful number, and it scales ~ ln2 / N_2q.

FIT S_eff = 1 + (S_ideal - 1) F^a  (F = mean over grid of (1-eps)^N2q (1-eps/10)^N1q)  [sim-noisy] / [model]
  exact dep n=6,8: LOW a = 0.99 (1.35 with F_eff fitted from Q), MEDIUM a = 0.85 (1.16). HIGH: not meaningful (S_ideal<1).
  global-dep model n=6-10 + EA: LOW 1.10, MEDIUM 1.48. Use a = 1.0-1.5. Pessimistic break-even: with N_2q = 800 and
  eps = 2e-3 (F = 0.20) the excess S-1 is multiplied by 0.2^a = 0.09-0.20, i.e. required ideal S-1 is 5-11x larger than
  S*-1. For S* ~ 1e7-1e8 this is irrelevant compared with latency (break-even unreachable either way at these n).

SYMMETRY / BIAS [sim-noisy] + [derived]
  Exact symmetry theorem [derived, verified to 1e-15]: if the gate sequence is a palindrome of symmetric gates
  (RZZ, RZ, RX, and also IBM CZ/SX/X/RZ are symmetric matrices) and each noise channel is transpose-invariant
  (Kraus set closed under transpose: all Pauli channels) and either covariant with its gate or placed palindromically,
  then Q_noisy = Q_noisy^T. Hence: 2q/1q depolarizing (covariant) and Z-dephasing (slides through diagonal gates) give
  asym ~5e-16 at n=6 (3e-7 at n=8 = complex64 floor), stationary bias 0 -> plain Metropolis stays EXACT. P1's worry is
  about noise that breaks this, not about depolarizing.
  Asymmetric, biased:
    AD per gate: asym (mean|Q-Q^T|/mean Q) 0.10 at gamma=1e-3, 0.19 at 2e-3, 0.67 at 1e-2 (n=6); 0.28 at 2e-3 (n=8).
      Plain-Metropolis stationary TVD vs Boltzmann (n=6): LOW 2.1e-3 / MEDIUM 2.0e-2 / HIGH 3.9e-2 at gamma=1e-3;
      HIGH 0.23 at 1e-2. n=8, gamma=2e-3: LOW 0.022, MEDIUM 0.087, HIGH 0.099. Bias grows with temperature.
    readout symmetric p=1e-2: asym 0.02, TVD 1.3e-4..1.3e-3; asymmetric (0.5p,1.5p) p=2e-2: asym 0.08, TVD 1e-3..0.03
      (symmetric readout also breaks symmetry: Q M != M Q).
    FakeMarrakesh n=6 exact: asym 0.056 (no readout) / 0.075 (with readout); bias TVD LOW 8e-4, MEDIUM 0.017, HIGH 0.026.
      The dossier's sampled 0.135 (1024 shots) is about 2x the exact value: roughly half was shot noise.
    FakeBoston: asym 0.043/0.049, bias TVD 0.005-0.021.
  Hastings correction with the exact Q_noisy: bias 0 by construction; gap ratio plain/Hastings median 1.00, 10-90% range 0.99-1.04 (extremes 0.87-2.9 at the largest
  gamma; Marrakesh
  MEDIUM S_plain 1.09 vs S_hast 1.06): plain chain's extra "gap" is partly the bias. Hastings needs Q(s'|s) and
  Q(s|s'), i.e. the full noisy proposal matrix: not available beyond toy n [derived] -> not a practical fix.
  Fixes:
    Gauge / spin-reversal averaging (mask m: input s xor m, problem J_ij m_i m_j, h_i m_i, output xor m):
      does NOT restore exact symmetry for amplitude damping. Counterexample: n=2..6, every placement; n=4 gamma=1e-2
      full 2^n mask average asym 3.7e-3 ('after') / 9.3e-3 ('split'); n=6 pair {0,1..1}: 0.096 -> 0.0029 at
      gamma=1e-3, 0.68 -> 0.18 at 1e-2. Marrakesh pair: 0.056 -> 0.021, bias TVD 0.013 -> 0.005 (MEDIUM).
      Reason [derived]: Q_F[b,a] = Q_{F^T}[a,b] where F^T has Kraus K^T. For AD the jump operator transposes into the
      X-conjugated one (|0><1| -> |1><0|) but the no-jump operator K0 = diag(1, sqrt(1-g)) is diagonal, so K0^T = K0
      while X K0 X = diag(sqrt(1-g), 1). AD^T is not even trace preserving, so F_m^T != F_{complement m} and the
      average over a fixed-per-shot frame cancels only the leading population-drift term; residual ~gamma^1.6-2.
    Pauli twirling of each noise location (exact average, i.e. AD -> Pauli channel px=py=g/4, pz=((1-sqrt(1-g))/2)^2):
      exact symmetry (7e-16) IF placement is palindromic ('split'); with 'after' placement residual 1.4e-3 (g=1e-3),
      7e-3 (g=1e-2), bias TVD <= 2e-4. Requires a palindromic compiled schedule too (heavy-hex routing is not).
    Readout: twirl readout (random X before measure -> symmetric flip pbar) + mirrored classical pre-flip of the
      input with the same flip -> Q' = M Q M, exact symmetry (6e-16) for any Q symmetric; costs a little gap
      (n=6 LOW S 1.69 -> 1.59 at p=1e-2).

CONCLUSION
  shown by own simulation (ideal/noisy, n<=8 exact, n=10/EA via validated model):
  1. Depolarizing and dephasing do NOT bias plain Metropolis if the circuit is palindromic: Q stays exactly symmetric.
     Bias comes from T1 (amplitude damping), readout, and non-palindromic compiled circuits with T1; at Heron
     calibration (FakeMarrakesh) the exact asymmetry is 0.06-0.08 and the stationary TVD bias 1e-3 (LOW) to 3e-2 (HIGH).
  2. Gauge (spin-reversal) averaging reduces but provably cannot remove the AD asymmetry; Pauli twirl + palindromic
     schedule does; readout needs twirl + mirrored pre-flip.
  3. The step advantage halves at eps ~ 1.2e-3 - 3e-3 (scales ~1/N_2q), S drops to ~1 at eps ~ 3e-3 - 1e-2 for
     these tiny circuits; with a = 1.0-1.5 the erosion is roughly linear-to-faster in circuit fidelity F. On
     calibrated Heron r2 at n=6 (351 CZ) the advantage is already gone (S ~ 0.9-1.1). HIGH regime: no ideal advantage
     to lose; noise only moves the quantum proposal toward the (near-best) uniform proposal.
  speculation: at n >= 20 with dense heavy-hex compilation (N_2q >> 1000) F << 0.1 at eps = 2e-3, so the noisy proposal
     is a near-uniform proposal: the advantage requires eps well below 1e-4 or coarse-graining (small groups).

WHAT WAS CUT (machine overload, coordinator instruction max 2 processes)
  n=10 exact density matrix (d^3 = 1e9 complex: infeasible) -> global-depolarizing model only, validated at n=6
    (model eps* 8e-3 vs exact 8.7e-3 LOW; eps_half 3.3e-3 vs 2.6e-3).
  EA 3x3 exact noisy runs -> model only. n=8 exact: dep at eps {1e-3, 3e-3(1 seed), 1e-2}, ad at 2e-3 (2 seeds), t=2 grid.
  deph / adgp / adtw at n=6: 3 eps for seeds 101,102,104 (6 eps for 100,103) -> those medians mix seed subsets.
  FakeBoston: 2 seeds; FakeMarrakesh n=8: not run. Idle-qubit noise, crosstalk, leakage: not modelled.
  PT / cluster baselines not in the gap comparison (weak best-classical set, as P1).
  Break-even S* not recomputed here; use BRIEF-screening convention (S* ~1e6/1e7/5e8 class for cheap energies).

FILES: results/summary.txt (all tables), results/all_rows.csv (raw per seed/regime/variant), results/thresholds.json,
  results/fit_a.json, results/symmetry_checks.json, results/instances.json, plots/*.png, cache/*.npz (Q matrices).
