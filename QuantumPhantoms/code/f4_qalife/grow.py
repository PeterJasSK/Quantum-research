"""F4 grow — render a lineage's clonal growth as a baked timeline page (longitudinal arm).

Usage (run from QuantumPhantoms/code/, `python -m`):
    python -m f4_qalife.grow --backend aer --generations 4 --ct-source synthetic

Picks the single cleanest parenchymal spot in a lung-CT slice (lowest-variance patch that
fully fits a lung window), latches ONE tumour there, grows it generation by generation via the
QALife processes (progression.grow_lineage), composites every clone of each generation's mass
into the SAME spot, and bakes a self-contained timeline page: gen 0 → gen N frames side by side,
each annotated with the process (divide / mutate / fate), the clone count, the mass diameter,
and the within-generation witness W_g. CHSH header for provenance.

Outputs under QuantumPhantoms/research_runs/<run>/ :
    progression/gen_<g>.png     one crop per generation (the growing mass at a fixed spot)
    progression.json            frames metadata (cells, offsets, fate, witness, diameter)
and the page at QuantumPhantoms/web/progression.html (override with --out).

HARD RULE (plan header): the implementer never runs hardware. `--backend ibm`/`auto` is the
human-run path; no token is read or stored by this code.
"""

from __future__ import annotations

import argparse
import base64
import functools
import io
import json
import math
import os
import time

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_fill_holes, distance_transform_edt, label, uniform_filter

from f1_quantum.backend import get_backend
from f1_quantum.lineage import DEFAULT_THETA_MUT
from f1_quantum.rulebook import Rulebook
from imaging.ctsource import load_background
from imaging.insert import crop, insert_lesion, lung_field_mask, window_to_uint8
from imaging.lesion import build_lesion, central_slice
from f4_qalife.progression import coherent_core_qubits, grow_lineage

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_BASE = os.path.normpath(os.path.join(_HERE, "..", "..", "research_runs"))
DEFAULT_OUT = os.path.normpath(os.path.join(_HERE, "..", "..", "web", "index.html"))


def _parse_args():
    ap = argparse.ArgumentParser(description="F4 grow — clonal-growth timeline at one clean spot.")
    ap.add_argument("--backend", default="aer",
                    help="'aer'/'' = AerSimulator (default), 'auto' = least_busy, or 'ibm_heron' (HUMAN-RUN).")
    ap.add_argument("--generations", type=int, default=4, help="growth generations (frames).")
    ap.add_argument("--coherent-cells", type=int, default=2,
                    help="Mode-B coherent core size (founder + daughters kept entangled). 2 = one "
                         "coherent parent↔daughter genealogy (~20q, shallow). Deeper collapses on Heron.")
    ap.add_argument("--offspring", type=int, default=4, help="candidate daughters per division (>=1).")
    ap.add_argument("--max-cells", type=int, default=16, help="cap on total clones in the mass.")
    ap.add_argument("--theta-mut", type=float, default=DEFAULT_THETA_MUT, help="mutation angle (radians).")
    ap.add_argument("--phase", type=float, default=0.0, help="P2 fate phase dial (radians).")
    ap.add_argument("--witness-shots", type=int, default=4096, help="shots per witness/CHSH basis job.")
    ap.add_argument("--ct-source", default="synthetic",
                    help="'synthetic' (dev default), 'bundled', or a dir of LUNA16 .mhd/.npy/.png.")
    ap.add_argument("--spacing", type=float, default=0.7, help="mm/px for npy/png/synthetic.")
    ap.add_argument("--crop", type=int, default=160, help="timeline frame crop size (px).")
    ap.add_argument("--wl", type=float, default=-600.0, help="lung window level (HU).")
    ap.add_argument("--ww", type=float, default=1500.0, help="lung window width (HU).")
    ap.add_argument("--psf", type=float, default=0.7, help="scanner point-spread blur sigma (px).")
    ap.add_argument("--out", default=DEFAULT_OUT, help="output HTML path.")
    return ap.parse_args()


