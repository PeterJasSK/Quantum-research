"""F3 entrypoint — bake one F2 run into a single self-contained web page (the MVP).

Usage:
    python QuantumPhantoms/code/build_web.py --run research_runs/<f2_run>
    python QuantumPhantoms/code/build_web.py --run <dir> --out ../web/index.html

Reads <run>/tiles.json + <run>/tiles/*.png, base64-embeds every PNG, embeds the cohort data
and the published rulebook reference, injects them into code/web_template.html, and writes a
single standalone index.html (no backend, no external requests). Sampler-blind — renders
whatever tiles.json carries; never recomputes anything quantum (epic §3).
"""

from __future__ import annotations

import argparse
import base64
import functools
import json
import math
import os

from common.datamodel import TYPES
from f1_quantum.rulebook import Rulebook

print = functools.partial(print, flush=True)

_HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(_HERE, "web_template.html")
DEFAULT_OUT = os.path.normpath(os.path.join(_HERE, "..", "..", "web", "index.html"))


def _parse_args():
    ap = argparse.ArgumentParser(description="F3 — build the self-contained cohort web page.")
    ap.add_argument("--run", required=True,
                    help="F2 run dir containing tiles.json + tiles/ (absolute or relative to "
                         "QuantumPhantoms/).")
    ap.add_argument("--out", default=DEFAULT_OUT, help="output HTML path (default ../web/index.html).")
    return ap.parse_args()


def _resolve_run(run_arg: str) -> str:
    if os.path.isdir(run_arg):
        return os.path.abspath(run_arg)
    cand = os.path.normpath(os.path.join(_HERE, "..", "..", run_arg))
    if os.path.isdir(cand):
        return cand
    raise FileNotFoundError(f"--run dir not found: {run_arg}")


def _sanitize(obj):
    """Replace NaN/Inf floats with None so the embedded blob is valid JSON for the browser."""
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def _png_data_uri(path: str) -> str:
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _png_data_uri_resized(path: str, max_dim: int) -> str:
    """Embed a PNG downscaled so its longest side is <= max_dim (F3.1 Q5, embed weight)."""
    import io

    from PIL import Image

    im = Image.open(path)
    if max(im.size) > max_dim:
        scale = max_dim / max(im.size)
        im = im.resize((int(im.size[0] * scale), int(im.size[1] * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _rulebook_block() -> dict:
    rb = Rulebook()
    return {
        "size_labels": rb.size_labels(),
        "size_probs": rb.size_probs(),
        "size_mm": rb.size_mm(),
        "types": list(TYPES),
    }


def main():
    args = _parse_args()
    run_dir = _resolve_run(args.run)

    tiles_json = os.path.join(run_dir, "tiles.json")
    if not os.path.isfile(tiles_json):
        raise FileNotFoundError(
            f"{run_dir} has no tiles.json — run F2 (build_tiles.py) on this run first."
        )
    with open(tiles_json) as f:
        data = json.load(f)  # json.load accepts NaN from F1's PRNG runs

    # embed each tile's zoom crop; embed each distinct full slice ONCE (F3.1, Q5).
    full_images: dict[str, str] = {}
    for t in data["tiles"]:
        png_abs = os.path.join(run_dir, t["png_path"])
        if not os.path.isfile(png_abs):
            raise FileNotFoundError(f"missing tile PNG: {png_abs}")
        t["png"] = _png_data_uri(png_abs)

        full_rel = t.get("full_png_path", "")
        if full_rel and full_rel not in full_images:
            full_abs = os.path.join(run_dir, full_rel)
            if not os.path.isfile(full_abs):
                raise FileNotFoundError(f"missing full-slice PNG: {full_abs}")
            full_images[full_rel] = _png_data_uri_resized(full_abs, max_dim=512)

    cohort = {
        "tiles": data["tiles"],
        "quantum_run": data["quantum_run"],
        "rulebook": _rulebook_block(),
        "honest_label": data.get("honest_label", ""),
        "ct_attribution": data.get("ct_attribution", ""),
        "full_images": full_images,
    }
    blob = json.dumps(_sanitize(cohort), allow_nan=False)

    with open(TEMPLATE) as f:
        html = f.read()
    if "__COHORT_DATA__" not in html:
        raise RuntimeError("template is missing the __COHORT_DATA__ placeholder")
    html = html.replace("__COHORT_DATA__", blob)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(html)

    kb = os.path.getsize(args.out) / 1024
    run = data["quantum_run"]
    print(f"  built {os.path.abspath(args.out)}  ({kb:.0f} KB, self-contained)")
    print(f"  {len(data['tiles'])} tiles · backend {run.get('backend_name')} · "
          f"CHSH {run.get('chsh_value')}")


if __name__ == "__main__":
    main()
