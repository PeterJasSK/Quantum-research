#!/usr/bin/env python3
"""Critical Quantum Life — F1: the DRAFT kill-gate (sim, toy scale).

The go/no-go BEFORE any hardware spend — the same discipline as the virus
`stage5_fliptest.py` P0 kill-gate. On Aer at toy scale (W=4, ~15 generations) it drives F0's
closed + yoked arms and checks that all THREE honesty-gate signals *exist* (coarse, not the
F2/F3 rigor):

  1. adaptation  (AC-F1.1): surprise falls under the closed loop but NOT under the yoked control.
  2. criticality (AC-F1.2): the branching sigma trends toward 1 (edge of chaos), not toward 0 (dead).
  3. poke-recover(AC-F1.3): a single scripted poke (gen 8) spikes surprise, which then relaxes.

The three boolean signals AND-reduce to an explicit GO / NO-GO verdict (AC-F1.4). An honest
NO-GO shipping with the toy-scale evidence blocks IS an acceptable deliverable (epic §7) — the
honest fix for an absent signal is F0's knobs, not loosening F1's threshold.

F1 writes NO new physics — it imports F0 (`closed_loop`) and reads the `generations[]`
observables F0 logs. `verify_run(path)` reloads a gate JSON + its referenced closed/yoked runs,
re-derives every signal + the verdict, and asserts they match the stored values (reproducibility).

Run (sim):
    cd THESIS/CriticalQuantumLife/code
    python draft_gate.py --generations 15 --seed 100 --name cql_f1
    python draft_gate.py --verify ../research_runs/cql_f1_gate_sim_seed100_sim_run.json
"""
from __future__ import annotations

import argparse
import functools
import json
import os
import statistics
import sys
from typing import Any

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import closed_loop as cl  # F0: run_closed_loop / run_yoked / write_run / OUTPUT_DIR / make_client

# ---- gate thresholds (plan §7; resolved §11 Q1-Q3) --------------------------
ADAPT_MIN = 0.15         # Q1: min closed-minus-yoked surprise drop (nats) to pass adaptation
SIGMA_DEAD = 0.30        # Q2: late-window sigma must exceed this (else collapsing to 0 = dead)
RELAX_WIN = 4            # Q3: generations after the poke within which surprise must relax
RELAX_FRAC = 0.50        # Q3: surprise must return within this fraction of the spike toward baseline
EARLY_WIN = 3            # generations averaged for the "early" window
LATE_WIN = 3             # generations averaged for the "late" window
POKE_GEN_DEFAULT = 8     # epic resolved Q2 — inside the 15-gen window so spike + relax both fit


# ---------------------------------------------------------------------------
# Signal computations (coarse by design — this is a gate, not F2/F3 rigor)
# ---------------------------------------------------------------------------
def surprise_drop(gens: list[dict[str, Any]]) -> float:
    """Mean surprise over the first EARLY_WIN gens minus mean over the last LATE_WIN gens.

    Positive = surprise fell (the loop learned to predict its own outcomes)."""
    s = [g["surprise"] for g in gens]
    if len(s) < EARLY_WIN + LATE_WIN:
        return s[0] - s[-1]
    return statistics.fmean(s[:EARLY_WIN]) - statistics.fmean(s[-LATE_WIN:])


def signal_adaptation(closed: dict[str, Any], yoked: dict[str, Any],
                      adapt_min: float = ADAPT_MIN) -> dict[str, Any]:
    """AC-F1.1 — closed surprise falls where the yoked control's does not."""
    closed_drop = surprise_drop(closed["generations"])
    yoked_drop = surprise_drop(yoked["generations"])
    gap = closed_drop - yoked_drop
    return {
        "closed_surprise_drop": closed_drop,
        "yoked_surprise_drop": yoked_drop,
        "gap": gap,
        "pass": gap > adapt_min,
    }


def signal_criticality(closed: dict[str, Any]) -> dict[str, Any]:
    """AC-F1.2 — branching sigma trends toward 1, and is not collapsing toward 0 (dead)."""
    sigmas = [g["sigma"] for g in closed["generations"] if g.get("sigma") is not None]
    if len(sigmas) < 2:
        # not enough non-None sigma samples to judge a trend
        return {"sigma_early_window_mean": None, "sigma_final_window_mean": None,
                "trends_to_one": False, "pass": False}
    early = statistics.fmean(sigmas[:EARLY_WIN])
    late = statistics.fmean(sigmas[-LATE_WIN:])
    trends_to_one = (abs(late - 1.0) < abs(early - 1.0)) and (late > SIGMA_DEAD)
    return {
        "sigma_early_window_mean": early,
        "sigma_final_window_mean": late,
        "trends_to_one": trends_to_one,
        "pass": trends_to_one,
    }


