"""F end to end: growth snapshot → realistic, scanner-matched lesion inside the 3-D host → hybrid_volume.

    python -m F_render.src.render                       # all inputs default to shared/stubs/ (fitted library if present)
    python -m F_render.src.render --step 0 --tag baseline
    python -m F_render.src.render --masks <anatomy_masks.json> --sites <sites.json> --fingerprint <fp.json> ...

The seed is the certificate's extracted seed; a `fail` certificate rejects the draw (exit 2, nothing written).
Same inputs → byte-identical hybrid_ct.nii.gz. Output dir = the run dir F_render/runs/<ts>-<tag>/ (gitignored).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path


from F_render.src import io as fio
from F_render.src.insert import insert
from F_render.src.lesion_render import render_lesion
from F_render.src.params import RenderParams
from shared.runrecord import start_run
from shared.volumes import write_volume


def run_render(a) -> Path:
    seed_hex, _, cert_p = fio.seed_from_certificate(a.certificate)        # raises RejectedDraw on fail
    traj, traj_p = fio.load(a.trajectory, "growth_trajectory")
    masks, masks_p = fio.load(a.masks, "anatomy_masks")
    sites, sites_p = fio.load(a.sites, "site_candidates")
    draw, draw_p = fio.load(a.draw, "tumor_draw")
    lib, lib_p = fio.load(a.library, "lesion_model_library")
    fp, fp_p = fio.load(a.fingerprint, "scanner_fingerprint")
    if traj["site_id"] != draw["site_id"]:
        raise ValueError(f"trajectory site {traj['site_id']} != draw site {draw['site_id']}")
    if sites["host_scan_id"] != masks["host_scan_id"] or fp["host_scan_id"] != masks["host_scan_id"]:
        raise ValueError("sites / fingerprint / masks refer to different host scans")
    site = fio.site_by_id(sites, draw["site_id"])
    state, snap = fio.snapshot(traj, traj_p, a.step)
    vols = fio.host_volumes(masks, masks_p)
    meta = vols["meta"]
    sp = meta["spacing_mm_xyz"][::-1]

    p = RenderParams()
    if a.no_mass_effect:
        p = replace(p, mass_effect=False)
    if a.psf:
        p = replace(p, psf_sigma_mm_zyx=tuple(a.psf))
    run = start_run("F_render", a.tag, seed_hex=seed_hex, tool="F_render.src.render")
    for path, contract in ((cert_p, "certificate"), (traj_p, "growth_trajectory"), (masks_p, "anatomy_masks"),
                           (sites_p, "site_candidates"), (draw_p, "tumor_draw"), (lib_p, "lesion_model_library"),
                           (fp_p, "scanner_fingerprint")):
        run.add_input(path, contract)

    les = render_lesion(state, traj["origin_mm_lps"], traj["spacing_mm_xyz"], meta, site["center_mm_lps"],
                        draw, lib, p, seed_hex)
    hybrid, lesion_mask, diag = insert(vols["host_ct"], vols["lungs"], vols.get("vessels"), sp, les, draw["type"],
                                       fp, p, seed_hex)

    out = Path(a.out) if a.out else run.path
    out.mkdir(parents=True, exist_ok=True)
    files = {"host_ct": write_volume(out / "host_ct.nii.gz", vols["host_ct"], meta["spacing_mm_xyz"], meta["origin_mm_lps"]),
             "hybrid_ct": write_volume(out / "hybrid_ct.nii.gz", hybrid, meta["spacing_mm_xyz"], meta["origin_mm_lps"]),
             "lesion_mask": write_volume(out / "lesion_mask.nii.gz", lesion_mask, meta["spacing_mm_xyz"],
                                         meta["origin_mm_lps"])}
    man = out / "hybrid_volume.json"
    params = p.as_dict()
    lnps = fp_p.parent / "local_nps.ref.json"
    if lnps.exists():
        params["local_nps_ref"] = fio.file_ref(fio.ref(lnps, json.loads(lnps.read_text())["local_nps"]), man)
    params["diagnostics"] = {k: v for k, v in {**les.diag, **diag}.items()}
    doc = fio.envelope("hybrid_volume", "F_render.src.render", run.code_hash, run.path.name,
                       [fio.up_ref(c, pth, man) for pth, c in
                        ((cert_p, "certificate"), (traj_p, "growth_trajectory"), (masks_p, "anatomy_masks"),
                         (sites_p, "site_candidates"), (draw_p, "tumor_draw"), (lib_p, "lesion_model_library"),
                         (fp_p, "scanner_fingerprint"))])
    doc.update({"host_scan_id": masks["host_scan_id"], "site_id": draw["site_id"], "draw_id": draw["draw_id"],
                "files": {k: fio.file_ref(v, man) for k, v in files.items()},
                "insertion": {"method": p.method, "params": json.loads(json.dumps(params, default=float))},
                "seed_hex": seed_hex, "fingerprint_ref": fio.file_ref(fp_p, man),
                "trajectory_ref": fio.file_ref(traj_p, man), "snapshot_step": snap["step"]})
    fio.write_manifest(man, doc)
    run.add_output(man, "hybrid_volume")
    d = params["diagnostics"]
    note = (f"{draw['type']}/{draw['margin']} step {snap['step']} ({snap['role']}): lesion "
            f"{d['lesion_volume_mm3_partial']:.0f} mm³ (lattice {d['lattice_volume_mm3']:.0f}), "
            f"σ in/out {d['sigma_in_hu']:.1f}/{d['sigma_out_hu']:.1f} HU, changed voxels {d['n_changed_voxels']}")
    run.finish(note)
    print(note)
    print(man)
    if a.export:
        from F_render.src.export_slices import export
        for f in export(man, tag=a.tag):
            print(f)
    return man


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    S = fio.STUB
    ap.add_argument("--trajectory", default=str(S["trajectory"]))
    ap.add_argument("--step", type=int, default=None, help="snapshot step (default: last)")
    ap.add_argument("--masks", default=str(S["masks"]))
    ap.add_argument("--sites", default=str(S["sites"]))
    ap.add_argument("--draw", default=str(S["draw"]))
    ap.add_argument("--certificate", default=str(S["certificate"]))
    ap.add_argument("--library", default=str(fio.FITTED_LIBRARY if fio.FITTED_LIBRARY.exists() else S["library"]))
    ap.add_argument("--fingerprint", default=str(S["fingerprint"]))
    ap.add_argument("--psf", type=float, nargs=3, default=None, help="override PSF σ (mm, z y x)")
    ap.add_argument("--no-mass-effect", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--tag", default="render")
    ap.add_argument("--export", action="store_true", help="also write the final 2-D PNG slices to F_render/figures/")
    a = ap.parse_args(argv)
    try:
        run_render(a)
    except fio.RejectedDraw as e:
        print(f"REJECTED: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
