E3 RED TEAM: HARDWARE CLAIMS D3 (noise threshold), D4 (native-subset U), BUILD-NOW calibration rows (K0, K3, B3-04)
Date 2026-11-21. Plain text. Labels: [sim-ideal] / [sim-noisy] = own exact simulation; [model] = own global-depolarizing
model; [derived]; [speculation]; [lit] with arXiv ID.

WHAT WAS RUN (this folder, OMP/OPENBLAS/MKL_NUM_THREADS=2, machine load ~16, at most 2 processes)
  e3lib.py   stronger classical kernels, all exactly reversible w.r.t. Boltzmann pi:
             tuned local+uniform mixture (weight on local 0,0.1..1); random-block heat-bath with exact FULL-energy
             conditional (all pairs, all triples, native edges, native connected subtrees of size 3 and 4), each also
             mixed with MH-uniform (w 1/.75/.5/.25, best kept); tree independence sampler q ~ exp(-bq E_native)
             (exactly sampleable in O(n) on the native tree; Hastings accept with full E; bq = beta/2, beta; also
             50/50 mixed with local MH). Deep-circuit tilt bias (see 1c).
  python claim1.py  -> results/claim1.json, logs/claim1.log  (~1 min). Uses D3 cached exact Q (D3-noise/cache) and D3
             instance/regime definitions (SK seeds 100-104, n=6 grid gamma{.3,.5} x t{2,6}; n=8 cache is t=2 grid).
  python claim2.py  -> results/claim2.jsonl, results/claim2_summary.txt, results/claim2_Q_n8.npz (~10 min).
             Exactly D4's instances, embedding (native_subset.best_embedding) and draws (qmc.draw_params(0,16));
             reproduces D4 gap_native to all printed digits (checked all 5 n=8 seeds and n=10 seed 0).
             Noise: per draw F_k = (1-2e-3)^N2q_k, N2q_k = 2 x edges x r(t_k), r(t) log-log interpolated from D4's SK n=10
             Trotter table 5/17/43/86 at t=2/6/12/20; Q_noisy = mean_k [F_k Q_k + (1-F_k) U]; variant "ro" multiplies
             F by (1-1.67e-2)^n. "short" = same gammas, t ~ U[2,6] (rng seed 1).
  python claim3.py  -> results/claim3.json, logs/claim3.log (~5 min). Proposal-matrix tomography: N shots per start
             state, multinomial, symmetrised (Q+Q^T)/2 with diagonal fixed, 20 replicas; cost 0.3 ms/shot, $96/QPU-min
             [own estimate]. Sequential chain: 1000 steps, 100 replicas, Sokal IAT of energy, quantum vs tuned mixture.