def signal_poke_recover(closed: dict[str, Any], poke_gen: int) -> dict[str, Any]:
    """AC-F1.3 — surprise spikes at the poke, then relaxes within RELAX_WIN gens."""
    surprises = [g["surprise"] for g in closed["generations"]]
    n = len(surprises)
    if poke_gen < EARLY_WIN or poke_gen >= n:
        return {"poke_gen": poke_gen, "baseline": None, "spike": 0.0,
                "relaxed": False, "pass": False}
    baseline = statistics.fmean(surprises[poke_gen - 3:poke_gen])
    spike = surprises[poke_gen] - baseline
    relaxed = False
    for g in range(poke_gen + 1, min(poke_gen + RELAX_WIN + 1, n)):
        if (surprises[g] - baseline) <= RELAX_FRAC * spike:
            relaxed = True
            break
    return {
        "poke_gen": poke_gen,
        "baseline": baseline,
        "spike": spike,
        "relaxed": relaxed,
        "pass": (spike > 0.0) and relaxed,
    }


def verdict_from(signals: dict[str, Any]) -> str:
    """AND-reduce the three signal passes to GO / NO-GO (mirror stage5_fliptest verdict)."""
    all_pass = (signals["adaptation"]["pass"] and signals["criticality"]["pass"]
                and signals["poke_recover"]["pass"])
    return "GO" if all_pass else "NO-GO"


def _failing(signals: dict[str, Any]) -> list[str]:
    return [name for name in ("adaptation", "criticality", "poke_recover")
            if not signals[name]["pass"]]


def _verdict_note(signals: dict[str, Any], verdict: str) -> str:
    if verdict == "GO":
        return "GO -> proceed to F5 hardware thesis; all three honesty-gate signals present."
    failing = ", ".join(_failing(signals))
    return (f"NO-GO -> documented no-go, evidence blocks retained. Absent signal(s): {failing}. "
            f"Honest fix is F0's knobs (Q2/Q3), not loosening F1's threshold.")


def _build_signals(closed: dict[str, Any], yoked: dict[str, Any], poke_gen: int,
                   adapt_min: float) -> dict[str, Any]:
    return {
        "adaptation": signal_adaptation(closed, yoked, adapt_min),
        "criticality": signal_criticality(closed),
        "poke_recover": signal_poke_recover(closed, poke_gen),
    }


# ---------------------------------------------------------------------------
# Gate driver
# ---------------------------------------------------------------------------
def run_gate(args: argparse.Namespace) -> tuple[dict[str, Any], str, str]:
    """Drive F0's closed + yoked arms at W=4, compute the three signals, AND-reduce to a
    verdict. Returns (gate_dict, closed_run_path, yoked_run_path)."""
    # F0-required knobs the gate fixes (W=4, both arms, sim, scripted poke) + F0 defaults.
    args.width = 4
    args.arm = "both"
    args.poke_gen = args.poke_gen if args.poke_gen is not None else POKE_GEN_DEFAULT
    for name, val in (("shots", 4096), ("death", "unitary"), ("interaction", "nn"),
                      ("nbins", 10), ("mut_scale", cl.DEFAULT_MUT), ("sim", True),
                      ("delta", cl.q4.AGING_DELTA), ("gamma", cl.q4.DAMP_GAMMA),
                      ("qrng_url", cl.QEAAS_URL_DEFAULT)):
        if not hasattr(args, name):
            setattr(args, name, val)

    # guard (§9): the poke needs >= RELAX_WIN generations after it inside the run
    if args.poke_gen + RELAX_WIN >= args.generations:
        print(f"[ABORT] poke_gen={args.poke_gen} + RELAX_WIN={RELAX_WIN} needs "
              f"< generations={args.generations} for the relaxation window")
        raise SystemExit(1)

    client = cl.make_client(args)              # None on sim (PRNG fallback)
    print(f"=== CQL F1 kill-gate: width={args.width} generations={args.generations} "
          f"poke_gen={args.poke_gen} adapt_min={args.adapt_min} sim={args.sim} ===")

    closed, stimulation = cl.run_closed_loop(args, client)
    yoked = cl.run_yoked(args, stimulation, client)   # SHARED stimulation from the closed arm
    cl._print_table(closed)
    cl._print_table(yoked)
    closed_path = cl.write_run(closed, args)
    yoked_path = cl.write_run(yoked, args)

    signals = _build_signals(closed, yoked, args.poke_gen, args.adapt_min)
    verdict = verdict_from(signals)
    note = _verdict_note(signals, verdict)

    meta = dict(closed["meta"])
    meta["arm"] = "gate"
    gate = {
        "meta": meta,
        "thresholds": {"adapt_min": args.adapt_min, "sigma_dead": SIGMA_DEAD,
                       "relax_win": RELAX_WIN, "relax_frac": RELAX_FRAC,
                       "early_win": EARLY_WIN, "late_win": LATE_WIN},
        "runs": {"closed": os.path.basename(closed_path),
                 "yoked": os.path.basename(yoked_path)},
        "signals": signals,
        "kill_gate": {"verdict": verdict, "note": note},
    }
    _print_verdict(gate)
    return gate, closed_path, yoked_path


