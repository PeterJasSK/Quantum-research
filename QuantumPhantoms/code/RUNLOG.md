# Run log: B and D circuit evaluation on hardware

One row per live run. A pass is a hardware result; it is a claim only when its bound is proven (not `[verify]`).
Every run is n = 1. Values are raw counts unless stated. QPU-s is the estimate over all jobs of the run.

## Summary

| Run | Date | Backend | CHSH S | B circuit | B result | D circuit | D result | QPU-s |
|---|---|---|---|---|---|---|---|---|
| `01LiveRun` | 2026-11-14 | ibm_fez | 2.731 | ROLL | - | DSCALE (100) | 0 of 3 passed | 28.6 |
| `set01/Run01-R2-Q2-R1-STAR-001` | 2026-11-14 | ibm_fez | 2.705 | R2-Q2 | **pass** 0.854 vs 0.75 | R1-STAR-001 | **pass** 0.386 / 0.394 vs 0.296 | 6.1 |
| `set01/Run01-R5-H12-DSCALE` | 2026-11-14 | ibm_fez | 2.763 | R5-H12 | not run (no hexagon) | DSCALE (100) | 0 of 3 passed | 28.6 |
| `set01/Run01-R2-D4-R3-LADDER` | 2026-11-14 | ibm_fez | 2.771 | R2-D4 | **pass** 0.737 vs 0.625 | R3-LADDER | **pass** 1.135 vs 2 | 14.2 |
| `set01/Run02-R5-H12-DSCALE` | 2026-11-14 | ibm_fez | 2.714 | R5-H12 | not run (no hexagon) | DSCALE (40) | 0 of 3 passed; GHZ F 0.457 vs 0.5 (near miss) | 28.6 |
| `set01/Run03-R5-H12-DSCALE` | 2026-11-14 | ibm_fez | 2.686 | R5-H12 | not run (no hexagon) | DSCALE (40) | 1 of 3 passed: QCA marginal; GHZ F 0.258 | 28.6 |
| `set01/Run04-R5-H12-R3-TEST` | 2026-11-14 | ibm_fez | 2.715 | R5-H12 | fail 0.742 vs 0.80 (0.684 on the even-weight inputs) | R3-TEST | **pass** at 16, 24, 32, 40 pairs (0.97, 0.98, 0.885, 0.85 vs 0.63 to 0.50) | 17.8 |
| `set01/Run01-R2-Q3-R5-LADDER` | 2026-11-14 | ibm_fez | 2.684 | R2-Q3 | **pass** 0.790 vs 0.75 | R5-LADDER | loss per CZ 0.052 (calibration) | 24.3 |
| `set01/Run02-R2-Q2-R1-STAR-001` | 2026-11-14 | ibm_fez | 2.698 | R2-Q2 | **pass** 0.850 vs 0.75 | R1-STAR-001 | **pass** 0.382 / 0.395 vs 0.296 | 6.1 |
| `set01/Run03-R2-Q2-R1-STAR-001` | 2026-11-14 | ibm_fez | 2.735 | R2-Q2 | **pass** 0.850 vs 0.75 | R1-STAR-001 | **pass** 0.404 / 0.389 vs 0.296 | 6.1 |
| `set01/Run05-R4-HEX-R3-TEST` | 2026-11-14 | ibm_fez | 2.688 | R4-HEX | fail: eps -0.21 ± 0.15 (no signal) | R1-STAR-001 (folder name says R3-TEST) | **pass** 0.392 / 0.394 vs 0.296 | 4.1 |

All eleven runs used the same calibration snapshot of ibm_fez (2026-11-13 17:27), 4000 shots requested.

## Per circuit

