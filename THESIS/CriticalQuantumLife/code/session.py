#!/usr/bin/env python3
"""Critical Quantum Life — F4: interactive poke() + inter-batch state persistence.

The "life you can poke" spine. Wraps F0's closed loop (closed_loop.run_closed_loop) with:

  1. an INTERACTIVE poke() API (AC-F4.1) — a human calls it mid-session (between batches)
     to change the contingency / selection pressure / inject a stimulus. It is NOT the
     scripted --poke-gen (that stays in F0 only for F1's non-interactive gate); F4's poke
     has no default generation and records a poke event.

  2. inter-batch STATE PERSISTENCE (AC-F4.2) — the inherited population state persists to
     disk between runs so a new run resumes the *same* population, not a redraw.

     HONEST PERSISTENCE (plan §9, Q_STATE). F0's draw_thetas is a pure function of
     (seed, generation, mut_scale): there is NO genome carried gen-to-gen and the PRNG
     path is stateless (QRNG is external / non-reproducible). So the genealogy is rebuilt
     from seed + the generation counter — NOT from a persisted statevector and NOT from a
     genome_thetas snapshot. The real carry-over state that makes a resume the SAME
     population is:
         running_dist  — the population's running outcome distribution (classical memory)
         mut_scale     — the feedback-adapted explore pressure
         generation    — the counter (drives draw_thetas -> the ongoing genealogy)
         recent        — surprise history: the is_surprising() baseline (load-bearing)
         active_hist   — per-gen surprising bools: the running_sigma() window (load-bearing)
     Dropping recent/active_hist would reset the surprise baseline at the boundary and turn
     the spike-then-relax into a reset artifact — a bug per epic §3. Do not overclaim a
     teleported statevector: on hardware the population is re-prepared each batch.

  3. a SESSION DRIVER (AC-F4.3) — run a batch, allow a poke, run the next batch continuing
     from persisted state, demonstrating a spike-then-relax across the batch boundary.

This is the ONE poke semantics both F5 (between hardware batches) and F6 (web POKE button)
call, so their results are comparable (AC-F4.4). POKE_KINDS is the shared vocabulary.

Run (sim):
    cd THESIS/CriticalQuantumLife/code
    python session.py --batches 2 --generations 8 --poke flip_expected@boundary \\
        --width 4 --seed 100 --name cql_f4
    # then resume the SAME population from the saved state (continuation, not redraw):
    python session.py --resume ../research_runs/sess_XXXX_state.json --generations 8
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import closed_loop as cl                      # F0 engine + run-JSON schema (reused, not rewritten)

# The canonical poke vocabulary — F5's batch driver and F6's button labels map 1:1 to these.
POKE_KINDS = ("flip_expected", "alter_selection", "inject_stimulus")


def _now_iso() -> str:
    """Wall-clock for the poke-log audit trail ONLY (never the session id — plan §9)."""
    return datetime.now(timezone.utc).isoformat()


def new_session_id(seed: int, name: str) -> str:
    """Short DETERMINISTIC id from seed + name (no wall-clock, so resume/verify is stable)."""
    h = hashlib.sha1(f"{name}:{seed}".encode()).hexdigest()[:8]
    return f"sess_{h}"


def _args_to_dict(args: argparse.Namespace) -> dict[str, Any]:
    """The F0 knobs needed to rebuild a run — persisted so --resume needs no re-supply."""
    keys = ("width", "shots", "seed", "name", "mut_scale", "poke_gen", "death",
            "interaction", "nbins", "delta", "gamma", "sim", "qrng_url")
    return {k: getattr(args, k) for k in keys if hasattr(args, k)}


def _dict_to_args(d: dict[str, Any], generations: int) -> argparse.Namespace:
    """Rebuild an F0-shaped Namespace from a persisted arg dict (+ this batch's length)."""
    ns = argparse.Namespace(**d)
    ns.generations = generations
    return ns


class Session:
    """One session = one persistent population threaded across batches by session_id.

    poke() queues a poke; run_batch() continues the persisted population (applying any
    queued poke on the batch's first generation); save()/load() persist the carry-over
    state so a later run resumes the SAME population."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.session_id = new_session_id(args.seed, args.name)
        self.state: dict[str, Any] = {        # gen-0 seed of the real carry-over state (Q_STATE)
            "generation": 0,
            "running_dist": {},
            "mut_scale": args.mut_scale,
            "recent": [],
            "active_hist": [],
        }
        self.poke_log: list[dict[str, Any]] = []
        self.meta: dict[str, Any] | None = None      # F0 meta from the last batch (plan §4)
        self._args_snapshot: dict[str, Any] = _args_to_dict(args)
        self._pending_poke: dict[str, Any] | None = None

    # -- AC-F4.1: interactive poke -------------------------------------------------------
    def poke(self, kind: str, **params: Any) -> None:
        """Queue an INTERACTIVE poke, applied on the FIRST generation of the next batch.
        Records a poke event; does NOT itself run circuits (AC-F4.1)."""
        if kind not in POKE_KINDS:
            raise ValueError(f"unknown poke kind {kind!r}; expected one of {POKE_KINDS}")
        self._pending_poke = {"kind": kind, "params": dict(params)}
        self.poke_log.append({"at_generation": self.state["generation"], "kind": kind,
                              "params": dict(params), "wall_clock": _now_iso()})
        print(f"[poke] queued {kind}{params or ''} at generation {self.state['generation']}")

    # -- AC-F4.3: continue the persisted population --------------------------------------
    def run_batch(self, n_gens: int) -> dict[str, Any]:
        """Continue cl.run_closed_loop from self.state for n_gens (applying any queued poke
        on the first gen), update self.state from the loop's final_state, return the F0
        run-JSON stamped with session_id + poke_events."""
        batch_args = _dict_to_args(self._args_snapshot, n_gens)
        client = cl.make_client(batch_args)   # sim -> None (PRNG); hardware is F5
        resume_state = dict(self.state)
        if self._pending_poke is not None:
            resume_state["pending_poke"] = self._pending_poke
        run, _stim = cl.run_closed_loop(batch_args, client, resume_state=resume_state)
        self.state = run.pop("final_state")   # the carry-over state for the NEXT batch
        self._pending_poke = None
        run["meta"]["session_id"] = self.session_id
        self.meta = run["meta"]
        return run

    # -- AC-F4.2: persist / resume the SAME population -----------------------------------
    def save(self, path: str | None = None) -> str:
        """Write <session_id>_state.json (plan §4): meta + carry-over state + poke_log."""
        os.makedirs(cl.OUTPUT_DIR, exist_ok=True)
        if path is None:
            path = os.path.join(cl.OUTPUT_DIR, f"{self.session_id}_state.json")
        payload = {
            "session_id": self.session_id,
            "meta": self.meta,                # F0 meta (arm, width, backend, mut_scale, ...)
            "state": self.state,              # generation, running_dist, mut_scale, recent, active_hist
            "poke_log": self.poke_log,        # AC-F4.1: every poke, in order
            "resume_args": self._args_snapshot,   # F0 knobs so --resume needs no re-supply
        }
        with open(path, "w") as f:
            json.dump(payload, f, indent=2, default=str)
        return path

    @classmethod
    def load(cls, path: str, args: argparse.Namespace | None = None) -> "Session":
        """Reconstruct a Session from a state file; a subsequent run_batch resumes the SAME
        population (same running_dist/mut_scale/recent/active_hist, continued generation)."""
        with open(path) as f:
            payload = json.load(f)
        arg_dict = payload.get("resume_args") or (_args_to_dict(args) if args else None)
        if arg_dict is None:
            raise ValueError("state file has no resume_args; pass args= to Session.load")
        ns = _dict_to_args(arg_dict, generations=0)
        self = cls(ns)
        self.session_id = payload["session_id"]
        self.state = payload["state"]
        self.poke_log = payload.get("poke_log", [])
        self.meta = payload.get("meta")
        self._args_snapshot = arg_dict
        return self


def _parse_poke_spec(spec: str | None) -> tuple[str | None, str | int | None]:
    """Parse '<kind>@<when>' (when = 'boundary' or an int gen). Returns (kind, when)."""
    if not spec:
        return None, None
    kind, _, when = spec.partition("@")
    if kind not in POKE_KINDS:
        raise SystemExit(f"[ABORT] --poke kind {kind!r} not in {POKE_KINDS}")
    when = when or "boundary"
    if when != "boundary":
        when = int(when)
    return kind, when


def _print_boundary_trace(runs: list[dict[str, Any]], poke_at: int | None) -> None:
    """Print the surprise trace across all batch boundaries — the spike-then-relax (AC-F4.3)."""
    print("\n=== surprise trace across the session (spike-then-relax at the poke) ===")
    print("  batch  gen  surprise  witness   active  poke")
    for b, run in enumerate(runs):
        for r in run["generations"]:
            mark = " <-- POKE" if r["poke"] else ""
            print(f"    {b:3d}  {r['gen']:4d}   {r['surprise']:7.3f}  "
                  f"{r['witness_signal']:+.3f}   {str(r['active']):>5}{mark}")
    if poke_at is not None:
        print(f"  (poke at generation {poke_at}: expect a surprise spike then a descent over "
              f"the following gens — F2's tau can be fit on it)")


def main() -> None:
    ap = argparse.ArgumentParser(description="CQL F4 — interactive poke + inter-batch persistence")
    ap.add_argument("--generations", type=int, default=8, help="generations per batch")
    ap.add_argument("--batches", type=int, default=2)
    ap.add_argument("--poke", type=str, default="flip_expected@boundary",
                    help="'<kind>@<when>'; kind in flip_expected|alter_selection|inject_stimulus; "
                         "when = 'boundary' or an int gen")
    ap.add_argument("--resume", type=str, default=None, help="resume from a <session>_state.json")
    ap.add_argument("--width", type=int, default=4)
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--name", type=str, default="cql_f4")
    ap.add_argument("--mut-scale", dest="mut_scale", type=float, default=cl.DEFAULT_MUT)
    ap.add_argument("--poke-gen", dest="poke_gen", type=int, default=None)
    ap.add_argument("--death", choices=["unitary", "damping"], default="unitary")
    ap.add_argument("--interaction", choices=["none", "nn"], default="nn")
    ap.add_argument("--nbins", type=int, default=10)
    ap.add_argument("--delta", type=float, default=cl.q4.AGING_DELTA)
    ap.add_argument("--gamma", type=float, default=cl.q4.DAMP_GAMMA)
    ap.add_argument("--sim", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--qrng-url", dest="qrng_url", type=str, default=cl.QEAAS_URL_DEFAULT)
    args = ap.parse_args()

    # -- resume path: continue the SAME population from a saved state --------------------
    if args.resume:
        sess = Session.load(args.resume, args)
        start = sess.state["generation"]
        print(f"=== CQL F4 resume {sess.session_id} from generation {start} "
              f"(running_dist has {len(sess.state['running_dist'])} bins) ===")
        run = sess.run_batch(args.generations)
        name = f"{args.name}_resume"
        path = cl.write_run(run, _dict_to_args({**sess._args_snapshot, "name": name}, args.generations))
        state_path = sess.save()
        print(f"  -> {path}")
        print(f"  -> state {state_path}")
        _print_boundary_trace([run], None)
        print(f"\n  resumed at generation {start} (NOT 0) — continuation, not redraw (AC-F4.2)")
        return

    # -- fresh session: batch -> poke at boundary -> batch (AC-F4.3) ---------------------
    kind, when = _parse_poke_spec(args.poke)
    sess = Session(args)
    print(f"=== CQL F4 session {sess.session_id}: {args.batches} batches x {args.generations} gens, "
          f"poke={kind}@{when} width={args.width} seed={args.seed} ===")
    runs: list[dict[str, Any]] = []
    poke_at: int | None = None
    for b in range(args.batches):
        if kind is not None and ((when == "boundary" and b == 1)
                                 or (isinstance(when, int) and sess.state["generation"] == when)):
            sess.poke(kind)
            poke_at = sess.state["generation"]
        run = sess.run_batch(args.generations)
        path = cl.write_run(run, _dict_to_args({**sess._args_snapshot, "name": f"{args.name}_b{b}"},
                                               args.generations))
        print(f"  batch {b}: gens {run['generations'][0]['gen']}..{run['generations'][-1]['gen']}  -> {path}")
        runs.append(run)
    state_path = sess.save()
    print(f"  -> state {state_path}")
    _print_boundary_trace(runs, poke_at)


if __name__ == "__main__":
    main()
