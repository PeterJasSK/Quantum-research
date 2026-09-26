#!/usr/bin/env python3
"""PJ2.2 renderer -- banked 2D-lattice run JSON -> the FILLED mockups + an isolated-vs-coupled PNG.

Reads a banked ``research_runs/pj2_lattice/*.json`` (the depth-scan schema from
``pj_lattice_vivarium.py``, already the mockup data contract) and emits SELF-CONTAINED filled ports
of the design mockups (CSP-safe: all CSS/JS inline, no external fetch, ``file://``-safe):

  * ``research/pj2_vivarium/lattice_3x3_snap.html``     -- a port of ``mockups/vivarium_3x3_snap.html``
    (all three modes x both arms), real ``fields/w/overlap`` per generation.
  * ``research/pj2_vivarium/lattice_4x4_movement.html`` -- a port of ``mockups/vivarium_4x4_scenarios.html``
    (solo movement only, Phase B).

The port is programmatic + faithful: each mockup's client-side data-GENERATION block (the ``const
G/N/GENS`` + ``BIAS``/``walk``/``genSolo/genRep/genDuo`` + ``const DATA={...}``) is replaced by a
single injected ``const GRID=.. ; const DATA=<real scenarios>;`` (the ``clamp``/``rc``/``Z`` helpers the
renderer still needs are re-declared). Everything downstream -- the snap/cloud/nucleus rendering
(argmax + ``easeBack`` trail, centroid glide) -- is kept verbatim; it reads the injected real fields.

Mirrors ``analysis/pj_vivarium_render.py`` (``_latest``, ``build_data``, ``render_html``,
``render_witness_png``, ``main() -> int``, degrade-gracefully).

Usage:
    cd artificial-life
    python analysis/pj_lattice_render.py --run-glob 'research_runs/pj2_lattice/*sim*.json'
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from typing import Any

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_MOCKUPS = os.path.join(_ROOT, "research", "pj2_vivarium", "mockups")
_DEFAULT_OUT = os.path.join(_ROOT, "research", "pj2_vivarium")

_MODES = ("solo", "replicate", "duo")
_ARMS = ("isolated", "coupled")

_HEAD = ('<!doctype html>\n<meta charset="utf-8">\n'
         '<meta name="viewport" content="width=device-width,initial-scale=1">\n')


def _latest(run_glob: str) -> str | None:
    matches = glob.glob(run_glob if os.path.isabs(run_glob) else os.path.join(_ROOT, run_glob))
    return max(matches, key=os.path.getmtime) if matches else None


def _read_mockup(name: str) -> str:
    with open(os.path.join(_MOCKUPS, name)) as f:
        return f.read()


def _swap(text: str, start_anchor: str, end_anchor: str, replacement: str) -> str:
    """Replace the region [start_anchor .. end_anchor] (inclusive) with `replacement` (once)."""
    i = text.index(start_anchor)
    j = text.index(end_anchor, i) + len(end_anchor)
    return text[:i] + replacement + text[j:]


# ---------------------------------------------------------------------------
# Data mapping: the banked scenarios already match the mockup contract.
# ---------------------------------------------------------------------------
def _snap_scenarios(run: dict[str, Any]) -> dict[str, Any]:
    """DATA[mode][arm] = [{fields:[occ[C],..], w, overlap, n} per gen] -- the snap/3x3 contract."""
    sc = run["scenarios"]
    out: dict[str, Any] = {}
    for mode, arms in sc.items():
        out[mode] = {}
        for arm, frames in arms.items():
            out[mode][arm] = [{"fields": f["fields"], "w": f["w"],
                               "overlap": f.get("overlap", 0.0), "n": f.get("n", 1)}
                              for f in frames]
    return out


def _solo_scenarios_4x4(run: dict[str, Any]) -> dict[str, Any]:
    """DATA.solo[arm] = [{occ:[16], w, mass} per gen] -- the 4x4 single-field contract (Phase B)."""
    sc = run["scenarios"]["solo"]
    out: dict[str, Any] = {"solo": {}}
    for arm, frames in sc.items():
        seq = []
        for f in frames:
            occ = f["fields"][0]
            seq.append({"occ": occ, "w": f["w"], "mass": round(sum(occ), 4)})
        out["solo"][arm] = seq
    return out


def build_data(run: dict[str, Any]) -> dict[str, Any]:
    """Provenance + shape summary for the caption (the scenarios pass straight through)."""
    meta = run["meta"]
    return {"grid": int(meta["grid"]), "gens": int(meta["gens"]), "width": int(meta["width"]),
            "backend": meta.get("backend"), "sim": bool(meta.get("sim", True)),
            "certified_frames": bool(meta.get("certified_frames", True)),
            "modes": list(run["scenarios"].keys())}


# ---------------------------------------------------------------------------
# Fill the mockups (swap the generation block for the injected real DATA).
# ---------------------------------------------------------------------------
def render_snap(run: dict[str, Any], out_dir: str) -> str:
    grid = int(run["meta"]["grid"])
    gens = int(run["meta"]["gens"])
    data = _snap_scenarios(run)
    preamble = (
        f"const GRID={grid},G=GRID,N=G*G,GENS={gens};\n"
        "const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));\n"
        "const rc=i=>[Math.floor(i/G),i%G];\n"
        "const Z=()=>Array(N).fill(0);\n"
        "const DATA=" + json.dumps(data, separators=(",", ":")) + ";")
    html = _read_mockup("vivarium_3x3_snap.html")
    html = _swap(html, "const G=3,N=9,GENS=6;", 'coupled:genDuo("coupled")}};', preamble)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "lattice_3x3_snap.html")
    with open(out, "w") as f:
        f.write(_HEAD + html)
    return out


def render_smooth(run: dict[str, Any], out_dir: str) -> str:
    """Same data contract as the snap port, but fills the smooth mockup (body glides, no snap)."""
    grid = int(run["meta"]["grid"])
    gens = int(run["meta"]["gens"])
    data = _snap_scenarios(run)
    preamble = (
        f"const GRID={grid},G=GRID,N=G*G,GENS={gens};\n"
        "const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));\n"
        "const rc=i=>[Math.floor(i/G),i%G];\n"
        "const Z=()=>Array(N).fill(0);\n"
        "const DATA=" + json.dumps(data, separators=(",", ":")) + ";")
    html = _read_mockup("vivarium_3x3_smooth.html")
    html = _swap(html, "const G=3,N=9,GENS=6;", 'coupled:genDuo("coupled")}};', preamble)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "lattice_3x3_smooth.html")
    with open(out, "w") as f:
        f.write(_HEAD + html)
    return out


def render_4x4(run: dict[str, Any], out_dir: str) -> str:
    grid = int(run["meta"]["grid"])
    gens = int(run["meta"]["gens"])
    data = _solo_scenarios_4x4(run)
    preamble = (
        f"const GRID={grid},G=GRID,N=G*G,GENS={gens},Wd=3;\n"
        "const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));\n"
        "const rc=i=>[Math.floor(i/G),i%G];\n"
        "const DATA=" + json.dumps(data, separators=(",", ":")) + ";")
    html = _read_mockup("vivarium_4x4_scenarios.html")
    html = _swap(html, "const G=4,N=16,GENS=6,Wd=3;", 'coupled:genDuo("coupled")}};', preamble)
    # solo movement only -- drop the replicate/duo mode buttons (no data for them).
    html = html.replace(
        '    <button data-mode="replicate" aria-pressed="false">Replicate<b>one → two</b></button>\n'
        '    <button data-mode="duo" aria-pressed="false">Two organisms<b>interact</b></button>\n', "")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "lattice_4x4_movement.html")
    with open(out, "w") as f:
        f.write(_HEAD + html)
    return out


# ---------------------------------------------------------------------------
# Static witness figure: isolated vs coupled witness-vs-gen per mode.
# ---------------------------------------------------------------------------
def render_witness_png(run: dict[str, Any], out_dir: str) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:                                   # noqa: BLE001
        print(f"[WARN] matplotlib unavailable, skipping PNG: {exc}")
        return False
    sc = run["scenarios"]
    modes = list(sc.keys())
    fig, axes = plt.subplots(1, len(modes), figsize=(4.6 * len(modes), 4.0), dpi=150, squeeze=False)
    for ax, mode in zip(axes[0], modes):
        for arm, col in (("isolated", "#5cf0cf"), ("coupled", "#ff5d6c")):
            if arm not in sc[mode]:
                continue
            frames = sc[mode][arm]
            xs = [f["gen"] for f in frames]
            ws = [f["w"] for f in frames]
            ax.plot(xs, ws, "-o", ms=4, color=col, label=arm)
        ax.axhline(0.15, ls="--", lw=0.8, color="#888", label="certified >0.15")
        ax.set_ylim(-0.1, 1.05)
        ax.set_xlabel("generation (depth scan)")
        ax.set_title(mode)
        ax.grid(alpha=0.15)
    axes[0][0].set_ylabel(r"germ witness  $\langle X^{\otimes W}\rangle$")
    axes[0][0].legend(fontsize=8, framealpha=0.3)
    grid = run["meta"].get("grid")
    fig.suptitle(f"PJ2.2 2D-lattice ({grid}x{grid}) -- isolated vs coupled germ witness "
                 f"({'sim' if run['meta'].get('sim') else run['meta'].get('backend')})")
    fig.tight_layout()
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "pj2_lattice_witness.png")
    fig.savefig(out)
    plt.close(fig)
    print(f"[OK] wrote {out}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the PJ2.2 2D-lattice mockups + witness PNG.")
    ap.add_argument("--run-glob", dest="run_glob", default="research_runs/pj2_lattice/*sim*.json",
                    help="glob for the banked run JSON(s); 3x3 -> snap, 4x4 -> movement")
    ap.add_argument("--out-dir", dest="out_dir", default=_DEFAULT_OUT)
    ap.add_argument("--smooth", action="store_true",
                    help="render the smooth mockup (body glides, no snap) for 3x3 runs")
    args = ap.parse_args()

    matches = glob.glob(args.run_glob if os.path.isabs(args.run_glob)
                        else os.path.join(_ROOT, args.run_glob))
    if not matches:
        print(f"[FAIL] no run matched {args.run_glob!r} (run pj_lattice_vivarium.py first)")
        return 1

    # Latest 3x3 run -> snap; latest 4x4 run -> movement (solo).
    by_grid: dict[int, str] = {}
    for path in sorted(matches, key=os.path.getmtime):
        with open(path) as f:
            run = json.load(f)
        by_grid[int(run["meta"]["grid"])] = path

    wrote_any = False
    if 3 in by_grid:
        with open(by_grid[3]) as f:
            run = json.load(f)
        out = render_smooth(run, args.out_dir) if args.smooth else render_snap(run, args.out_dir)
        d = build_data(run)
        print(f"[OK] wrote {out}  (grid={d['grid']} gens={d['gens']} modes={d['modes']} "
              f"backend={d['backend']})")
        render_witness_png(run, args.out_dir)
        wrote_any = True
    if 4 in by_grid:
        with open(by_grid[4]) as f:
            run = json.load(f)
        out = render_4x4(run, args.out_dir)
        print(f"[OK] wrote {out}  (4x4 solo movement, Phase B)")
        wrote_any = True

    if not wrote_any:
        print("[FAIL] runs matched but none were grid 3 or 4")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