| Circuit | Level | Value ± sigma | Bound (rigour) | Ideal | Margin | Job | Status |
|---|---|---|---|---|---|---|---|
| R1-STAR-001, identical steps | L1′-T | 0.3855 ± 0.0077 | 0.29641 (certified grid search, 2-state machine) | 0.4375 | 11.6 sigma | dbs7ekejjaos73ajrvtg | pass; bound 0.29641 is computer-certified, to verify in the PDF |
| R1-STAR-001, first step compiled | L1′-T | 0.3935 ± 0.0077 | 0.29641 (certified grid search) | 0.4375 | 12.6 sigma | dbs7ekejjaos73ajrvtg | pass; bound 0.29641 is computer-certified, to verify in the PDF |
| R2-Q2 | L1′-C | 0.854 ± 0.0039 | 0.75 (textbook `[verify]`) | 0.8536 | 26 sigma | dbs7ecfv5hds73dikpo0 | pass, bound to verify |
| R2-D4 | L1′-C | 0.7367 ± 0.0025 | 0.625 (textbook `[verify]`) | 0.750 | 45 sigma | dbs96khabdes73fqsovg | pass, bound to verify |
| R3-LADDER | L1′-L | overhead 1.135 ± 0.003 | 2 (`[verify]`, gap G3) | 1 | - | dbs96snv5hds73dimhs0 | pass, bound to verify |
| R5-H12 | L1.5 | - | 0.80 (`[verify]`) | - | - | - | not run: no hexagon tile on ibm_fez after pruning |
| DSCALE ghz-spine, N = 35 | L1 | F 0.087 ± 0.019, then 0.129 ± 0.020 | 0.5 | 1 | - | dbs4erfv5hds73dihr0g, dbs901fv5hds73dimb10 | fail twice (0 parity checks fitted) |
| DSCALE ghz-spine, N = 14 (`BUDGET = 40`) | L1 | F 0.457 ± 0.025 raw; 0.580 readout-corrected | 0.5 | 1 | 1.7 sigma below (raw) | dbs9i9pabdes73fqt530 | fail, near miss (0 of 2 parity checks fitted) |
| DSCALE ch-qca, 12 sites (`BUDGET = 40`) | L1 | negativity 0 on all 4 edges; echo 0.348 | Bonferroni 0.05 | 0, 0.126, 0, 0 on the 4 edges | - | same | fail: witness is 0 by design on 3 of 4 edges |
| DSCALE pmd-bank (`BUDGET = 40`) | L1′ | gap / floor -3.09 | > 3 | - | - | same | fail (pass rule not reachable) |
| DSCALE ghz-spine, N = 14, repeat (Run03) | L1 | F 0.258 ± 0.050 raw | 0.5 | 1 | 4.9 sigma below | dbsaemgk09pc73avucu0 | fail; same qubits and tree as Run02, 61 min later |
| DSCALE ch-qca, 12 sites, repeat (Run03) | L1 | negativity 0.0139 ± 0.0059 | Bonferroni 0.05 | as above | 2.4 sigma | same | pass, **not claimable**: 1 of 2 on the same qubits (Run02 gave 0) |
| DSCALE pmd-bank, repeat (Run03) | L1′ | gap / floor -3.14 | > 3 | - | - | same | fail (pass rule not reachable) |
| DSCALE ch-qca, 27 sites | L1 | negativity 0.011, then 0.012 (p_bonf 0.12, 0.11) | Bonferroni 0.05 | - | - | same | fail twice (3 of 4 edges exactly 0) |
| DSCALE pmd-bank | L1′ | gap / floor -2.85, then -1.87 | > 3 | - | - | same | fail twice (pass rule not reachable) |
| R3-TEST, 16 pairs | L1′-L | success 0.970 ± 0.012 | 0.631 (2408.03376 Eq. 4 `[verify]`, M = 20,000) | 1 | 28 sigma | dbsbg8ujjaos73ak08n0 | pass, bound to verify; emulated channel |
| R3-TEST, 24 pairs | L1′-L | 0.980 ± 0.010 | 0.5005 | 1 | 48 sigma | same | pass, bound to verify; strongest row |
| R3-TEST, 32 pairs | L1′-L | 0.885 ± 0.023 | 0.500 | 1 | 17 sigma | same | pass, bound to verify |
| R3-TEST, 40 pairs (80 qubits) | L1′-L | 0.850 ± 0.025 | 0.500 | 1 | 14 sigma | same | pass, bound to verify |
| R3-TEST, 8 pairs | L1′-L | 0.980 ± 0.010 | 1 (no separation at this M) | 1 | - | same | no claim possible |
| R5-H12, all 64 inputs | L1.5 | 0.742 ± 0.002 | 0.80 (`[verify]`) | 1 | 24 sigma below | dbsbft7v5hds73dip3n0 | fail; input set was wrong (see note) |
| R5-H12, 32 even-weight inputs | L1.5 | 0.684 ± 0.004 | 0.80 (`[verify]`) | 1 | 31 sigma below | same | fail; this is the game score |
| R5-LADDER, n = 12 / 20 | calibration | win 0.783 / 0.672; loss per CZ 0.047 / 0.053 | none | - | - | dbsbo2pabdes73fqvkfg, dbsbob9abdes73fqvkog | mixed input set, old F formula: indicative only |
| R2-Q3 | L1′-C | 0.7897 ± 0.0026 | 0.75 (textbook `[verify]`) | 0.789 | 15 sigma | dbsbnqhabdes73fqvk70 | pass, bound to verify |
| R2-Q2, repeats | L1′-C | 0.8503 ± 0.0040, 0.8496 ± 0.0040 | 0.75 (textbook `[verify]`) | 0.8536 | 25 sigma each | dbsbvb8k09pc73b00680, dbsc6rok09pc73b00dm0 | pass 3 of 3 runs |
| R1-STAR-001, identical steps, repeats | L1′-T | 0.3823 ± 0.0077, 0.4043 ± 0.0078, 0.3920 ± 0.0077 | 0.29641 | 0.4375 | 11.2, 13.9, 12.4 sigma | dbsbvr7v5hds73dipkmg, dbsc73ujjaos73ak104g, dbscgkejjaos73ak19i0 | pass 4 of 4 runs |
| R1-STAR-001, first step compiled, repeats | L1′-T | 0.3945 ± 0.0077, 0.3890 ± 0.0077, 0.3938 ± 0.0077 | 0.29641 | 0.4375 | 12.7, 12.0, 12.6 sigma | same | pass 4 of 4 runs |
| R4-HEX, 8 layers, 16 circuits x 1 shot | L1′-C (n = 12) | eps -0.213 ± 0.150 | eps about 0.16 for 12 bits (two-point reading `[verify]`) | eps 0.024 (ansatz fidelity) | - | dbscgc7v5hds73diq4u0 | fail: could not pass at these sizes |