def _print_verdict(gate: dict[str, Any]) -> None:
    s = gate["signals"]
    a, c, p = s["adaptation"], s["criticality"], s["poke_recover"]
    print("\n  --- F1 signal summary -------------------------------------------")
    print(f"  adaptation : closed_drop={a['closed_surprise_drop']:+.3f}  "
          f"yoked_drop={a['yoked_surprise_drop']:+.3f}  gap={a['gap']:+.3f}  pass={a['pass']}")
    early = c["sigma_early_window_mean"]
    late = c["sigma_final_window_mean"]
    print(f"  criticality: sigma_early={_fmt(early)}  sigma_late={_fmt(late)}  "
          f"trends_to_one={c['trends_to_one']}  pass={c['pass']}")
    print(f"  poke@{p['poke_gen']:>2} : spike={p['spike']:+.3f}  relaxed={p['relaxed']}  "
          f"pass={p['pass']}")
    verdict = gate["kill_gate"]["verdict"]
    banner = "GO to hardware thesis" if verdict == "GO" else "honest NO-GO (evidence retained)"
    print(f"\n  KILL-GATE VERDICT: {verdict}  ({banner})")
    print(f"  {gate['kill_gate']['note']}")


def _fmt(x: float | None) -> str:
    return " none" if x is None else f"{x:5.3f}"


# ---------------------------------------------------------------------------
# Reproducibility gate
# ---------------------------------------------------------------------------
def verify_run(path: str) -> int:
    """Reload a gate JSON + its referenced closed/yoked runs, re-derive every signal + the
    verdict, assert they match the stored values. Nonzero exit on mismatch (mirror
    stage5_fliptest.verify_run)."""
    with open(path) as f:
        gate = json.load(f)
    runs = gate["runs"]
    closed = _load_run(runs["closed"])
    yoked = _load_run(runs["yoked"])
    poke_gen = gate["signals"]["poke_recover"]["poke_gen"]
    adapt_min = gate.get("thresholds", {}).get("adapt_min", ADAPT_MIN)

    recomputed = _build_signals(closed, yoked, poke_gen, adapt_min)
    verdict = verdict_from(recomputed)

    ok = True
    for name in ("adaptation", "criticality", "poke_recover"):
        want = gate["signals"][name]["pass"]
        got = recomputed[name]["pass"]
        mark = "ok" if want == got else "MISMATCH"
        if want != got:
            ok = False
        print(f"  {name:12} stored_pass={want!s:5} recomputed={got!s:5}  [{mark}]")
    if verdict != gate["kill_gate"]["verdict"]:
        ok = False
    print(f"  verdict      stored={gate['kill_gate']['verdict']:5} recomputed={verdict:5}  "
          f"[{'ok' if verdict == gate['kill_gate']['verdict'] else 'MISMATCH'}]")

    if ok:
        print(f"\n  VERIFY OK — {os.path.basename(path)} reproduces (verdict={verdict})")
        return 0
    print(f"\n  VERIFY FAILED — recomputed signals/verdict differ from stored")
    return 1


def _load_run(name: str) -> dict[str, Any]:
    """Resolve a referenced run by basename against F0's OUTPUT_DIR and load it."""
    path = name if os.path.isabs(name) else os.path.join(cl.OUTPUT_DIR, os.path.basename(name))
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def write_gate(gate: dict[str, Any], args: argparse.Namespace) -> str:
    os.makedirs(cl.OUTPUT_DIR, exist_ok=True)
    fname = f"{args.name}_gate_sim_seed{args.seed}_{cl.timestamp()}_run.json"
    path = os.path.join(cl.OUTPUT_DIR, fname)
    with open(path, "w") as f:
        json.dump(gate, f, indent=2, default=str)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description="CQL F1 — DRAFT kill-gate (sim, toy scale)")
    ap.add_argument("--generations", type=int, default=15)
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--name", type=str, default="cql_f1")
    ap.add_argument("--poke-gen", dest="poke_gen", type=int, default=POKE_GEN_DEFAULT)
    ap.add_argument("--adapt-min", dest="adapt_min", type=float, default=ADAPT_MIN)
    ap.add_argument("--verify", type=str, default=None,
                    help="path to a gate JSON; re-derive signals + verdict and exit")
    args = ap.parse_args()

    if args.verify is not None:
        raise SystemExit(verify_run(args.verify))

    gate, _closed_path, _yoked_path = run_gate(args)
    path = write_gate(gate, args)
    print(f"\n  -> {path}")


if __name__ == "__main__":
    main()
