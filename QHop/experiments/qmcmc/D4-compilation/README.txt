D4 - COMPILATION / EMBEDDING COST OF ONE QeMCMC PROPOSAL CIRCUIT (Wave 4, experiment agent D4)
Date 2026-11-21. qiskit 2.3.1, qiskit-ibm-runtime 0.47.0, anaconda python3. Everything is ideal simulation plus transpilation;
nothing ran on hardware. Fidelities are a gate-count proxy (own calculation), not a noisy simulation.

WHAT WAS RUN (from this folder, OMP/OPENBLAS/MKL_NUM_THREADS=2)
  python trotter_r.py ising     -> results/trotter_r_ising.jsonl  (~2.4 h CPU on the overloaded machine)
  python trotter_r.py potts     -> results/trotter_r_potts.jsonl  (KILLED after ~6 h on coordinator request; see CUTS)
  python compile.py             -> results/compile_layers.jsonl   (~4 h wall, overloaded machine)
  python native_subset.py       -> results/native_subset.jsonl    (~45 min CPU)
  python analyze.py             -> results/costs.csv, fits.csv, thresholds.csv, trotter_r_fit.json,
                                   native_subset_summary.txt, plots/N2q_vs_n.png, plots/F_vs_n.png, plots/r_vs_t.png
  validate.py (full-r transpile check of the per-layer linear model) was written but NOT run (budget cut).
Code: d4lib.py (families, exact vs Trotter proposal, circuit builders), compile.py, trotter_r.py, native_subset.py, analyze.py.

CIRCUIT
  H = (1-g) alpha E + g sum X, alpha = sqrt(n)/sqrt(sum_{i<j} J^2 + sum h^2). Second-order (Strang) Trotter, r steps.
  On a basis-state input with Z readout the first and last half diagonal layers are pure phases, so they are dropped
  (exact for the proposal matrix; checked against Statevector to 1e-16): r X-layers and r-1 full ZZ layers.
  Potts one-hot: q qubits per site, XY ring mixer per site ((XX+YY)/2 terms), ring split into edge-colour classes,
  palindromic inside each step; one-hot weight is conserved exactly. Potts alpha = sqrt(sites)/std(E) (own choice).
  Detailed balance: every variant keeps H real symmetric, so U = U^T and the ideal proposal is symmetric (P1 argument);
  native-subset Q asymmetry measured <= 1.1e-16.

FAMILIES (fixed seeds, see d4lib.py)
  SK dense J,h~N(0,1) (qmc.sk_instance seed 1000+s); CG = group of k spins cut from a parent SK of k^2 spins with frozen
  random rest -> effective fields; COUL = random points in unit square, J_ij=-1/r_ij (dense long-range, no field);
  EA = 2D open-boundary LxL, J~N(0,1); HH = Ising on heavy-hex subgraphs of the Heron 156q map (12 = one hexagon cell;
  27/60/100 = BFS ball); POTTS3/4 = 3x3 grid, q=3/4, J~N(0,1) per edge, colour fields N(0,1).

TROTTER STEPS r (criterion: worst start state row-TVD(Q_trot, Q_exact) <= 0.05, worst of gamma {0.25,0.425,0.6},
worst of 3 seeds). Exact, all rows, for dim <= 1024 (SK n=4-10, CG 4-10, COUL 6-10, EA 4-10, HH 6-10, Potts 2x2);
sampled rows (128 / 64 / 16 / 4) for 12-qubit Ising, Potts 2x3 q4, 3x3 q3, 3x3 q4.
  max r at t = 2 / 6 / 12 / 20:   SK n=10: 5/17/43/86   CG k=10: 4/14/32/66   COUL n=10: 5/21/65/133
  EA 3x4: 5/19/47/94   HH 12: 4/16/40/84   POTTS3 3x3: 5/18/44/90   POTTS4 3x3: 4/13/31/67(partial)
  Fit r = c t^a n^b: a = 1.2-1.4 (all families), b = -0.07..0.38 (weak in n because alpha normalises the energy scale;
  COUL strongest 0.38). Larger n use the fit + max residual (labelled "extrapolated" in costs.csv). Plot r_vs_t.png.
  r ~ t^1.3 means long-t proposals (P1 draws t up to 20) are ~5x more expensive than t=6.

