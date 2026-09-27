#!/usr/bin/env python3
"""PJ2.2b renderer -- banked 1D-line run JSON -> the FILLED line mockup + an isolated-vs-coupled PNG.

The 1D sibling of ``analysis/pj_lattice_render.py``. Reads a banked ``research_runs/pj2_line/*.json``
(the depth-scan schema from ``1D_alive.py``) and emits a SELF-CONTAINED filled port of the line
mockup (CSP-safe: all CSS/JS inline, no external fetch, ``file://``-safe):

  * ``research/pj2_vivarium/line_movement.html`` -- a port of ``mockups/line_scenarios.html``,
    real ``fields/w/overlap`` per generation; if the run is solo-only (``--movement-only``) the
    replicate/duo mode buttons are dropped (no data for them).

The port is programmatic + faithful: the mockup's client-side synthetic-data block (the
``const L/GENS/Wd`` + ``walk1d``/``genSolo/genRep/genDuo`` + ``const DATA={...}``) is replaced by a
single injected ``const L=..,GENS=..,Wd=..;`` + ``const DATA=<real scenarios>;`` (the ``clamp`` helper
the renderer still needs is re-declared). Everything downstream -- the chain rendering + witness
plot -- is kept verbatim; it reads the injected real fields.

Usage:
    cd artificial-life
    python analysis/line_render.py --run-glob 'research_runs/pj2_line/*sim*.json'
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

_HEAD = ('<!doctype html>\n<meta charset="utf-8">\n'
         '<meta name="viewport" content="width=device-width,initial-scale=1">\n')

# The exact mode-button markup in mockups/line_scenarios.html (dropped when a run lacks that mode).
_MODE_BTN = {
    "replicate": '    <button data-mode="replicate" aria-pressed="false">Replicate<b>one → two</b></button>\n',
    "duo": '    <button data-mode="duo" aria-pressed="false">Two organisms<b>interact</b></button>\n',
}


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
# Data mapping: the banked scenarios already match the mockup's fields contract.
# ---------------------------------------------------------------------------
def _line_scenarios(run: dict[str, Any]) -> dict[str, Any]:
    """DATA[mode][arm] = [{fields:[occ[L],..], w, overlap, n} per gen] -- the line mockup contract."""
    sc = run["scenarios"]
    out: dict[str, Any] = {}
    for mode, arms in sc.items():
        out[mode] = {}
        for arm, frames in arms.items():
            out[mode][arm] = [{"fields": f["fields"], "w": f["w"],
                               "overlap": f.get("overlap", 0.0), "n": f.get("n", 1)}
                              for f in frames]
    return out


def build_data(run: dict[str, Any]) -> dict[str, Any]:
    """Provenance + shape summary for the log line (the scenarios pass straight through)."""
    meta = run["meta"]
    return {"length": int(meta["length"]), "gens": int(meta["gens"]), "width": int(meta["width"]),
            "backend": meta.get("backend"), "sim": bool(meta.get("sim", True)),
            "certified_frames": bool(meta.get("certified_frames", True)),
            "modes": list(run["scenarios"].keys())}


# ---------------------------------------------------------------------------
# Fill the mockup (swap the synthetic-data block for the injected real DATA).
# ---------------------------------------------------------------------------
def render_line(run: dict[str, Any], out_dir: str) -> str:
    length = int(run["meta"]["length"])
    gens = int(run["meta"]["gens"])
    width = int(run["meta"]["width"])
    data = _line_scenarios(run)
    pokes = run["meta"].get("pokes")
    if pokes is None:                                              # back-compat: old single-poke runs
        single = run["meta"].get("poke")
        pokes = [single] if single else []
    preamble = (
        f"const L={length},GENS={gens},Wd={width};\n"
        "const POKES=" + json.dumps(pokes, separators=(",", ":")) + ";\n"
        "const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));\n"
        "const DATA=" + json.dumps(data, separators=(",", ":")) + ";")
    html = _read_mockup("line_scenarios.html")
    html = _swap(html, "const L=9,GENS=6,Wd=3;", 'coupled:genDuo("coupled")}};', preamble)
    # drop mode buttons with no data in this run (e.g. --movement-only -> solo only).
    for mode, btn in _MODE_BTN.items():
        if mode not in data:
            html = html.replace(btn, "")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "line_movement.html")
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
        for arm, col in (("isolated", "#37e6d4"), ("coupled", "#ff5c6b")):
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
    length = run["meta"].get("length")
    fig.suptitle(f"PJ2.2b 1D-line (L={length}) -- isolated vs coupled germ witness "
                 f"({'sim' if run['meta'].get('sim') else run['meta'].get('backend')})")
    fig.tight_layout()
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "pj2_line_witness.png")
    fig.savefig(out)
    plt.close(fig)
    print(f"[OK] wrote {out}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the PJ2.2b 1D-line mockup + witness PNG.")
    ap.add_argument("--run-glob", dest="run_glob", default="research_runs/pj2_line/*sim*.json",
                    help="glob for the banked 1D-line run JSON(s); latest is used")
    ap.add_argument("--out-dir", dest="out_dir", default=_DEFAULT_OUT)
    args = ap.parse_args()

    path = _latest(args.run_glob)
    if path is None:
        print(f"[FAIL] no run matched {args.run_glob!r} (run 1D_alive.py first)")
        return 1

    with open(path) as f:
        run = json.load(f)

    out = render_line(run, args.out_dir)
    d = build_data(run)
    print(f"[OK] wrote {out}  (L={d['length']} gens={d['gens']} modes={d['modes']} "
          f"backend={d['backend']})")
    render_witness_png(run, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
