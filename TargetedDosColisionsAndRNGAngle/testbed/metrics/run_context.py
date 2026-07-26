"""Run context / tags the controller can't derive on its own (plan-4
Design). `knowledge_level`/`attack_mode` are set by whoever launches the
run -- P5's matrix, or a manual operator -- via env vars; the controller has
no way to infer them (it only knows `salt_kind`/`ROTATION_INTERVAL_SECONDS`).
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

from testbed.config import METRICS_CSV_PATH


@dataclass(frozen=True)
class RunContext:
    knowledge_level: str
    attack_mode: str
    csv_path: str
    start_time: float

    @classmethod
    def from_env(cls) -> "RunContext":
        return cls(
            knowledge_level=os.environ.get("KNOWLEDGE_LEVEL", "na"),
            attack_mode=os.environ.get("ATTACK_MODE", "na"),
            csv_path=os.environ.get("METRICS_CSV_PATH", METRICS_CSV_PATH),
            start_time=time.time(),
        )
