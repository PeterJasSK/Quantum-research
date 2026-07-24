"""Append-only rotation event log (epic s4 artefact, AC-3): one JSON object
per rotation, so P5 can replay the salt timeline."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from .sources import SaltKind


def append_event(
    path: Path | str,
    *,
    timestamp: str,
    old_salt: bytes,
    new_salt: bytes,
    interval: float,
    kind: SaltKind,
) -> None:
    """Append one rotation event line: `{timestamp, old_salt, new_salt,
    interval, kind}` (old/new salt as hex)."""
    event = {
        "timestamp": timestamp,
        "old_salt": old_salt.hex(),
        "new_salt": new_salt.hex(),
        "interval": interval,
        "kind": kind,
    }
    with open(path, "a") as f:
        f.write(json.dumps(event) + "\n")


def read_events(path: Path | str) -> Iterator[dict]:
    """Read rotation events back in order, for a P5 replay of the salt timeline."""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)
