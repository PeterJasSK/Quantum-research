"""Quantum Phantoms: the one command. Run from code/.

    python main.py                              # dry run: small sizes on the local fake backend (tests the pipeline)
    python main.py --backend ibm_aachen         # live: real hardware (auto = least busy). Peter only.
    python main.py --shots 2000                 # shots per circuit (default 4000 live, 400 dry)
    python main.py --run <run directory>        # continue a stopped run: finished sections are skipped,
                                                # submitted jobs are fetched, not paid twice

Sections run in this order; each is <section>/main.py with run(ctx) and writes its file into
research_runs/<run>/. What B and D run is the CIRCUIT constant at the top of their main.py.
"""
from __future__ import annotations

import argparse
import time
from importlib import import_module
from pathlib import Path

from common import RESEARCH_RUNS
from common.runio import Ctx, load_json

SECTIONS = [                                    # (section, the file that marks it done)
    ("C_certificate", "certificate.json"),      # Bell map: certificate, bit pool, pair map; too weak stops the run
    ("B_mapping", "cohort_params.json"),        # rulebook + pool bits -> tumour parameters; B's hypothesis circuit
    ("D_quantum_growth", "dscale/dscale_run.json"),   # quantum growth: seed shapes / hypothesis circuit
    ("A_placement", "sites.json"),              # a 3-D site per tumour in the host lung
    ("E_classical_growth", "growth.json"),      # classical growth from the seed
    ("F_render", "tiles.json"),                 # render into the host CT
    ("G_provenance", "lineage_record.json"),    # lineage record + ledger
    ("H_analysis", "analysis.json"),            # what the run shows
    ("webpage", None),                          # web/<run>.html (always rebuilt)
]


def main() -> None:
    ap = argparse.ArgumentParser(description="Quantum Phantoms pipeline")
    ap.add_argument("--backend", help="IBM backend name or 'auto' = live run; not set = dry run on the local fake backend")
    ap.add_argument("--shots", type=int, help="shots per circuit (default 4000 live, 400 dry)")
    ap.add_argument("--run", help="continue this run directory instead of starting a new one")
    a = ap.parse_args()
    run_dir = Path(a.run).resolve() if a.run else RESEARCH_RUNS / f"run_{'live' if a.backend else 'dry'}_{time.strftime('%Y%m%d-%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    saved = load_json(run_dir / "backend.json")
    if saved and saved["live"] and not a.backend:               # continuing a live run: stay on its backend
        a.backend = saved["name"]
    a.shots = a.shots or (4000 if a.backend else 400)
    ctx = Ctx(run_dir=run_dir, backend=a.backend, shots=a.shots)
    print(f"run {run_dir}  |  {'LIVE on ' + a.backend + ' (real hardware, Peter only)' if a.backend else 'dry run (local fake backend)'}"
          f"  |  {a.shots} shots")
    for name, done in SECTIONS:
        if done and (run_dir / done).is_file():
            print(f"\n[{name}] done earlier ({done}), skipped")
            continue
        t0 = time.time()
        print(f"\n{'=' * 100}\n[{name}]\n{'=' * 100}", flush=True)
        import_module(f"{name}.main").run(ctx)
        print(f"[{name}] {time.time() - t0:.0f} s", flush=True)
    print(f"\nrun {run_dir}\nweb {RESEARCH_RUNS.parent / 'web' / (run_dir.name + '.html')}")


if __name__ == "__main__":
    main()
