#!/usr/bin/env python3
"""
build_web.py — Quantum Galton Board: the P5 zero-runtime replay splicer (OQ-5.1).

Splices the current ``web/replay.json`` into the ``<script type="application/json"
id="replay">`` block of ``web/quantum_galton.html`` so the shipped single file
carries its data inline and opens from ``file://`` with no server, no build tool,
and no ``fetch`` at view time (OQ-6). This is a codegen step, not a view-time
build: re-run it after any P4 re-export (the noisy fill, or the Phase-B hw
matrix) to refresh the one file — no P5 code change is needed, the null arm
slots simply become populated (plan §1 Tier B).

stdlib only (``json`` + ``re``); imports nothing physics-facing. The replay JSON
is P4-frozen and read-only here (``web/replay.json`` is never rewritten).
"""

from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.normpath(os.path.join(_HERE, "..", "web"))
HTML_PATH = os.path.join(WEB_DIR, "quantum_galton.html")
REPLAY_PATH = os.path.join(WEB_DIR, "replay.json")

# the exact embed target authored in quantum_galton.html (OQ-5.1); the inner
# text is replaced wholesale, so a re-run is idempotent and the diff is confined
# to this one block.
_BLOCK = re.compile(
    r'(<script type="application/json" id="replay">)(.*?)(</script>)',
    re.DOTALL)


def splice(html: str, replay_json: str) -> str:
    """Return ``html`` with the ``id="replay"`` block's body set to ``replay_json``."""
    if not _BLOCK.search(html):
        raise ValueError('no <script type="application/json" id="replay"> block found '
                          "in quantum_galton.html — cannot splice the replay")
    # a plain function replacement avoids re backreference interpretation of the
    # JSON payload (\1, \g<...> etc. inside the data would otherwise be expanded).
    return _BLOCK.sub(lambda m: m.group(1) + replay_json + m.group(3), html, count=1)


def main() -> int:
    if not os.path.exists(REPLAY_PATH):
        print(f"no {REPLAY_PATH}; run replay_export.py first", file=sys.stderr)
        return 1
    if not os.path.exists(HTML_PATH):
        print(f"no {HTML_PATH}", file=sys.stderr)
        return 1

    with open(REPLAY_PATH) as f:
        replay = json.load(f)                       # validate it parses
    # compact, and guaranteed free of the "</script>" sentinel (JSON escapes '/'
    # is optional, but no key/value here contains that literal); keys stay as
    # written by P4 (stringified ints).
    replay_json = json.dumps(replay, separators=(",", ":"))

    with open(HTML_PATH) as f:
        html = f.read()
    spliced = splice(html, replay_json)
    with open(HTML_PATH, "w") as f:
        f.write(spliced)

    filled = [a for a in replay.get("arms", [])
              if replay.get("per_arm", {}).get(a) is not None]
    print(f"spliced {REPLAY_PATH} -> {HTML_PATH}")
    print(f"  arms={replay.get('arms')} filled={filled} depths={replay.get('depths')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
