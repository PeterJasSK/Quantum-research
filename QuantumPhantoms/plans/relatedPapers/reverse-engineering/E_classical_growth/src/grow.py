"""Grow one lung tumor from contract inputs and write a `growth_trajectory` (feature plan AC-6 … AC-15).

    python -m E_classical_growth.src.grow                       # all inputs = shared/stubs
    python -m E_classical_growth.src.grow --site-id S002        # verification override of the draw's site
    python -m E_classical_growth.src.grow --certificate <file> --draw <file> --masks <file> ...

Exit codes: 0 ok · 1 invalid input · 2 draw rejected (certificate not `pass`) · 3 growth failed (size/day not
reached within --max-days). Every PRNG is shared.seedhash.rng(certificate seed, "E/engine/<draw>/<site>").
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


from E_classical_growth.src import lattice
from E_classical_growth.src.engine import LungEngine, LungParams
from E_classical_growth.src.io_contracts import (DEFAULTS, PARAMS, certificate_refusal, load_masks, load_seed_shape,
                                                 read_json, validate_inputs, write_trajectory)
from shared import RE_ROOT
from shared.runrecord import start_run
from shared.seedhash import rng
from shared.validate import validate_file

LETTER = "E_classical_growth"
TOOL = "E_classical_growth.src.grow"


def _path(p: str | Path) -> Path:
    p = Path(p)
    return p if p.is_absolute() else (Path.cwd() / p).resolve()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--masks", default=DEFAULTS["anatomy_masks"], type=_path)
    ap.add_argument("--sites", default=DEFAULTS["site_candidates"], type=_path)
    ap.add_argument("--draw", default=DEFAULTS["tumor_draw"], type=_path)
    ap.add_argument("--certificate", default=DEFAULTS["certificate"], type=_path)
    ap.add_argument("--seed-shape", default=DEFAULTS["seed_shape"], type=_path)
    ap.add_argument("--site-id", help="override the draw's site (verification only; marks the output stub)")
    ap.add_argument("--follow-up-days", type=int, default=90)
    ap.add_argument("--every", type=int, default=0, help="extra 'other' snapshot every N days (0 = none)")
    ap.add_argument("--max-days", type=int, default=3000)
    ap.add_argument("--lattice-mm", type=float, default=None, help="default: params_lung.json lattice_mm")
    a = ap.parse_args(argv)
    inputs = {"anatomy_masks": a.masks, "site_candidates": a.sites, "tumor_draw": a.draw,
              "certificate": a.certificate, "seed_shape": a.seed_shape}

    # certificate gate first: a failed draw is rejected and logged, nothing else happens
    cert = read_json(a.certificate)
    refusal = certificate_refusal(cert)
    if refusal:
        run = start_run(LETTER, "grow-rejected", tool=TOOL)
        run.add_input(a.certificate, "certificate")
        rj = run.finish(refusal)
        print(f"{refusal}\nrun record: {rj}", file=sys.stderr)
        return 2

    errs = validate_inputs(inputs)
    if errs:
        print("invalid input:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 1
    docs = {k: read_json(p) for k, p in inputs.items()}
    draw = docs["tumor_draw"]
    notes = []
    site_id = a.site_id or draw["site_id"]
    site = next((s for s in docs["site_candidates"]["sites"] if s["site_id"] == site_id), None)
    if site is None:
        print(f"invalid input: site '{site_id}' not in {a.sites}", file=sys.stderr)
        return 1
    if a.site_id and a.site_id != draw["site_id"]:
        notes.append(f"--site-id override: draw {draw['draw_id']} targets {draw['site_id']}, grown at {site_id} "
                     "(verification run, output marked stub)")
    stub = bool(any(d.get("stub") for d in docs.values()) or notes)

    cfg = json.loads(PARAMS.read_text())
    tp = cfg["types"][draw["type"]]
    params = LungParams.from_json(tp)
    sp = a.lattice_mm or cfg["lattice_mm"]
    seed_hex = cert["extracted_seed_hex"]

    run = start_run(LETTER, f"grow-{site_id}", seed_hex=seed_hex, tool=TOOL)
    for c, p in inputs.items():
        run.add_input(p, c)
    run.add_input(PARAMS, "params_lung")

    vols, meta = load_masks(a.masks)
    # box: drawn size + expected follow-up growth (VDT target) + 5 mm
    fu_diam = draw["size_mm"] * 2 ** (a.follow_up_days / (3 * tp["vdt_target_days"]))
    env = lattice.build(vols, meta, site, 1.3 * fu_diam / 2 + 5.0, sp, tuple(cfg["lung_hu_bounds"]))
    occ, occ_sp = load_seed_shape(a.seed_shape)
    seed = lattice.place_seed(env, occ, occ_sp)
    ratio = (occ_sp / sp) ** 3
    notes += env.notes + [f"seed: {int(seed.sum())} voxels on the lattice (seed_shape n_cells {int(occ.sum())} "
                          f"× volume ratio {ratio:g} = {occ.sum() * ratio:g})"]
    for n in notes:
        print(n)

    engine = LungEngine(env, seed, params, rng(seed_hex, f"E/engine/{draw['draw_id']}/{site_id}"))
    snaps, per_day, failure = engine.run(draw["size_mm"], a.follow_up_days, a.every, a.max_days)
    if failure:
        rj = run.finish(f"growth failed: {failure}")
        print(f"growth failed: {failure}\nrun record: {rj}", file=sys.stderr)
        return 3

    out = write_trajectory(run.path / "growth_trajectory", run=run, inputs=inputs, stub=stub, site=site, draw=draw,
                           seed_hex=seed_hex, env=env, snaps=snaps, per_day=per_day,
                           vessel_entered_day=engine.vessel_entered_day, notes=notes, params_type=draw["type"])
    _, verrs = validate_file(out)
    if verrs:
        raise ValueError(f"{out} violates growth_trajectory:\n  " + "\n  ".join(verrs))
    run.add_output(out, "growth_trajectory")
    for s in read_json(out)["snapshots"]:
        run.add_output(out.parent / s["npz"]["path"], "growth_trajectory")
    summ = read_json(out.parent / "growth_summary.json")
    rj = run.finish(f"{site_id} {site['context']['placement_class']} {draw['type']}: "
                    + "; ".join(f"{s['role']} day {s['day']} Ø {s['eq_diameter_mm']} mm" for s in summ["snapshots"]))
    for s in summ["snapshots"]:
        print(f"{s['role']:9s} day {s['day']:5d}  Ø {s['eq_diameter_mm']:6.2f} mm  prolif {s['f_prolif']:.2f} "
              f"dormant {s['f_dormant']:.2f} necrotic {s['f_necrotic']:.2f}")
    print("checks: " + json.dumps(summ["checks"]))
    print(f"run dir: {run.path.relative_to(RE_ROOT)}\nmanifest: {out.relative_to(RE_ROOT)}\nrun record: "
          f"{rj.relative_to(RE_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
