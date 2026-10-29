"""In-context visual Turing test kit (protocol of Chuquicusma et al., F10; benchmark 64-66 %, goal ~ 50 %).

    python -m H_analysis.src.turing_kit --manifest <cohort.json> --lidc-ref <run> [--n 40]

Writes runs/<ts>-turing/{kit.html, key.json}: one self-contained offline page (inline PNG data URIs, no CDN).
Axial lung-window crop 96 x 96 mm through the lesion centroid, real and synthetic shuffled, size/type-matched.
The reader downloads answers.json; score it with `python -m H_analysis.src.turing_score answers.json key.json`.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from H_analysis.src import lidc_ref, manifest, roi  # noqa: E402
from shared import runrecord, seedhash, volumes  # noqa: E402

CTX_MM = 96
WINDOW = (-1350.0, 150.0)  # lung window


def png_uri(slice2d: np.ndarray) -> str:
    img = np.clip((slice2d - WINDOW[0]) / (WINDOW[1] - WINDOW[0]), 0, 1)
    buf = io.BytesIO()
    plt.imsave(buf, img, cmap="gray", format="png", vmin=0, vmax=1)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def synthetic_slice(c: dict, i: int) -> np.ndarray:
    h, hp = c["obj"]["hybrids"][i], c["files"]["hybrids"][i]
    ref = {k: (hp.parent / v["path"]).resolve() for k, v in h["files"].items()}
    hyb, meta = volumes.read_volume(ref["hybrid_ct"])
    mask, _ = volumes.read_volume(ref["lesion_mask"])
    sx, sy, sz = meta["spacing_mm_xyz"]
    cen = np.argwhere(mask > 0).mean(0)
    return roi.crop_iso(hyb, (sz, sy, sx), cen, CTX_MM)[CTX_MM // 2]


def real_slice(scan, item: dict) -> np.ndarray:
    vol = np.transpose(scan.to_volume(verbose=False), (2, 0, 1)).astype(np.float32)
    sp = (float(scan.slice_thickness), float(scan.pixel_spacing), float(scan.pixel_spacing))
    return roi.crop_iso(vol, sp, item["centroid_zyx_vox"], CTX_MM)[CTX_MM // 2]


HTML = """<!doctype html><meta charset=utf-8><title>Visual Turing test</title>
<style>body{font-family:sans-serif;max-width:760px;margin:2em auto}img{width:384px;image-rendering:auto}
.c{border-bottom:1px solid #ccc;padding:1em 0}</style>
<h1>Real or synthetic?</h1><p>Each image is a 96 mm axial lung-window crop centred on one nodule. Mark each as real or
synthetic and give your confidence (1 = guess, 5 = certain). Do not look up cases. When finished, download the answers.</p>
<div id=cases></div><button onclick=done()>Download answers.json</button>
<script>const CASES=%CASES%;
const root=document.getElementById('cases');
CASES.forEach((c,k)=>{root.insertAdjacentHTML('beforeend',`<div class=c><b>Case ${k+1}/${CASES.length}</b><br><img src="${c.img}"><br>
<label><input type=radio name=call${k} value=real> real</label> <label><input type=radio name=call${k} value=synthetic> synthetic</label>
&nbsp; confidence <select id=conf${k}>${[1,2,3,4,5].map(v=>`<option>${v}</option>`).join('')}</select></div>`)});
function done(){const ans=CASES.map((c,k)=>{const r=document.querySelector(`input[name=call${k}]:checked`);
return {id:c.id,call:r?r.value:null,confidence:+document.getElementById('conf'+k).value}});
if(ans.some(a=>a.call===null)){alert('Please answer every case.');return}
const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({answers:ans},null,1)],{type:'application/json'}));
a.download='answers.json';a.click()}</script>"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--lidc-ref", required=True)
    ap.add_argument("--n", type=int, default=40, help="total cases (half real, half synthetic)")
    a = ap.parse_args(argv)
    c = manifest.load(a.manifest)
    meta = json.loads((Path(a.lidc_ref) / "lidc_ref.json").read_text())
    reals = [it for it in meta["items"] if it["kind"] == "nodule" and it["role"] == "real"]
    nh = len(c["obj"]["hybrids"])
    half = min(a.n // 2, nh, len(reals))
    rng = seedhash.rng(c["seed"], "H.turing")
    syn_idx = list(rng.permutation(nh)[:half])
    pool = list(reals)
    pairs = []
    for i in syn_idx:
        t = manifest.hybrid_type(c, i)
        d = manifest.load_hybrid(c, i)["d_eq_mm"]
        cand = sorted(pool, key=lambda r: (r["type"] != t, abs(r["d_eq_mm"] - d)))
        if not cand:
            break
        pairs.append((i, cand[0]))
        pool.remove(cand[0])
    import pylidc as pl
    lidc_ref.pylidc_shim()
    scans = {s.patient_id: s for s in pl.query(pl.Scan).all() if s.patient_id in {r["patient_id"] for _, r in pairs}}
    cases, key = [], []
    for i, r in pairs:
        cases.append({"truth": "synthetic", "img": png_uri(synthetic_slice(c, i))})
        cases.append({"truth": "real", "img": png_uri(real_slice(scans[r["patient_id"]], r))})
    order = rng.permutation(len(cases))
    shuffled = []
    for new_id, k in enumerate(order):
        key.append({"id": new_id, "truth": cases[k]["truth"]})
        shuffled.append({"id": new_id, "img": cases[k]["img"]})
    run = runrecord.start_run("H_analysis", "turing", seed_hex=c["seed"], tool="H_analysis.src.turing_kit")
    (run.path / "kit.html").write_text(HTML.replace("%CASES%", json.dumps(shuffled)))
    (run.path / "key.json").write_text(json.dumps(key, indent=1))
    run.finish(notes="visual Turing test kit; key.json stays beside the kit, do not show readers")
    print(f"{len(shuffled)} cases -> {run.path / 'kit.html'} (key.json beside it)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