Notes:
- R3-TEST (Run04): 43 pairs available, 401 circuits, 50 shots each, 10,000 calibration shots. Calibration factor
  0.714, 0.452, 0.286, 0.171, 0.106 at 8 to 40 pairs = 0.945 to 0.959 per pair. Success is the same for both
  hidden channels (no bias toward one answer). Limits: the 200 trials of a size share one pool and one calibration,
  so the binomial sigma is a lower limit; one inserted Pauli per circuit (50 shots); the channel is emulated by
  subsampling as in the paper; n = 1 run.
- R5-H12 (Run04): ring [123, 124, 125, 126, 127, 137, 147, 146, 145, 144, 143, 136], holds pruned qubit 146. The
  64 inputs included the 32 odd-weight ones, which keep only the input-independent parity of the six fixed sites
  (win 0.799, any classical player wins it). The 32 even-weight inputs (two parities each) gave 0.684. White-noise
  reading: F = 0.58 to 0.60 from both groups; win 0.80 needs F >= 0.73. Fixed in `common/game.py` after this run:
  even-weight inputs only; ladder F = (4 win - 1) / 3.
- R4-HEX (Run05): same ring as the hexagon game (holds pruned qubit 146), up to 505 CZ per circuit, most of them
  in the routed global Clifford measurement. The 8-layer ansatz reaches fidelity 0.024 to its Haar target, so even
  a noiseless device scores eps about 0.024, far below the 0.16 threshold; 16 single-shot circuits give sigma
  0.15, so the run cannot resolve anything below about 0.45. The plan's size is 86 layers and 10,000 circuits.
  Inputs were pseudo-random and the bound's constants are not transcribed: it could not have been a claim either.
  The "bits" value of -79 is the two-point line extrapolated below its range and has no meaning.
- R1-STAR-001 over four runs: identical steps 0.386, 0.382, 0.404, 0.392 (mean 0.391); first step compiled 0.394,
  0.395, 0.389, 0.394 (mean 0.393). Spread between runs 0.010 and 0.003, at or below the shot sigma 0.0077. Same
  tile [3, 2, 4, 16] each time.
- R1-STAR-001: tile [3, 2, 4, 16], 6 CZ. Assumption: the memory is one qubit (not device-independent).
- R2-Q2: qubit 58, 0 CZ, worst input 0.834. R2-D4: qubits [58, 71], 1 CZ, worst input 0.690. Message dimension assumed.
- R3-LADDER: 8 and 16 pairs, 8 instances each, hidden sign recovered at both sizes (72.6 and 34.0 sigma); 43 pairs
  available on the chip, so R3-CHIP64 (64 pairs) does not fit ibm_fez today.
- DSCALE at `BUDGET = 40` (Run02): 14-qubit spine, depth 4, <X^14> = 0.555, mean ZZ = 0.882, ghz2 = 1.437. No
  parity check fitted (0 of 2), so no post-selection. The claim rule uses the raw F.
- ch-qca, ideal statevector of the 12-site Run02 patch (local, noiseless): pair negativity at t_w = 2 is 0 on three
  of the four registered edges and 0.126 on (67, 68); at t_w = 1 it is 0.233 on one edge. The witness cannot pass
  as registered, whatever the hardware does.
- Run02 vs Run03: identical allocation (spine root 124, same 14 qubits, same QCA and PMD regions), same
  calibration snapshot, unchanged spine code; only the DFE stabilizer sample differs (seeded by the roll). GHZ F
  went 0.457 -> 0.258 and ghz2 1.437 -> 0.980. Cause not determined: raw counts are not stored. So one DSCALE run
  does not fix the value of F to better than about 0.2, and no single run of it can carry a claim.

