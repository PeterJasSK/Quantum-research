"""D orchestrator: certified seed -> quantum lineage -> memory-advantage q-machine -> Goldilocks QCA -> 3-D seed shape
-> belief-propagation adversary, in one run directory.

    python -m D_quantum_growth.src.grow --mode ideal|heron [--dd] [--chsh-settings quantum|classical]
                                        [--tumor-draw P] [--certificate P] [--compiled-circuit P]

A failed certificate rejects the draw (exit 2, no outputs). A lineage CHSH S <= 2 rejects the run (exit 3, logged,
no seed shape). Simulation only; every quantum number carries its sim label.
"""
from __future__ import annotations

import argparse
import json

from D_quantum_growth.src import bp, io_contracts as io, lineage, memory_advantage, qca, seed_shape
from shared.simbackend import sim_label

TOOL = "D_quantum_growth.src.grow"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=("ideal", "heron"), required=True)
    ap.add_argument("--dd", action="store_true")
    ap.add_argument("--chsh-settings", choices=("quantum", "classical"), default="quantum")
    ap.add_argument("--skip-bp", action="store_true", help="debug: skip the BP adversary stage")
    io.add_input_args(ap)
    a = ap.parse_args()
    mode = a.mode
    run_, paths, docs, seed = io.begin(mode, f"grow-{mode}" + ("-dd" if a.dd else ""), TOOL, io.overrides_of(a))
    if seed is None:
        return 2
    notes = [sim_label(mode)]

    lin = lineage.run(run_, seed, mode, a.dd, a.chsh_settings == "classical")
    notes.append(f"lineage S_chsh={lin['chsh']['S']:.3f}+-{lin['chsh']['stderr']:.3f} "
                 f"({lineage.LABEL_CHSH}); witness passed={lin['passed']}")
    if not lin["chsh_ok"]:
        notes.append("RUN REJECTED: lineage CHSH S <= 2 (epic decision 6); no seed shape written")
        with open(io.LETTER_DIR / "runs" / "rejections.jsonl", "a") as f:
            f.write(json.dumps({"run_id": run_.path.name, "stage": "grow", "mode": mode,
                                "S": lin["chsh"]["S"]}) + "\n")
        run_.finish("; ".join(notes))
        print("; ".join(notes))
        return 3

    mem = memory_advantage.run(run_, seed, mode)
    d = mem["detail"]
    notes.append(f"memory advantage passed={mem['passed']} (d_KL q={d['d_kl_quantum_bits_per_symbol']:.5f} vs 1-bit "
                 f"{d['d_kl_classical_1bit_sampled']:.5f}; C_q meas={d['C_q_measured']:.4f} < C_mu={d['C_mu']:.4f})")

    q = qca.run(run_, seed, mode)
    notes.append(f"QCA ({q['detail']['patch_kind']} patch) SWAPs={q['swaps']} witness passed={q['passed']}")

    up = [{"contract": "quantum_lineage", **lin["lineage_ref"]}]
    ss = seed_shape.write(run_, run_.path, q["patch"], q["snapshot"], lin["lineage_file"], q["passed"], mode, up)
    notes.append(f"seed shape n_cells={int(ss['occupancy'].sum())} claim={'L1' if q['passed'] else 'L0'}")

    if not a.skip_bp:
        res = bp.run_adversary(run_.path)
        bp.write_report(run_, res["rows"], mode)
        notes.append("smallest chi with fidelity>=0.99: " + json.dumps(bp.smallest_chi(res["rows"])))
    run_.finish("; ".join(notes))
    print(run_.path)
    for n in notes:
        print(" ", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