CLAIM 1 (D3 noise threshold)
  (a) Strongest attack: the threshold is a circuit-fidelity number, not an MCMC number.
      [derived] Global depolarizing makes Q_noisy = F Q + (1-F) U exactly, MH is linear in Q, and the Dirichlet form is
      linear, so 1-lambda_2(P_noisy) >= F (1-lambda_2(P_Q)) + (1-F)(1-lambda_2(P_U)). The only MCMC inputs are S_ideal and
      rU = gap_U/gap_best; when uniform is near-best (rU -> 1) S can never fall below ~1, so eps* is undefined; this is
      the "S->1 from above" D3 itself saw. eps* is soft by construction.
      [own calc] eps_half x <N2q> = 2.6e-3 x 150 = 0.39 (n=6) and 2.3e-3 x 168 = 0.39 (n=8): constant. So
      eps_half ~ 0.39/N2q, i.e. ln2/(a N2q) with a ~ 1.8 (F alone with a=1 gives 4.8e-3 / 4.1e-3; a=1.35 gives 3.5e-3 /
      3.0e-3). It measures circuit depth. With S_ideal-1 = 0.4-0.7 it would not resolve anything else either.
  (b) Baseline is weak. [sim-ideal] Ideal S vs best of {tuned mixture, pair-HB, triple-HB} (5 seeds, median [IQR]):
      n=6 LOW 0.62 [0.32,1.69] (vs mixture 1.69), MEDIUM 0.53 [0.36,0.99] (vs mixture 1.43), HIGH 0.47;
      n=8 (t=2 grid) LOW 1.06 [1.05,1.11] (vs mixture 1.22), MEDIUM 0.68, HIGH 0.49.
      A 3-spin exact heat-bath (8 energy evaluations per step, still ~ns) removes the ideal advantage at n=6-8 in most
      instances. Noisy [sim-noisy]: dep eps=2e-3 n=6 LOW 0.53; FakeMarrakesh n=6 vs best 0.30 (LOW), 0.59 (MEDIUM),
      0.66 (HIGH); vs mixture 0.93 / 1.09 / 0.91 (reproduces D3).
  (c) T1 bias at D4 depths. [derived] If the circuit is deep enough that F ~ 0 (SK n=10 t=6: 2,160 CZ, F ~ 3e-3), the
      proposal becomes row-independent q(s). Plain Metropolis with an independent q has stationary pi' ~ pi q exactly.
      T1 plus readout asymmetry give q ~ prod (1 +- z)/2, a uniform-field tilt mu = atanh z. The bias then does NOT
      shrink or average: it saturates at a z-set value. [own calc] TVD(pi, pi'), median over 5 seeds:
        z=0.1: n=6 LOW 0.003 / MED 0.059 / HIGH 0.097;  n=8 LOW 0.021 / MED 0.081 / HIGH 0.114
        z=0.2: n=6 LOW 0.005 / MED 0.126 / HIGH 0.197;  n=8 LOW 0.052 / MED 0.160 / HIGH 0.230
      [speculation, rough] Heron z ~ 0.05-0.2. Gate-level AD 3e-4 against 2.1e-3 depolarizing gives a fixed point of
      ~0.12; ~50 us circuits at T1 ~250 us add idle relaxation; asymmetric readout adds ~0.01. The drive partly rotates
      this away. So D3's bias claim survives qualitatively and gets worse: TVD 0.1-0.2 at MEDIUM/HIGH is plausible.
      Pauli twirling removes the tilt (it makes the channel unital). Readout twirling plus the mirrored pre-flip removes
      the readout part. A palindromic schedule is not needed for the tilt itself.
  Revised verdict: the D3 physics is correct, but eps* and eps_half are restatements of F = (1-eps)^N2q.
  What a Heron run of dense SK n=6-10 will show: S vs tuned mixture 0.9-1.1 (n=6), and below 1 vs a 3-spin heat-bath.
  The other result is a fidelity-collapse curve S = 1 + (S_ideal-1)F^a with no advantage left, plus a temperature-rising
  T1/readout bias of 1e-3 to 2e-1 TVD that twirling can remove. That is a noise-characterisation result, not a
  sampling-advantage threshold.

CLAIM 2 (D4 native-subset U)  [sim-ideal] / [model], 5 seeds, median [IQR]
  N2q per circuit (mean over the 16 draws): n=8 637 (F 0.34) with t in [2,20]; 155 (F 0.74) with t in [2,6].
  n=10: 819 (F 0.26); 199 (F 0.68).
                      beta=1.0 n=8                    beta=1.0 n=10                 beta=0.3 n=8 / n=10
  vs best(loc,uni)    3.34 (D4, reproduced)           2.59 (D4)                     1.89 / 1.59 (D4)
  ideal vs tuned mix  1.67 [1.65,2.61]                1.68 [1.34,2.53]              1.18 / 1.00
  noisy t<=20 vs mix  0.91 [0.89,1.47]                1.11 [0.94,1.15]              0.87 / 0.65
  noisy t<=6 vs mix   1.42 [1.30,1.98] (ro 1.33)      1.37 [1.12,2.05] (ro 1.29)    1.08 / 1.00
  ideal vs best cl.   0.24 [0.19,0.35]                0.22 [0.20,0.36]              0.48 / 0.45
  noisy t<=6 vs best  0.19 [0.11,0.30]                0.18 [0.16,0.48]              0.47 / 0.36
  decohered vs mix    0.70                            0.43                          0.73 / 0.71
  Best classical is the tree independence sampler (all n=8 cases, 3 of 5 at n=10) or the native 4-subtree heat-bath
  (2 of 5 at n=10). Gap over the tuned mixture: tree independence 10.9x (n=8) and 4.0x (n=10); native 4-subtree HB
  4.4x / 2.7x; pair HB only 1.15-1.35x.
  (a) Half of D4's 2.6-3.3x comes from tuning the local/uniform mixture. A classical move that uses the same native-
      coupling information beats the native quantum proposal by 4-5x at beta=1 and 2-3x at beta=0.3, at n=8-10.
      Caveat [speculation]: independence samplers decay exponentially with n. Block heat-bath and tree/low-treewidth
      conditional moves do not decay that way. The heavy-hex subgraph has treewidth <= ~4, so it stays exactly
      sampleable classically at any n.
  (b) With D4's own t ~ U[2,20] draws, the gain over the tuned mixture is gone on Heron (0.9-1.1x). Short t (2-6) keeps
      1.3-1.4x over the mixture only.
  (c) Novelty: this is not P2. P2 freezes spins and quantises a group; native-subset keeps all spins and drops
      couplings inside U. It is a special case of "any H_prob in U keeps symmetry" (P1) and of the surrogate idea
      (D5 here; Kawamata & Fujii arXiv:2611.05883 with neural surrogates). One web search found no paper doing heavy-hex
      coupling sparsification [lit search shallow]. Orfi & Sels arXiv:2408.07881 predicts the loss: the sparse quench
      detunes the fine-tuned intermediate regime.
  Verdict: NOT an advantage claim. The interesting part is the CZ reduction. On the physics, a classical sampler
  given the same native information wins.

CLAIM 3 (BUILD NOW calibration rows)  [model] shot simulation
  Tomography resolves S. At n=8 native short-t, N=1024 shots per row (2.6e5 shots, ~$126) gives sd 0.07-0.16 on S
  (S_true 0.90-2.08); N=4096 (~$500) gives sd 0.05-0.09. At n=6 FakeMarrakesh, N=1024 ($31) gives sd 0.03-0.11 for
  S_true 0.86-1.17. Shot noise is not the blocker; the weak baseline is. S>1 is resolvable only against the tuned
  mixture, never against the native heat-bath or the tree sampler. Note: the symmetrised estimator hides the
  asymmetry/bias, so measure the asymmetry separately.
  The sequential chain is uninterpretable. With 1000 steps, the coefficient of variation of IAT is 0.48-0.58 per
  chain. P(q-chain IAT < classical IAT) = 0.49-0.70 even where S_true ~ 2. Cost [estimate]: 1000 jobs x 2-3 s =
  33-50 QPU-min, $1.6k-4.8k at $48-96/min, which is over budget and below resolution.
  K3 (3x4 lens, 4096 start states) [speculation, extrapolated]: total shots scale roughly with dim^2 at fixed sd
  (n=6 -> 8: 16x shots for similar sd), so about 250x the n=8 cost, ~$30k. Do it at n<=8, or measure only
  symmetry/bias on sampled rows.
  K0: interpretable only as a fidelity curve (claim 1).
  B3-04 (native +-J bed, exact Kasteleyn Z): it has the most value of the three, as a bias/symmetry calibration.
  Measure low-dimensional marginals (E, M histograms) from tomography-built offline chains (P1 style), not from a live
  chain. A TVD of 0.05 in a marginal needs ~1e3-1e4 effective samples, which is affordable.
  Verdict: K0 and B3-04 are worth running as noise/bias calibration (<= $150 each at n<=8). Present them as
  calibration, not advantage. Drop K3 at full size.

FILES: e3lib.py, claim1.py, claim2.py, claim3.py; results/claim1.json, claim2.jsonl, claim2_summary.txt, claim2_Q_n8.npz,
claim3.json; logs/claim{1,2,3}.log.
NOT DONE: PT/cluster baselines (would only strengthen the attack); real-device T1 fixed-point simulation at 2,160 CZ
(z range is reasoned); idle noise; n>10.
