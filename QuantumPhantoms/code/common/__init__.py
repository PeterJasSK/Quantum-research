"""Common code of the Quantum Phantoms pipeline: everything more than one section needs.

    runio.py        run context, the files the sections exchange, seeds, hashes, claims
    quantum.py      one backend per run (real, or a local fake for the dry run), spend guard, jobs, execute
    targets.py, allocate.py, lint.py, pauli_noise.py, witness.py     chip calibration, layouts, lints, noise, statistics
    qhard.py, game.py                                                rings / tiles / GF(2) and the cluster-state game
    host.py, lidc_fetch.py, datamodel.py                             host CT, cohort data model
"""
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = CODE_ROOT.parent                           # QuantumPhantoms/
RESEARCH_RUNS = PROJECT_ROOT / "research_runs"            # every run lives here
WEB_DIR = PROJECT_ROOT / "web"

HOST = "LIDC-IDRI-0481"                                   # public Siemens-scanner CT the tumours are rendered into
FAKE_BACKEND = "FakeMarrakesh"                            # dry run: the same circuits on this local fake (not hardware)
MAX_QPU_SECONDS = 45.0                                    # estimated QPU-s cap over all jobs of one live run
MIN_SHOTS = 300                                           # a job cut below this is refused
