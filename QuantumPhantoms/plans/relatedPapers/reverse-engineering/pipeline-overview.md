<!-- Not rendered (INT). Its weak-edges marker colours the index readiness diagram. Ratings live in each letter README's
     readiness marker; the weak-edges marker below colours the diagram edges. -->

## Where the chain is weakest

<!-- weak-edges: B>G, B>D, C>A -->

1. **Quantum jobs → receipt (B, C, D → G): blocking.** `G receipt fill --job` is a single-value flag. The chain passes
   five job records, argparse keeps the last, and only D's QCA job is signed. Evidence: probe `G.fill`, the only
   `block`. Fix: `action="append"` and bind every job id and counts hash in `fill`.
2. **Draw → quantum growth (B → D): wired, not integrated.** D records B's draw but grows every tumour from the same
   fixed founder, and B's circuits still have no BP simulability number because `D bp` has no `--circuit`. Evidence:
   `D_quantum_growth/src/lineage.py:26, 135`; probe `D.bp_b`. Fix: founder preset from draw `type × margin` (plan AC-8);
   `bp --circuit` (AC-9).
3. **Certified seed (C → everything): provenance is weaker than it looks.** No chain got a beacon pulse later than
   its commit, and the fallback pulse reproduced the identical certificate and seed (`7dfb4d50…`) in two chains with
   different commits, because the simulation is seeded from the public pulse. Evidence: prefix runs 3 and 4,
   `chain.json.beacon_fetch`. Fix: fetch only the newest pulse with backoff, select "first pulse after the commit", and
   refuse a pulse already used.

Next in line: the commit freezes only A–F `.py` code (parameter JSONs, G and H are outside it); A's first run on a
host costs ~25–75 min; B-2 at K = 8 has never run in Heron mode; two chain steps write into git-tracked folders
(`C fetch_pulses`, `F render --export`).