def pick_clean_spot(arr, is_hu, mask, win, margin) -> tuple[int, int]:
    """Cleanest parenchymal spot: deepest INTERIOR of a real lung with lowest local variance.

    Guards against two traps: (1) a uniform-but-bright soft-tissue patch (low variance, wrong
    tissue) and (2) outside-body air pockets that read as "deep dark interior". The lung is
    gated to dark regions INSIDE the filled body silhouette, then only the large connected
    components (the actual lungs) are kept — dropping air pockets below/around the body. A
    distance transform then finds open parenchyma far from any boundary (vessels, pleura,
    mediastinum), and among those the lowest-variance point wins. Returns (x, y).
    """
    a = arr.astype(np.float32)
    h, w = a.shape
    if mask is None:
        mask = (a < -400.0) if is_hu else (a < 70.0)

    # Lungs = dark parenchyma INSIDE the body (fill-holes of the soft-tissue silhouette).
    soft = (a > -300.0) if is_hu else (a > 90.0)
    body = binary_fill_holes(soft)
    lung = mask & body
    # Keep only large, non-border-hugging components (the real lungs); drop outside-body air
    # pockets (whose bounding box runs to an image edge) and small fissure slivers.
    lbl, n = label(lung)
    if n > 0:
        by, bx = 0.045 * h, 0.045 * w
        valid = {}
        for i in range(1, n + 1):
            ys, xs = np.where(lbl == i)
            if ys.min() < by or ys.max() > h - by or xs.min() < bx or xs.max() > w - bx:
                continue                       # touches/nears an edge -> outside-body air pocket
            valid[i] = len(ys)
        if valid:
            amax = max(valid.values())
            keep = np.zeros_like(lung)
            for i, ar in valid.items():
                if ar >= 0.4 * amax:
                    keep |= lbl == i
            lung = keep
    if not lung.any():
        lung = mask

    dist = distance_transform_edt(lung)           # px from the nearest lung boundary
    need = win / 2.0                              # half-window should fit inside the lung
    deep = dist >= max(need, 0.6 * float(dist.max()))
    if not deep.any():                            # small/odd lung — relax to the most interior
        deep = dist >= 0.5 * float(dist.max()) if dist.max() > 0 else lung

    mean = uniform_filter(a, 9)
    std = np.sqrt(np.clip(uniform_filter(a * a, 9) - mean * mean, 0.0, None))
    std_masked = np.where(deep, std, np.inf)
    yx = np.unravel_index(int(np.argmin(std_masked)), std.shape)
    return int(yx[1]), int(yx[0])


def render_frame(bg, cells, spot, args) -> np.ndarray:
    """Composite every clone of one generation's mass into the fixed spot; return uint8 crop."""
    shared = bg.array.astype(np.float32).copy()
    rng = np.random.default_rng(20261026)   # fixed so frames are directly comparable
    for pc in cells:
        seed = int(pc.word, 2) & 0x7FFFFFFF          # morphology seed = certified-quantum bits
        lesion = build_lesion(pc.cell, bg.spacing_mm, seed=seed)
        d2d, a2d = central_slice(lesion)
        x = int(round(spot[0] + pc.dx_mm / bg.spacing_mm))
        y = int(round(spot[1] + pc.dy_mm / bg.spacing_mm))
        shared = insert_lesion(shared, d2d, a2d, (x, y), is_hu=bg.is_hu, rng=rng, psf_sigma=args.psf)
    u8 = window_to_uint8(shared, is_hu=bg.is_hu, wl=args.wl, ww=args.ww)
    return crop(u8, spot, args.crop)


