"""Section W: web page. Bake the run into ONE self-contained HTML file (web/<run name>.html).

Reads tiles.json + tiles/*.png, base64-embeds every PNG, adds the rulebook reference and the quantum claims, and
injects them into template.html. No backend, no external requests. It renders what the files carry and never
recomputes anything quantum.
"""
from __future__ import annotations

import base64
import io
import json
import math
import os

from PIL import Image

from common import WEB_DIR, runio
from common.runio import Ctx

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html")


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
    im = Image.open(path)
    if max(im.size) > max_dim:
        scale = max_dim / max(im.size)
        im = im.resize((int(im.size[0] * scale), int(im.size[1] * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def run(ctx: Ctx) -> None:
    d = ctx.run_dir
    data = runio.load_json(d / "tiles.json")
    full_images: dict[str, str] = {}
    for t in data["tiles"]:
        t["png"] = _png_data_uri(os.path.join(d, t["png_path"]))
        full_rel = t.get("full_png_path", "")
        if full_rel and full_rel not in full_images:               # each distinct full slice is embedded once
            full_images[full_rel] = _png_data_uri_resized(os.path.join(d, full_rel), max_dim=512)
        for g in t.get("growth", []):
            g["png"] = _png_data_uri(os.path.join(d, g["png_path"]))
    rb = runio.load_json(d / "rulebook.json")
    labels = list(rb["size"])
    ds = runio.load_json(d / "dscale" / "dscale_run.json") or {}
    ds["claims"] = [c | {"family": f"{c.get('stage', '?')} · {c.get('family', '?')}"}
                    for c in runio.load_json(d / "claims.json") or []]
    cohort = {"tiles": data["tiles"], "quantum_run": data["quantum_run"], "honest_label": data.get("honest_label", ""),
              "ct_attribution": data.get("ct_attribution", ""), "full_images": full_images,
              "provenance": data.get("provenance"), "dscale": ds,
              "rulebook": {"size_labels": labels, "size_probs": [rb["size"][k] for k in labels],
                           "size_mm": [rb["size_mm"][k] for k in labels], "types": rb["types"]}}
    with open(TEMPLATE) as f:
        html = f.read().replace("__COHORT_DATA__", json.dumps(_sanitize(cohort), allow_nan=False))
    out = WEB_DIR / f"{d.name}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"  built {out} ({out.stat().st_size / 1024:.0f} KB, self-contained)")