## What works

- Pipeline B -> web, live, eleven runs without a fault.
- CHSH gate: S = 2.71 to 2.77 on every run.
- Small circuits (0 to 32 CZ): every one passed with wide margins; R1-STAR-001 repeated 4 of 4, R2-Q2 3 of 3.
- R3-TEST: the hypothesis test passes at 16 to 40 pairs (80 qubits) on the first run.
- Closest to a claim: R1-STAR-001 (L1′-T, repeatable) and R3-TEST (L1′-L, one run), once their bounds are checked
  in the PDFs.

## What does not

- No L1 (entangled generative state) yet: DSCALE at 100 qubits fails the same way twice; at 40 qubits the GHZ
  spine gives 0.457 then 0.258 on the same qubits. The one QCA pass (Run03, 2.4 sigma) did not repeat Run02.
- DSCALE is not repeatable run to run on a calibration snapshot more than a day old.
- R5 cluster game on ibm_fez: placed with the ring fallback, but 0.684 on the game inputs against 0.80. The ring
  state is at F about 0.58 (needs 0.73); readout of 12 qubits in one parity is the likely main loss (not separated
  from gate loss by the meter).
- R4-HEX at first-run sizes (8 layers, 16 circuits) carries no information; on ibm_fez the full size is forecast
  below threshold as well.
- The roll is 642 CZ: tumour parameters on hardware are noise-dominated, not the rulebook distribution.
- Tumour growth + render take 11 to 14 minutes per run and do not depend on the circuit under test.

## Next

Scope from 2026-11-14: the tile-scale separations (R1, R2, R3) plus the ring ladder (R5, then R6a) as the measured
distance to L2. DSCALE (GHZ spine, CH-QCA, PMD), R6b-LEAN64 as an L2 candidate and R4 on fez are dropped.

0. QSCALE (2026-11-15, dry runs only so far): C now runs first as a Bell map and the run spends its bits. First
   live run: B `R2-MAP`, D `R5-LADDER` on the best backend open; compare the pair map with the ring the layout
   picked, and check the pool size against the spend (12 tumours = 768 bits). Then D `R6a-S36` with `--run` on the
   same directory to read the forecast line and "L2 distance".
   QCAND (2026-11-15, dry runs only): 11 candidates built, one live run each, in this order. B and D can share a
   run; C `GRAPH-BELL` is its own switch. Two live runs below the bound on the best backend = dropped (row kept,
   commented).
   - D `D-GRAPH` with B `B-GHZ`; then C `GRAPH-BELL` in the next run.
   - D `D-DU`, then `R6a-S36` with `--run` on the same directory: the forecast then uses the deep-circuit loss.
   - B `B-MSQ`, D `D-STC`.
   - B `B-IQP` (108 qubits need one connected pruned region; refused otherwise), D `D-DTC`.
   - B `B-KS` last: set `MID_CIRCUIT_LIVE = True` in `B_mapping/games.py` once mid-circuit readout is enabled.
   Paper checks before any claim: 2512.02284 (GHZ game bound), 2101.10307 Eq. 3 (graph Bell form), 2504.15725
   (check construction), 2411.00765 (dual-unitary observable), 2501.18036 (couplings), 2506.06869, 2503.18949.
1. `R3-TEST` once more (repeatability), with any B circuit. It now takes certified pairs of the Bell map, 2,000
   pool circuits at 10 shots.
2. `R1-TILE24` (D) with `R2-D4` (B): the clock on 24 tiles, both arms.
3. `R5-H12` (B) again with the corrected input set, on a backend with lower readout error than ibm_fez if one is
   open; `R5-LADDER` (D) in the same run for a clean loss number.
4. `R6a-S36`: not on ibm_fez. At 0.045 loss per CZ a depth-22 ring has no signal.
5. Paper checks before any claim: 2005.04241 Table 3 (R1 bound 0.29641, computer-certified, not a hand proof);
   2408.03376 Eq. 4 and Chen et al. PRL 132, 180805 (R3-TEST bound, adaptive learners, what counts in M);
   2110.04277 Remark 2 and the input set of the game (R5); the R2 textbook bounds.

Paper reading of 2026-11-14 (partial reads, see the claim notes): R1's 8/27 is the attained classical value; the
upper bound is 0.29641 by certified grid search. The identical-steps arm is the one that matches the paper's
time-independent machine. The 70-qubit open-chain doped-Clifford circuit was simulated classically (2608.13110);
a depth-36 ring sits near that cost, so only the published depth 73 on a ring stands as L2.