def _png_b64(u8: np.ndarray) -> str:
    buf = io.BytesIO()
    Image.fromarray(u8, mode="L").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _png_b64_img(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def render_overview(bg, cells, spot, args, max_w: int = 760) -> Image.Image:
    """Zoomed-OUT context: the whole lung slice with the final mass in situ, spot ringed."""
    shared = bg.array.astype(np.float32).copy()
    rng = np.random.default_rng(20261026)
    reach_mm = 0.0
    for pc in cells:
        seed = int(pc.word, 2) & 0x7FFFFFFF
        lesion = build_lesion(pc.cell, bg.spacing_mm, seed=seed)
        d2d, a2d = central_slice(lesion)
        x = int(round(spot[0] + pc.dx_mm / bg.spacing_mm))
        y = int(round(spot[1] + pc.dy_mm / bg.spacing_mm))
        shared = insert_lesion(shared, d2d, a2d, (x, y), is_hu=bg.is_hu, rng=rng, psf_sigma=args.psf)
        reach_mm = max(reach_mm, math.hypot(pc.dx_mm, pc.dy_mm) + pc.cell.size_mm / 2.0)

    u8 = window_to_uint8(shared, is_hu=bg.is_hu, wl=args.wl, ww=args.ww)
    img = Image.fromarray(u8, mode="L").convert("RGB")
    draw = ImageDraw.Draw(img)
    x, y = spot
    r = reach_mm / bg.spacing_mm + 12.0               # ring just outside the mass
    teal = (0, 180, 180)
    draw.ellipse([x - r, y - r, x + r, y + r], outline=teal, width=max(2, int(r * 0.07)))
    L = r * 1.7                                        # crosshair ticks pointing at the spot
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        draw.line([x + dx * r, y + dy * r, x + dx * L, y + dy * L], fill=teal, width=2)

    w, h = img.size
    if w > max_w:
        img = img.resize((max_w, int(h * max_w / w)))
    return img


def _frame_data(frames) -> list[dict]:
    """Per-frame payload for the slider (image + annotation), consumed by the page JS."""
    out = []
    for f in frames:
        r = f.record
        modeb = f.mode == "B"
        n = len(f.cells)
        out.append({
            "img": _png_b64(f._png),
            "gen": f.generation,
            "mode": f.mode,
            "modeLabel": "MODE B · coherent" if modeb else "MODE A · classical genealogy",
            "stat": f"{f.diameter_mm():.1f} mm · {n} clone" + ("s" if n != 1 else ""),
            "proc": f.process,
            "witLabel": "cross-generation W" if (modeb and f.generation >= 1) else "within-gen W",
            "w": f"{r.witness_value:.3f}",
            "wver": "entangled" if r.witness_value > 1.0 else "separable",
        })
    return out


_PAGE_JS = """
const img=document.getElementById('frame'), sl=document.getElementById('sl'),
      gl=document.getElementById('genlabel'), st=document.getElementById('stat'),
      pr=document.getElementById('proc'), wt=document.getElementById('wit'),
      btn=document.getElementById('play');
const thumbs=[...document.querySelectorAll('.thumb')];
function show(i){
  const f=F[i];
  img.src='data:image/png;base64,'+f.img;
  gl.innerHTML='GEN '+f.gen+' <span class="mode '+(f.mode==='B'?'mb':'ma')+'">'+f.modeLabel+'</span>';
  st.textContent=f.stat; pr.textContent=f.proc;
  wt.innerHTML=f.witLabel+' = <b>'+f.w+'</b> <span class="tag '+f.wver+'">'+f.wver+'</span>';
  sl.value=i; thumbs.forEach((t,j)=>t.classList.toggle('on',j===i));
}
sl.addEventListener('input',e=>show(+e.target.value));
thumbs.forEach((t,j)=>t.addEventListener('click',()=>show(j)));
let timer=null;
function stop(){clearInterval(timer);timer=null;btn.textContent='▶ Play growth';}
btn.addEventListener('click',()=>{
  if(timer){stop();return;}
  if(+sl.value>=F.length-1) show(0);
  btn.textContent='⏸ Pause';
  timer=setInterval(()=>{let n=+sl.value+1; if(n>=F.length){stop();return;} show(n);},950);
});
show(0);
"""


def build_page(frames, chsh, backend_name, spot, source, out_path, overview_b64):
    data = _frame_data(frames)
    frames_json = json.dumps(data)
    thumbs = "".join(
        f'<img class="thumb" data-i="{i}" src="data:image/png;base64,{d["img"]}" alt="gen {d["gen"]}">'
        for i, d in enumerate(data)
    )
    sim = backend_name == "AerSimulator"
    chsh_line = f'CHSH S = {chsh:.3f} &middot; {"simulator (noiseless)" if sim else "real hardware"}'
    head = f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quantum Phantoms — a tumour grown on a quantum computer</title>
<style>
 :root{{--bg:#f1f4f8;--card:#fff;--ink:#0f2744;--mut:#5b6b80;--line:#e0e6ee;
   --teal:#009999;--deep:#005f73;--green:#1a9e5f;--red:#c24545;--mono:ui-monospace,Menlo,Consolas,monospace}}
 *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);
   font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;-webkit-font-smoothing:antialiased}}
 .wrap{{max-width:1080px;margin:0 auto;padding:0 24px;width:100%}}
 a{{color:var(--deep)}}
 .logo{{width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,var(--teal),var(--deep));
   display:inline-flex;align-items:center;justify-content:center;color:#fff;font-size:15px}}
 /* hero */
 .hero{{background:radial-gradient(1200px 320px at 50% -30px,rgba(0,153,153,.12),transparent);
   padding:56px 0 30px;text-align:center}}
 .kicker{{display:inline-flex;align-items:center;gap:9px;font-weight:700;font-size:15px;
   letter-spacing:-.2px;margin-bottom:18px}}
 .eyebrow{{font-family:var(--mono);font-size:11.5px;letter-spacing:2px;color:var(--teal);
   font-weight:700;margin-bottom:14px}}
 .hero h1{{margin:0 0 14px;font-size:35px;line-height:1.12;letter-spacing:-.8px}}
 .hero .sub{{color:var(--mut);font-size:15.5px;line-height:1.6;max-width:720px;margin:0 auto}}
 .prov{{margin-top:20px;display:flex;gap:8px;flex-wrap:wrap;justify-content:center}}
 .chip{{font-family:var(--mono);font-size:12px;background:#fff;border:1px solid var(--line);
   border-radius:20px;padding:5px 13px;color:var(--deep)}}
 .chip .dot{{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--green);
   box-shadow:0 0 6px var(--green);margin-right:6px;vertical-align:middle}}
 /* cards */
 main{{padding:14px 0 34px}}
 .card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:26px;
   margin:20px 0;box-shadow:0 1px 3px rgba(16,39,68,.05)}}
 .card h2{{margin:0 0 4px;font-size:19px;letter-spacing:-.3px}}
 .card .lead{{color:var(--mut);font-size:13.5px;margin:0 0 20px;line-height:1.5}}
 /* slider hero */
 .hero-top{{display:flex;gap:26px;flex-wrap:wrap;align-items:flex-start}}
 .stage{{flex:0 0 auto;width:430px;max-width:100%;background:#000;border:1px solid var(--line);
   border-radius:12px;overflow:hidden;box-shadow:0 2px 14px rgba(16,39,68,.10)}}
 .stage img{{display:block;width:100%;height:auto;image-rendering:auto}}
 .panel{{flex:1 1 260px;min-width:240px}}
 .panel .gen{{font-family:var(--mono);font-size:12px;letter-spacing:1px;color:var(--teal);
   font-weight:600;margin-bottom:12px}}
 .panel .big{{font-size:26px;font-weight:700;margin-bottom:12px;letter-spacing:-.4px}}
 .panel .proc{{color:var(--mut);font-size:13.5px;line-height:1.55;margin-bottom:16px;min-height:66px}}
 .panel .wit{{font-family:var(--mono);font-size:13px;color:var(--deep);background:#f3f7f8;
   border:1px solid var(--line);border-radius:9px;padding:9px 12px;display:inline-block}}
 .controls{{margin-top:22px}}
 .play{{background:var(--teal);color:#fff;border:none;border-radius:9px;padding:9px 17px;
   font-size:13px;font-weight:600;cursor:pointer}} .play:hover{{background:var(--deep)}}
 #sl{{width:100%;margin:16px 0 12px;accent-color:var(--teal)}}
 .thumbs{{display:flex;gap:9px;overflow-x:auto;padding-bottom:4px}}
 .thumb{{width:62px;height:62px;object-fit:cover;border-radius:8px;border:2px solid transparent;
   cursor:pointer;background:#000;opacity:.55;transition:.15s}}
 .thumb.on{{border-color:var(--teal);opacity:1}} .thumb:hover{{opacity:1}}
 .mode{{display:inline-block;font-size:9.5px;padding:2px 8px;border-radius:9px;letter-spacing:.3px;
   font-weight:700;margin-left:6px;vertical-align:middle}}
 .mode.mb{{background:rgba(0,95,115,.14);color:var(--deep)}}
 .mode.ma{{background:rgba(91,107,128,.14);color:var(--mut)}}
 .tag{{font-size:10px;padding:1px 7px;border-radius:9px;margin-left:5px}}
 .tag.entangled{{background:rgba(26,158,95,.14);color:var(--green)}}
 .tag.separable{{background:rgba(194,69,69,.12);color:var(--red)}}
 /* overview */
 .overview-wrap{{display:block;max-width:560px;margin:0 auto;background:#000;border:1px solid var(--line);
   border-radius:12px;overflow:hidden}}
 .overview-wrap img{{display:block;max-width:100%;height:auto}}
 .cap{{color:var(--mut);font-size:12.5px;margin:12px auto 0;max-width:620px;line-height:1.45;text-align:center}}
 /* how it works */
 .how{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}
 @media(max-width:760px){{.how{{grid-template-columns:1fr}} .hero h1{{font-size:28px}}}}
 .step{{border:1px solid var(--line);border-radius:14px;padding:20px;background:#fbfdfe}}
 .step .n{{width:30px;height:30px;border-radius:8px;background:var(--teal);color:#fff;font-weight:700;
   display:inline-flex;align-items:center;justify-content:center;font-size:14px;margin-bottom:12px}}
 .step h3{{margin:0 0 6px;font-size:14.5px}} .step p{{margin:0;color:var(--mut);font-size:13px;line-height:1.5}}
 .step .mb-pill{{font-size:10px;font-weight:700;color:var(--deep);background:rgba(0,95,115,.12);
   border-radius:8px;padding:1px 7px;margin-left:6px}}
 /* footer */
 footer{{border-top:1px solid var(--line);background:#fff;margin-top:14px}}
 .foot{{padding:28px 0 52px;color:var(--mut);font-size:12.5px;line-height:1.6}}
 .foot b{{color:var(--ink)}}
 .foot-brand{{display:flex;align-items:center;gap:10px;font-weight:700;color:var(--ink);
   font-size:15px;margin-bottom:12px}}
 .foot-names{{margin-top:14px;font-size:12px;color:var(--mut)}}
</style></head><body>
<header class="hero"><div class="wrap">
  <div class="kicker"><span class="logo">◈</span> Quantum Phantoms</div>
  <div class="eyebrow">LIVING-PROCESS ARM · MODE A + MODE B</div>
  <h1>A tumour grown on a quantum computer</h1>
  <p class="sub">A single lesion is latched to the cleanest spot in a real lung-CT slice, then
  grown — generation by generation — by biological processes rolled on quantum hardware. The
  image is a classical rendering; the <i>life story</i> is quantum.</p>
  <div class="prov">
    <span class="chip"><span class="dot"></span>{chsh_line}</span>
    <span class="chip">backend {backend_name}</span>
    <span class="chip">spot x={spot[0]} · y={spot[1]}</span>
    <span class="chip">CT: {source}</span>
  </div>
</div></header>

<main class="wrap">
  <section class="card">
    <h2>Watch it grow</h2>
    <p class="lead">Drag the slider or press play to step through the generations. Each frame is
    baked from the real quantum trace — division, mutation, fate — with its entanglement witness.</p>
    <div class="hero-top">
      <div class="stage"><img id="frame" alt="tumour growth"></div>
      <div class="panel">
        <div class="gen" id="genlabel"></div>
        <div class="big" id="stat"></div>
        <div class="proc" id="proc"></div>
        <div class="wit" id="wit"></div>
      </div>
    </div>
    <div class="controls">
      <button id="play" class="play">▶ Play growth</button>
      <input type="range" id="sl" min="0" max="{len(data) - 1}" value="0" step="1">
      <div class="thumbs">{thumbs}</div>
    </div>
  </section>

  <section class="card">
    <h2>Where it lives</h2>
    <p class="lead">The grown tumour in the full lung slice. The ring marks the single clean
    parenchymal spot it was latched to — the slider above zooms into that ring.</p>
    <div class="overview-wrap"><img src="data:image/png;base64,{overview_b64}" alt="whole lung slice — where the tumour lives"></div>
  </section>

  <section class="card">
    <h2>How it works</h2>
    <p class="lead">Three steps. Only the processes with no honest classical substitute run on the device.</p>
    <div class="how">
      <div class="step"><div class="n">1</div><h3>Latch &amp; seed</h3>
        <p>The cleanest lung-parenchyma spot is found automatically; a founder genotype is rolled
        from published nodule statistics as a quantum state on the device.</p></div>
      <div class="step"><div class="n">2</div><h3>Coherent core <span class="mb-pill">MODE B</span></h3>
        <p>Founder and its first daughter are kept <b>entangled across the generation boundary</b> —
        one joint state, never measured between. A cross-generation witness W&gt;1 certifies it; no
        classical genealogy reproduces this. <b>This earns the name.</b></p></div>
      <div class="step"><div class="n">3</div><h3>Deep growth <span class="mb-pill">MODE A</span></h3>
        <p>Each later generation every clone divides, mutates and commits a fate; the host keeps the
        fittest and adds it to the mass. Constant depth — it survives the coherence wall.</p></div>
    </div>
  </section>
</main>

<footer><div class="wrap foot">
  <div class="foot-brand"><span class="logo">◈</span> Quantum Phantoms</div>
  <b>Honest label.</b> Tumour <b>parameters + growth trajectory</b> are quantum; the CT <b>image</b>
  is a classical procedural rendering (no training, no patient data). The Mode-B cross-generation
  witness W = ⟨XX⟩+⟨ZZ⟩ (separable bound 1) &gt; 1 proves the lineage correlation is genuinely
  quantum. Mode A between generations is classical genealogy (measure-restart). Mode B is kept
  shallow on purpose — deep coherent genealogy collapses to Mode A on today's Heron, and <i>where</i>
  it collapses is the thesis's measured number. CHSH is job-level provenance.
  <div class="foot-names">Quantum Synthetic Cultures (management) · Quantum Phantoms (thesis) — a
  Siemens-8 living-process study.</div>
</div></footer>
"""
    html = head + "<script>\nconst F=" + frames_json + ";\n" + _PAGE_JS + "\n</script>\n</body></html>"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write(html)
    return out_path


def _write_run(run_dir, frames, chsh, backend_name, spot, source):
    os.makedirs(os.path.join(run_dir, "progression"), exist_ok=True)
    for f in frames:
        Image.fromarray(f._png, mode="L").save(os.path.join(run_dir, "progression", f"gen_{f.generation}.png"))
    meta = {
        "backend": backend_name, "chsh_value": chsh, "spot_xy": list(spot), "ct_source": source,
        "frames": [
            {
                "generation": fr.generation, "clones": len(fr.cells),
                "diameter_mm": round(fr.diameter_mm(), 2), "process": fr.process,
                "witness": fr.record.to_dict(),
                "cells": [
                    {**pc.cell.to_dict(), "fate": pc.fate,
                     "dx_mm": round(pc.dx_mm, 2), "dy_mm": round(pc.dy_mm, 2), "born_gen": pc.born_gen}
                    for pc in fr.cells
                ],
            }
            for fr in frames
        ],
    }
    with open(os.path.join(run_dir, "progression.json"), "w") as f:
        json.dump(meta, f, indent=2, default=str)


def main():
    args = _parse_args()
    if args.backend not in ("", "aer", "sim"):
        print("=" * 68)
        print("  HUMAN-RUN HARDWARE PATH — submitting real quantum jobs (Peter only).")
        print("  Uses a pre-existing saved IBM account; no token is read by this code.")
        print("=" * 68)

    rulebook = Rulebook()
    min_qubits = max(2 * 9 + 2, coherent_core_qubits(args.coherent_cells))
    backend = get_backend(args.backend, min_qubits=min_qubits)

    frames, raw_bits, chsh = grow_lineage(
        rulebook, generations=args.generations, offspring=args.offspring,
        theta_mut=args.theta_mut, phase=args.phase, witness_shots=args.witness_shots,
        max_cells=args.max_cells, coherent_cells=args.coherent_cells, backend=backend,
    )

    bg = load_background(args.ct_source, args.spacing)
    mask = lung_field_mask(bg.array, bg.is_hu)
    spot = pick_clean_spot(bg.array, bg.is_hu, mask, win=args.crop, margin=args.crop // 2)

    for f in frames:
        f._png = render_frame(bg, f.cells, spot, args)   # attach rendered crop
    overview = render_overview(bg, frames[-1].cells, spot, args)

    backend_name = "AerSimulator" if backend is None else backend.name
    run_dir = os.path.join(OUTPUT_BASE, f"grow_{'aer' if backend is None else backend.name}_{time.strftime('%Y%m%d-%H%M%S')}")
    _write_run(run_dir, frames, chsh, backend_name, spot, bg.source)
    overview.save(os.path.join(run_dir, "overview.png"))
    out = build_page(frames, chsh, backend_name, spot, bg.source, args.out, _png_b64_img(overview))

    print(f"\n  grew {len(frames)} generations at spot (x={spot[0]}, y={spot[1]}) on {bg.source}")
    for f in frames:
        wk = "cross-gen" if (f.mode == "B" and f.generation >= 1) else "within-gen"
        print(f"    gen {f.generation} [Mode {f.mode}]: {len(f.cells):>2} clones  "
              f"diam {f.diameter_mm():>5.1f} mm   {wk} W={f.record.witness_value:.3f}")
    print(f"  CHSH S = {chsh:.3f} ({backend_name})")
    print("  honest label: Mode B coherent core (entangled genealogy, earns 'quantum') + "
          "Mode A deep growth (classical genealogy).")
    print(f"\n  wrote frames + metadata -> {run_dir}")
    print(f"  built timeline page     -> {out}")


if __name__ == "__main__":
    main()
