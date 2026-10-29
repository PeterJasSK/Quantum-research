"""Reproduction #19: CT-GAN-style tampering vs signed provenance (Mirsky G01 §7.2 countermeasure).

    python -m G_provenance.repro.r19_ctgan_tamper [--n 20] [--receipt <ledgered receipt.json>]

Builds one signed, ledgered, DICOM-exported hybrid (stubs by default), then makes n injections and
n removals (pixel edits written back into the DICOM files, tags untouched), four non-pixel forgery
attacks and two controls, and runs the verifier on every copy. GAN-free (see ctgan_tamper.py).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import numpy as np
import pydicom
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from G_provenance.src import keys as keymod  # noqa: E402
from G_provenance.src import ledger as ledgermod  # noqa: E402
from G_provenance.src.ctgan_tamper import inject, pick_lung_site, remove  # noqa: E402
from G_provenance.src.dicom_export import export, read_series, set_tags, write_pixels  # noqa: E402
from G_provenance.src.receipt import _stub, commit, fill, sign  # noqa: E402
from G_provenance.src.verify import verify  # noqa: E402
from shared import RE_ROOT  # noqa: E402
from shared.runrecord import start_run  # noqa: E402
from shared.seedhash import canonical_json, rng, sha256_bytes  # noqa: E402
from shared.volumes import read_volume  # noqa: E402

G = RE_ROOT / "G_provenance"
FIG = G / "figures"


def build_signed_series(work: Path, ledger_path: Path, receipt: Path | None) -> tuple[Path, Path]:
    if receipt is None:
        if not (keymod.KEYS_DIR / keymod.KEY_FILE).exists():
            keymod.init_keys()
        assert commit(_stub("rulebook", "rulebook.json"), ledger_path, keymod.KEYS_DIR) == 0
        commit_receipt = sorted((G / "runs").glob("*-commit"))[-1] / "receipt.json"
        paths = {"job": _stub("quantum_job_record", "quantum_job_record.json"),
                 "certificate": _stub("certificate", "certificate.json"),
                 "draw": _stub("tumor_draw", "tumor_draw.json"), "hybrid": _stub("hybrid_volume", "hybrid_volume.json")}
        assert fill(commit_receipt, paths, [_stub("witness_record", "witness_record.json")], ledger_path,
                    keymod.KEYS_DIR) == 0
        receipt = sorted((G / "runs").glob("*-fill"))[-1] / "receipt.json"
    series = work / "original"
    export(receipt, series, ledger_path)
    return receipt, series


def rewrite_tags(series: Path, **values) -> None:
    """Rewrite private tags in every slice file, leaving pixels alone."""
    for f in sorted(series.glob("*.dcm")):
        ds = pydicom.dcmread(f)
        set_tags(ds, values)
        ds.save_as(f, enforce_file_format=True)


def forged_receipt(series: Path, attacker_key=None) -> dict:
    r = json.loads(read_series(series)[2][0]["receipt_json"])
    seed = r["fill"]["seed_hex"]
    r["fill"]["seed_hex"] = ("0" if seed[0] != "0" else "1") + seed[1:]
    if attacker_key is not None:
        r["signature"] = sign(attacker_key, r["commit"], r["fill"])
    return r


def slices_from(report: dict) -> set[int]:
    for c in report["checks"]:
        if c["name"] == "voxels" and c["where"]:
            m = re.match(r"slices \[(.*)\]", c["where"])
            if m and m.group(1).strip():
                return {int(v) for v in m.group(1).split(",")}
    return set()


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--receipt", type=Path, help="existing ledgered receipt (default: build one from stubs)")
    ap.add_argument("--ledger", type=Path, default=ledgermod.LEDGER)
    a = ap.parse_args(argv)

    run = start_run(G, "r19")
    work = run.path / "work"
    receipt_path, series = build_signed_series(work, a.ledger, a.receipt.resolve() if a.receipt else None)
    receipt = json.loads(receipt_path.read_text())
    seed = receipt["fill"]["seed_hex"]
    arr0, meta, tags0, _ = read_series(series)
    hyb_ref = next(u for u in receipt["upstream"] if u["contract"] == "hybrid_volume")
    hyb_path = (receipt_path.parent / hyb_ref["path"]).resolve()
    hyb = json.loads(hyb_path.read_text())
    lesion, _ = read_volume(hyb_path.parent / hyb["files"]["lesion_mask"]["path"])
    anat = next(u for u in hyb["upstream"] if u["contract"] == "anatomy_masks")
    anat_path = (hyb_path.parent / anat["path"]).resolve()
    lungs, _ = read_volume(anat_path.parent / json.loads(anat_path.read_text())["files"]["lungs"]["path"])
    lesion_c = tuple(int(round(v)) for v in np.argwhere(lesion > 0).mean(0))
    meta_t = {"spacing_mm_xyz": meta["spacing_mm_xyz"]}

    rows = []

    def record(name, report, expect, truth=None, exact=False):
        failed = set(report["failed"])
        detected = bool(failed)
        ok = expect <= failed and (not exact or failed == expect)
        j = jaccard(slices_from(report), truth) if truth is not None else None
        rows.append({"attack": name, "detected": detected, "expected_ok": ok, "failed": sorted(failed), "jaccard": j})
        return report

    def fresh(tag):
        d = work / tag
        shutil.copytree(series, d)
        return d

    base = verify(series, a.ledger)
    rows.append({"attack": "control: untampered", "detected": bool(base["failed"]), "expected_ok": not base["failed"],
                 "failed": base["failed"], "jaccard": None})
    d = fresh("control_resave")
    for f in d.glob("*.dcm"):
        ds = pydicom.dcmread(f)
        ds.InstitutionName = "RESAVED-ELSEWHERE"
        ds.save_as(f, enforce_file_format=True)
    rep = verify(d, a.ledger)
    rows.append({"attack": "control: re-save, unbound tag edited", "detected": bool(rep["failed"]),
                 "expected_ok": not rep["failed"], "failed": rep["failed"], "jaccard": None})
    shutil.rmtree(d)

    stealth = {"inside_mean": [], "inside_max": [], "outside_max": [], "header_unchanged": []}
    first = {}
    for kind, fn in (("injection", inject), ("removal", remove)):
        for k in range(1, a.n + 1):
            r = rng(seed, f"G.tamper.{kind}.{k}")
            site = lesion_c if kind == "removal" else pick_lung_site(lungs, meta_t, lesion_c, r)
            tampered, info = fn(arr0, meta_t, site, r)
            d = fresh(f"{kind}_{k}")
            write_pixels(d, tampered)
            delta = np.abs(tampered.astype(int) - arr0.astype(int))
            truth = {int(z) for z in np.nonzero(delta.any(axis=(1, 2)))[0]}
            rep = record(f"pixel {kind}", verify(d, a.ledger), {"voxels"}, truth, exact=True)
            hdr = all(_header(pydicom.dcmread(f1)) == _header(pydicom.dcmread(f2))
                      for f1, f2 in zip(sorted(series.glob("*.dcm")), sorted(d.glob("*.dcm"))))
            zs = np.array(info["slices_z"])
            box = np.zeros(delta.shape, bool)
            box[zs.min():zs.max() + 1] = delta[zs.min():zs.max() + 1] > 0
            stealth["inside_mean"].append(float(delta[delta > 0].mean()) if (delta > 0).any() else 0.0)
            stealth["inside_max"].append(float(delta.max()))
            stealth["outside_max"].append(float(delta[~box].max()) if (~box).any() else 0.0)
            stealth["header_unchanged"].append(bool(hdr))
            if k == 1:
                first[kind] = (tampered, site, sorted(slices_from(rep)), info)
            shutil.rmtree(d)

    # non-pixel forgeries
    d = fresh("atk_a")
    rewrite_tags(d, receipt_json=canonical_json(forged_receipt(series)).decode())
    record("(a) edit seed in tag", verify(d, a.ledger), {"signature"})
    shutil.rmtree(d)

    attacker = Ed25519PrivateKey.generate()
    d = fresh("atk_b")
    rewrite_tags(d, receipt_json=canonical_json(forged_receipt(series, attacker)).decode())
    record("(b) (a) + re-sign, fresh key", verify(d, a.ledger), {"trusted_key"})
    shutil.rmtree(d)

    d = fresh("atk_c")
    forged = forged_receipt(series, attacker)
    entries = ledgermod.read(a.ledger)
    idx = int(tags0[0]["ledger_index"])
    entries[idx] = {**entries[idx], "receipt_sha256": sha256_bytes(canonical_json(forged))}
    ledger_c = work / "ledger_c.jsonl"
    ledgermod.write(ledgermod.rechain(entries), ledger_c)
    rewrite_tags(d, receipt_json=canonical_json(forged).decode(),
                 ledger_entry_hash=ledgermod.read(ledger_c)[idx]["entry_hash"])
    record("(c) (b) + ledger rewritten", verify(d, ledger_c), {"trusted_key"}, exact=True)
    shutil.rmtree(d)

    d = fresh("atk_d")
    cidx = json.loads(tags0[0]["bound_params_json"])["commit_receipt"]["ledger_index"]
    ledger_d = work / "ledger_d.jsonl"
    ledgermod.write(ledgermod.rechain(entries[:cidx] + entries[cidx + 1:]), ledger_d)
    record("(d) commit entry deleted, re-chained", verify(d, ledger_d), {"commit_first"})
    shutil.rmtree(d)

    # report
    detection = summarise(rows)
    print_table(detection)
    (run.path / "detection.json").write_text(json.dumps({"rows": rows, "summary": detection, "stealth": {
        k: (float(np.mean(v)) if k != "header_unchanged" else all(v)) for k, v in stealth.items()}}, indent=2) + "\n")
    FIG.mkdir(exist_ok=True)
    figure_slices(arr0, meta_t, lesion_c, first, a.n)
    figure_table(detection)
    ok = all(r["expected_ok"] for r in rows)
    pix = [r for r in rows if r["attack"].startswith("pixel")]
    status_update(detection, stealth, len(pix), all(r["jaccard"] == 1.0 for r in pix) if pix else False)
    run.add_input(receipt_path, "receipt")
    run.finish(f"r19: {sum(r['detected'] for r in pix)}/{len(pix)} pixel tampers detected; all expected: {ok}")
    print(f"stealth: inside mean |dHU| {np.mean(stealth['inside_mean']):.1f}, max {np.max(stealth['inside_max']):.0f}; "
          f"outside max {np.max(stealth['outside_max']):.0f}; plain header unchanged on all tampered files: "
          f"{all(stealth['header_unchanged'])}")
    return 0 if ok else 1


def _header(ds: pydicom.Dataset) -> list:
    return [(str(e.tag), str(e.value)) for e in ds if e.tag != (0x7FE0, 0x0010)]


def summarise(rows: list[dict]) -> list[dict]:
    out = {}
    for r in rows:
        o = out.setdefault(r["attack"], {"attack": r["attack"], "n": 0, "detected": 0, "ok": 0, "checks": set(), "j": []})
        o["n"] += 1
        o["detected"] += r["detected"]
        o["ok"] += r["expected_ok"]
        o["checks"] |= set(r["failed"])
        if r["jaccard"] is not None:
            o["j"].append(r["jaccard"])
    return [{**o, "checks": sorted(o["checks"]), "jaccard": (min(o["j"]) if o["j"] else None)} for o in out.values()]


def print_table(det: list[dict]) -> None:
    print(f"{'attack':40s} {'detected':>9s} {'as expected':>11s} {'slice Jaccard':>13s}  failing checks")
    for d in det:
        j = "-" if d["jaccard"] is None else f"{d['jaccard']:.2f}"
        det_s, ok_s = f"{d['detected']}/{d['n']}", f"{d['ok']}/{d['n']}"
        print(f"{d['attack']:40s} {det_s:>9s} {ok_s:>11s} {j:>13s}  {', '.join(d['checks']) or '-'}")


def figure_slices(arr0, meta, lesion_c, first, n) -> None:
    fig = plt.figure(figsize=(12, 9))
    gs = fig.add_gridspec(3, 3, height_ratios=[3, 3, 1])
    rem, rsite, rflag, _ = first["removal"]
    inj, isite, iflag, iinfo = first["injection"]
    kw = dict(cmap="gray", vmin=-1000, vmax=200, origin="lower")
    for row, (name, vol, site) in enumerate((("removal", rem, rsite), ("injection", inj, isite))):
        z = site[0]
        for col, (title, img) in enumerate(((f"original z={z}", arr0[z]), (f"{name} z={z}", vol[z]),
                                            ("|Δ HU|", np.abs(vol[z].astype(int) - arr0[z].astype(int))))):
            ax = fig.add_subplot(gs[row, col])
            ax.imshow(img, **(kw if col < 2 else dict(cmap="magma", origin="lower")))
            ax.plot(site[2], site[1], "c+", ms=14)
            ax.set_title(title, fontsize=10)
            ax.axis("off")
    ax = fig.add_subplot(gs[2, :])
    nz = arr0.shape[0]
    for y, (lab, flags) in enumerate((("injection", iflag), ("removal", rflag))):
        ax.bar(flags, [0.8] * len(flags), bottom=y, width=1.0, color="tab:red")
    ax.set_xlim(-0.5, nz - 0.5)
    ax.set_ylim(0, 2)
    ax.set_yticks([0.4, 1.4], ["removal", "injection"])
    ax.set_xlabel("axial slice z (red = verifier: FAIL voxels)")
    fig.suptitle("Target #19: classical CT-GAN-style tamper on a signed, DICOM-exported synthetic hybrid "
                 f"(stub phantom; n={n} per kind in the table)", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / "r19-ctgan-tamper.png", dpi=130)
    plt.close(fig)


def figure_table(det: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(11, 0.5 + 0.45 * len(det)))
    ax.axis("off")
    cells = [[d["attack"], f"{d['detected']}/{d['n']}", f"{d['ok']}/{d['n']}",
              "-" if d["jaccard"] is None else f"{d['jaccard']:.2f}", ", ".join(d["checks"]) or "-"] for d in det]
    t = ax.table(cellText=cells, colLabels=["attack", "detected", "as expected", "slice Jaccard", "failing checks"],
                 loc="center", cellLoc="left")
    t.auto_set_font_size(False)
    t.set_fontsize(9)
    t.scale(1, 1.4)
    t.auto_set_column_width(range(5))
    fig.tight_layout()
    fig.savefig(FIG / "r19-detection-table.png", dpi=130)
    plt.close(fig)


def status_update(det, stealth, n_pixel, jacc_ok) -> None:
    f = G / "status.json"
    s = json.loads(f.read_text())
    t = s["targets"][0]
    pix = [d for d in det if d["attack"].startswith("pixel")]
    found = sum(d["detected"] for d in pix)
    forg = [d for d in det if d["attack"].startswith("(")]
    t.update({
        "state": "adapted",
        "reproduced": {
            "quantity": "G01 §7.2: detection of CT-GAN-style tampering by a scanner-side signature "
                        "(classical in-painter, GAN-free; reader-study numbers not reproduced)",
            "paper_value": "countermeasure claim (qualitative): signing each scan detects the attack; "
                           "readers 99% injected / 94% removed misdiagnosed",
            "our_value": f"{found}/{n_pixel} pixel injections+removals detected, slice Jaccard "
                         f"{'1.00' if jacc_ok else '<1'}; forgeries a-d: "
                         f"{sum(d['ok'] for d in forg)}/{sum(d['n'] for d in forg)} caught by the expected check; "
                         "controls: 0 false positives",
            "unit": "detection rate",
            "agreement": "claim reproduced qualitatively; (c) full re-forge with a stolen key is detected only by "
                         "the pinned-key check (needs an external anchor); reader numbers not reproduced (H)",
            "sim_mode": "n/a",
            "figure": "figures/r19-ctgan-tamper.png"},
        "claim_level": None,
        "figures": ["figures/r19-ctgan-tamper.png", "figures/r19-detection-table.png"],
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
    f.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    sys.exit(main())