COMPILATION METHOD
  Transpile r=2,3,5 versions (1,2,4 ZZ layers), optimization_level=3, seeds 0-3 (n<=16) or 0-2, best N_2q kept.
  Cost at r: N(r) = N(3) + (r-3)(N(5)-N(3))/2 (linear in layers; NOT validated against full-r transpiles: validate.py
  not run). Topologies: heavy-hex (FakeMarrakesh map; identical coupling maps for FakeFez/Kingston/Boston, checked),
  square (FakeNighthawk 120q), all-to-all CZ reference (no map, same basis), all-to-all native RZZ (Helios-like,
  analytic: one native 2q gate per RZZ, two per XX+YY; 2q depth = edge colouring, K_n: n-1 or n rounds).
  Dense families: best of SABRE and an explicit odd-even transposition swap network on a line path (RZZ+SWAP fused
  to 3 CZ; note: qc.swap must not be used, level-3 ElidePermutations deletes it). Swap network wins for dense on
  heavy-hex for all n >= 8 (84 CZ/layer at n=8 = 3 per pair; 1001 CZ/layer at n=27); SWAP overhead vs all-to-all
  CZ ~1.43-1.5x for dense. Nighthawk used the same line network (a 2D swap network could do better: not tried).
  Heavy-hex has no RZZ fractional gate in the fake basis: each RZZ = 2 CZ. Real Heron fractional RZZ gates could cut
  the ZZ part up to ~2x (reasoned, not compiled).

DEVICE MODELS (pessimistic F = prod(1-e2)^N2q (1-e1)^N1q (1-ro)^n [ (1-mem)^(n*depth2q) for Helios ]; idle decoherence
on superconducting NOT included)
  Heron r2: e2 2e-3, ro 1.67e-2 (A4). Heron r3: e2 2.15e-3 = A4 EPLG(100q) ibm_boston (pessimistic; FakeBoston median
  1.27e-3 / ro 5.1e-3 reported as HeronR3_fakecal in costs.csv), ro not found -> r2 value. Nighthawk: e2 2e-3
  ("Heron-class", A4), ro not found -> r2 value. Helios: e2 8e-4, 1q 3e-5, SPAM 5e-4, memory 6e-4/qubit/layer (A4).
  Timing: IBM t_shot = estimate_duration(transpiled, fake target) + 250 us rep delay; Nighthawk + 1 us, floor 1e-5 s;
  Helios t_shot = 2q depth x 55 ms per depth-1 layer (A4 figure measured at ~98 q, assumed for all n: estimate).
  t_Q sequential: IBM/Nighthawk optimistic 2 s + t_shot, realistic 3 s + t_shot (A4/BRIEF). Helios: whole chain in one
  program, t_Q = t_shot (circuit-time floor; no published loop overhead).
  t_Q batched per chain-step: IBM max(t_shot, 0.35 ms) + 2 s/1e4 executions; Nighthawk max(t_shot,1e-5)+2 s/1e5;
  Helios t_shot / floor(98/n) chains packed in one circuit.

RESULTS (best variant; N_2q / 2q-depth / F; full table results/costs.csv)
 t=6:
  SK n=10 (r=17):  HeronR2 2160/480/3e-3 | Nighthawk 2160/480/5e-3 | Helios 720/144/0.23
  SK n=27 (r=26):  heavy-hex 25,077/1929/5e-29 | Helios 8775/675/1.5e-8
  CG k=8 (r=12):   heavy-hex 924/264/0.08 | Helios 308/77/0.53;  k=12: 3168/576/2.5e-4 | Helios 1056/176/0.12
  COUL n=16 (r=34): heavy-hex 11,880/1584/5e-14 | Helios 3960/495/3.5e-4
  EA 4x4 (r=23):   heavy-hex 2325/681/2.3e-3 (SWAP x2.2) | Nighthawk 1056/192/0.064 (no SWAP) | Helios 528/88/0.28
  EA 6x6 (r=26):   heavy-hex 8098/1272/1e-9 | Nighthawk 3000/232/4.4e-4 | Helios 1500/125/0.02
  HH 12 (r=16):    heavy-hex 360/70/0.31 | Nighthawk 360/70/0.34 | Helios 180/45/0.62
  HH 100 (r=20):   heavy-hex 4180/170/2.6e-6 | Nighthawk 5510/329/3.4e-7 | Helios 2090/76/1.9e-3
  POTTS3 3x3 27q (r=18): heavy-hex 8682/2090/2e-10 (x3.1) | Nighthawk 5552/1167/1.4e-6 | Helios 2232/248/2.9e-3
  POTTS4 3x3 36q (r=13): heavy-hex 8628/2077/2e-10 | Nighthawk 5691/912/9e-7 | Helios 1980/126/1.3e-2
 t=20: every family x device F < 0.1 except tiny sizes (SK n=10 heavy-hex F ~1e-13; Helios 4.5e-4; HH12 Helios 0.07).
 N_2q ~ n^b at t=6: SK 2.5, CG 2.6-2.7, COUL 2.9-3.0 (r grows with n), EA 1.4-1.6, HH 1.2-1.3 (results/fits.csv).

