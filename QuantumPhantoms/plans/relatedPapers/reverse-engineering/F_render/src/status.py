"""Update one target in F_render/status.json (lifecycle state + reproduced record), validated before writing."""
from __future__ import annotations

import json
from datetime import date

from F_render.src.io import F_DIR
from shared.validate import schema_errors

STATUS = F_DIR / "status.json"
ORDER = ["listed", "dissected", "reproduced", "adapted", "integrated"]


def set_reproduced(number: int, state: str, reproduced: dict | None, figures: list[str] | None = None) -> None:
    """Set target `number` to `state` (never moves backwards) and record its reproduction."""
    doc = json.loads(STATUS.read_text())
    t = next(t for t in doc["targets"] if t["number"] == number)
    if t["state"] in ORDER and state in ORDER and ORDER.index(state) < ORDER.index(t["state"]):
        state = t["state"]
    t["state"] = state
    if reproduced is not None:
        t["reproduced"] = reproduced
    t["claim_level"] = "n/a"
    t["sim_mode"] = "n/a"
    for f in figures or []:
        if f not in t["figures"]:
            t["figures"].append(f)
    t["updated"] = date.today().isoformat()
    errs = schema_errors(doc, "target_status")
    if errs:
        raise ValueError("status.json would violate target_status:\n  " + "\n  ".join(errs))
    STATUS.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
