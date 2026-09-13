#!/usr/bin/env python3
"""PJ1 renderer -- banked arena run JSON -> the locked wave-bars web demo + the 3-arm witness PNG.

Reads a banked ``research_runs/pj1/*.json`` (the arm/frame schema from ``pj1_run_arena.py``),
extracts the per-arm frames, maps each to the wave-bars render contract
(``{a,b,s,ov,w}`` per frame), and writes a SELF-CONTAINED ``research/pj1_arena/index.html`` by
injecting the real measured frames into the picked visual
(``pj1Concepts/4_wave-bars_PICKED.html``) -- the demo contract (AC-PJ1.7). Also emits the static
3-arm witness figure ``research/pj1_arena/pj1_witness_3arm.png`` (the science figure).

The port is faithful by construction: the picked HTML is a self-contained page (inline CSS/JS, no
external fetch -- CSP-safe) whose only data is one ``const DATA = {...};`` literal; the renderer
swaps that literal for the real frames and leaves the visual byte-identical otherwise.

Mirrors ``analysis/plot_baseline.py``: path shim, ``main() -> int``, degrade-gracefully if
matplotlib is absent.

Usage:
    cd artificial-life
    python analysis/pj1_render.py --run-glob 'research_runs/pj1/*sim*.json'
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
from typing import Any

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TEMPLATE = os.path.join(_ROOT, "plans/pj1Concepts", "4_wave-bars_PICKED.html")
_DEFAULT_OUT = os.path.join(_ROOT, "research", "pj1_arena")

_ARMS = ("none", "soma_soma", "germ_routed")


def _latest(run_glob: str) -> str | None:
    matches = glob.glob(run_glob if os.path.isabs(run_glob) else os.path.join(_ROOT, run_glob))
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)


def build_data(run: dict[str, Any]) -> dict[str, Any]:
    """Map the banked arena run to the wave-bars render contract:
        DATA = {"L": track, "frames": N, "arms": {arm: [{a,b,s,ov,w}, ...]}}
    where per frame  a/b = the two organisms' occupancy (len L),  s = contact entropy (bits),
    ov = occupancy overlap (contact),  w = the joint genealogy witness <X^{2W}>."""
    meta = run["meta"]
    track = int(meta["track"])
    arms_out: dict[str, list[dict[str, Any]]] = {}
    for arm, frames in run["arms"].items():
        seq: list[dict[str, Any]] = []
        for f in frames:
            a, b = f["occ"][0], f["occ"][1]
            s = f.get("contact_entropy_sim") or 0.0
            ov = sum(x * y for x, y in zip(a, b))
            seq.append({
                "a": [round(float(x), 4) for x in a],
                "b": [round(float(x), 4) for x in b],
                "s": round(float(s), 4),
                "ov": round(float(ov), 4),
                "w": round(float(f["witness_joint"]), 4),
            })
        arms_out[arm] = seq
    # inject ONLY the arms actually in the run (single-arm runs render single-arm; render_html
    # strips the buttons for any arm not present).
    n_frames = len(next(iter(arms_out.values())))
    return {"L": track, "frames": n_frames, "arms": arms_out}


def render_html(data: dict[str, Any], out_dir: str) -> str:
    """Inject `data` into the picked wave-bars template; write a self-contained index.html."""
    with open(_TEMPLATE) as f:
        template = f.read()
    present = set(data["arms"])
    literal = "const DATA = " + json.dumps(data, separators=(",", ":")) + ";"
    lines = template.splitlines()
    swapped = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("const DATA ="):
            indent = line[:len(line) - len(line.lstrip())]
            lines[i] = indent + literal
            swapped = True
        m = re.search(r'data-arm="(\w+)"', line)      # drop buttons for arms not in this run
        if m and m.group(1) not in present:
            lines[i] = ""
    if not swapped:
        raise RuntimeError("could not find the `const DATA =` literal in the template")
    html = "\n".join(lines)
    if "soma_soma" not in present:                    # keep the default-selected arm valid
        html = html.replace("setArm('soma_soma')", f"setArm('{next(iter(present))}')")
    # standalone + CSP-safe: prepend a doctype/charset/viewport (the template is otherwise inline).
    head = ('<!doctype html>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n')
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "index.html")
    with open(out, "w") as f:
        f.write(head + html + "\n")
    return out


def render_witness_png(run: dict[str, Any], out_dir: str) -> bool:
    """The 3-arm witness figure: joint witness + separable null vs frame per arm (Agg).
    Returns False (degrades) if matplotlib is unavailable."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:                                   # noqa: BLE001
        print(f"[WARN] matplotlib unavailable, skipping PNG: {exc}")
        return False

    colors = {"none": "#8b96ab", "soma_soma": "#49dd8b", "germ_routed": "#ff5d78"}
    fig, ax = plt.subplots(figsize=(8.5, 4.2), dpi=150)
    for arm, frames in run["arms"].items():
        t = [f["t"] for f in frames]
        w = [f["witness_joint"] for f in frames]
        ax.plot(t, w, "-o", ms=3, color=colors.get(arm, "#888"), label=f"{arm} · joint witness")
    # separable joint null (should sit ~0) from the soma_soma arm as reference.
    ref = run["arms"].get("soma_soma") or next(iter(run["arms"].values()))
    ax.plot([f["t"] for f in ref], [f["separable_joint_null"] for f in ref],
            "--", color="#59637a", lw=1, label="separable joint null")
    ax.axhline(0.0, color="#2a3446", lw=0.8)
    ax.set_xlabel("frame (animation clock)")
    ax.set_ylabel(r"joint genealogy witness  $\langle X^{\otimes 2W}\rangle$")
    W = run["meta"].get("width")
    ax.set_title(f"PJ1 arena -- 3-arm joint witness across the collision (W={W}/organism)")
    ax.legend(fontsize=8, framealpha=0.3)
    ax.grid(alpha=0.15)
    fig.tight_layout()
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "pj1_witness_3arm.png")
    fig.savefig(out)
    plt.close(fig)
    print(f"[OK] wrote {out}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the PJ1 wave-bars demo + 3-arm witness PNG "
                                             "from a banked arena run.")
    ap.add_argument("--run-glob", dest="run_glob", default="research_runs/pj1/*sim*.json",
                    help="glob for the banked run JSON (latest by mtime is used)")
    ap.add_argument("--out-dir", dest="out_dir", default=_DEFAULT_OUT,
                    help="output directory for index.html + the PNG")
    args = ap.parse_args()

    run_path = _latest(args.run_glob)
    if run_path is None:
        print(f"[FAIL] no run matched {args.run_glob!r} (run pj1_run_arena.py first)")
        return 1
    print(f"[..] rendering from {run_path}")
    with open(run_path) as f:
        run = json.load(f)

    if not os.path.exists(_TEMPLATE):
        print(f"[FAIL] picked template not found: {_TEMPLATE}")
        return 1

    data = build_data(run)
    html = render_html(data, args.out_dir)
    print(f"[OK] wrote {html}  (L={data['L']} frames={data['frames']} "
          f"arms={list(data['arms'])})")
    render_witness_png(run, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
