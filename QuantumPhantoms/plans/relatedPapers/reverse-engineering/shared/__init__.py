"""Shared, FROZEN foundation of the Quantum Phantoms reverse-engineering epic (feature W).

Run everything with the reverse-engineering/ folder as the working directory:
    python -m shared.validate --stubs
"""
from pathlib import Path

RE_ROOT = Path(__file__).resolve().parent.parent
SHARED = RE_ROOT / "shared"
CONTRACTS = SHARED / "contracts"
STUBS = SHARED / "stubs"
CONTRACT_VERSION = "1.0.0"
LETTERS = {
    "A": "A_placement",
    "B": "B_mapping",
    "C": "C_certificate",
    "D": "D_quantum_growth",
    "E": "E_classical_growth",
    "F": "F_render",
    "G": "G_provenance",
    "H": "H_analysis",
}