LARGEST n WITH F >= 0.5 / F >= 0.1 at t=6 (fit-interpolated, results/thresholds.csv; measured grid in brackets where
it reaches the threshold)
  SK:    Heron r2/r3, Nighthawk ~5 / ~7 (6)     Helios ~7 / ~11 (10)
  CG:    Heron/Nighthawk ~4-5 / 7               Helios ~8 / 12
  COUL:  Heron ~6 / ~7, Nighthawk none / 6      Helios ~7 / 10
  EA:    Heron ~6 / ~9, Nighthawk ~7 / ~14 (9)  Helios ~10 / 25
  HH:    Heron ~8 / ~21 (12), Nighthawk ~5 / ~24 (12)   Helios ~14 / ~38 (27)
  POTTS 3x3: no device reaches 0.1 (best Helios q=4 0.013).
 At t=20: F>=0.1 only up to n ~4-6 on any device (Helios HH ~10, CG 6).

T_Q (per proposal step)
  Sequential, IBM Heron r2/r3 and Nighthawk: 2 s optimistic / 3 s realistic; t_shot itself only 0.06-1.4 ms, so the
  circuit is irrelevant to latency. Helios (in-program loop, circuit-time floor): SK n=10 t=6 ~8 s, t=20 ~42 s;
  SK n=27 t=6 ~37 s - i.e. the BRIEF's 0.1-0.5 s Helios estimate is optimistic by 1-2 orders for dense Trotter
  circuits at the TVD-0.05 r (own calculation from 55 ms/layer).
  Batched per chain-step: Heron ~0.55-1.6 ms, Nighthawk ~0.08-1.1 ms, Helios ~0.9-60 s (packing floor(98/n) chains).

NATIVE-SUBSET U (SK, U uses only couplings on a heavy-hex tree embedding chosen to keep max sum J^2; accept uses exact E;
exact ideal gaps; 5 instances; m=16 draws; decohered control included) - shown by own simulation (ideal)
  kept couplings 7/28 (n=8, 70% of J^2), 9/45 (n=10, 56% of J^2).
  gap(native)/gap(full) median [IQR]:  beta 0.1: 1.06 / 1.01;  beta 0.3: 0.89 [0.85,0.94] / 0.64 [0.60,0.88];
                                         beta 1.0: 0.46 [0.38,0.72] / 0.35 [0.24,0.40]   (n=8 / n=10)
  native vs best(local,uniform) at beta 1.0: 3.3x (n=8), 2.6x (n=10) vs full 6.2x / 13.9x; native-decohered control 1.0x,
  so the residual native gain is coherent. Ratio native/full falls with n (low T), as expected when kept J^2 falls.
  N_2q per ZZ layer on heavy-hex: dense best 84 -> ~14 CZ (n=8, x6), 135 -> 18 (n=10, x7.5), 198 -> 24 (n=12, x8),
  570 -> 38 (n=20, x15), 1001 -> 52 (n=27, x19). Trotter r for the subset not separately measured (HH family r is
  similar to SK: 16 vs 17 at t=6), so the N_2q ratio carries over to the full circuit approximately.
  Net: x6-19 fewer CZ for a 2-3x (n=8-10) loss in low-T gap; at fixed F that buys roughly 2.5x more spins on heavy-hex
  (HH F>=0.1 to n~21 vs SK n~7). Whether the native gain stays above PT/cluster moves is NOT tested here.

CUTS / NOT RUN / REASONED ONLY
  - validate.py (full-r transpile check of linear per-layer model) not run; per-layer increments from r=3->5 used.
  - Potts 3x3 q=4 Trotter run killed: gamma=0.6 at t=12,20 missing; r taken as max(available 3x3, full 2x3 q=4).
  - Trotter r for n>10 Ising (12-qubit sampled rows aside) is extrapolated by a power-law fit plus max residual.
  - No noisy simulation; F is a multiplicative gate+readout proxy (idle errors on superconducting omitted -> F optimistic
    there; Helios memory error included). Fractional-RZZ Heron and 2D swap networks on Nighthawk not compiled.
  - Only one transpile instance per structure (seed 0 instance); angle values do not change counts at level 3 except
    for special angles.

CONCLUSION
  Shown by own simulation/transpilation: at the TVD-0.05 Trotter depth, a dense QeMCMC proposal is far beyond NISQ
  fidelity on every device except at toy size: F>=0.1 only up to SK n~7 (IBM) / n~11 (Helios) at t=6, and n~4-5 at
  t=20. Dense N_2q grows ~n^2.5 (n^2 pairs x weakly growing r); routing adds only ~1.5x with a swap network, so the
  bottleneck is the dense interaction count and Trotter depth, not topology. Hardware-native sparse instances (HH, EA on
  Nighthawk) reach n~20-25 at F>=0.1 for t=6. Sequential t_Q is latency-bound (2-3 s IBM) and the circuit time is
  irrelevant there; on Helios the circuit time itself (8-40 s for SK n=10) dominates. The pessimistic S* multiplier 1/F
  is 10-300 at P1 sizes (n=8-10, t=6) and astronomically large at n>=16.
  Speculation: shorter-t or adiabatic-ramp proposals (Hsieh et al.) and native-subset U are the only routes to F~0.1
  at n>=20 on current devices.
