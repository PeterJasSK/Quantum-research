"""Process lifecycle for one experiment cell (plan-5 Design "1. Experiment
orchestrator"): boot the controller + Mininet with the cell's env, wait for
the leaf/spine datapaths to register, launch the attacker on the `attacker`
host, run for `RUN_DURATION_SECONDS`, tear down cleanly. stdlib
`subprocess`/`signal` + the Mininet API only -- no OpenFlow imports here.
Idempotent teardown so a crashed cell never poisons the next. Needs
root/Mininet, like P1/P3/P4's live steps.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mininet.net import Mininet  # noqa: E402
from mininet.node import OVSSwitch, RemoteController  # noqa: E402

from testbed.config import (  # noqa: E402
    CONTROLLER_LISTEN_ADDR,
    CONTROLLER_LISTEN_PORT,
    RUN_DURATION_SECONDS,
)
from testbed.experiments.matrix import ExperimentCell  # noqa: E402
from testbed.experiments.salt_handoff import current_salt_hex  # noqa: E402
from testbed.topology.ecmp_topo import ECMPTopo  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTROLLER_LAUNCHER = _REPO_ROOT / "testbed" / "controller" / "run_controller.py"
_DATAPATH_WAIT_TIMEOUT_SECONDS = 15.0
_DATAPATH_POLL_INTERVAL_SECONDS = 0.5
_CONTROLLER_TERM_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class CellResult:
    cell: ExperimentCell
    run_record: dict | None  # attacker JSON run-record, None for exp4d cells
    summary: dict | None  # parsed *.summary.csv row, None if never written
    passed: bool | None  # None = no PASS/FAIL classification for this cell
    reason: str


def _rotation_log_path(cell: ExperimentCell) -> str:
    return os.path.join(os.path.dirname(cell.csv_path), f"{cell.cell_id}.rotation_events.jsonl")


def _cell_env(cell: ExperimentCell) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "SALT_KIND": cell.salt_kind,
            "ROTATION_INTERVAL_SECONDS": str(cell.rotation_interval),
            "PRNG_SEED": str(cell.prng_seed),
            "DEFENCES_ENABLED": "1" if cell.defences_enabled else "0",
            "KNOWLEDGE_LEVEL": cell.knowledge_level,
            "ATTACK_MODE": cell.attack_mode or "na",
            "METRICS_CSV_PATH": cell.csv_path,
            "TARGET_LINK": str(cell.target_link),
            "ROTATION_LOG_PATH": _rotation_log_path(cell),
        }
    )
    return env


def _wait_for_datapaths(timeout: float = _DATAPATH_WAIT_TIMEOUT_SECONDS) -> bool:
    """Poll `ovs-ofctl show` for both switches until the controller has
    connected and installed the table-miss flow, or `timeout` elapses."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        leaf = subprocess.run(
            ["ovs-ofctl", "-O", "OpenFlow15", "show", "s1"], capture_output=True
        )
        spine = subprocess.run(
            ["ovs-ofctl", "-O", "OpenFlow15", "show", "s2"], capture_output=True
        )
        if leaf.returncode == 0 and spine.returncode == 0:
            return True
        time.sleep(_DATAPATH_POLL_INTERVAL_SECONDS)
    return False


def _run_attacker(cell: ExperimentCell, env: dict[str, str], net: Mininet) -> dict | None:
    if cell.attack_mode is None:
        return None  # exp4d clean-background cell -- no attacker launch

    args = [
        sys.executable,
        str(_REPO_ROOT / "testbed" / "attacker" / "run_attack.py"),
        "--level", cell.attacker_level,
        "--mode", cell.attack_mode,
        "--target-link", str(cell.target_link),
        "--count", str(cell.attacker_count),
    ]
    if cell.needs_salt:
        args += ["--salt", current_salt_hex(env["ROTATION_LOG_PATH"])]
    if cell.needs_oracle:
        args += ["--oracle-salt", current_salt_hex(env["ROTATION_LOG_PATH"])]

    attacker = net.get("attacker")
    output = attacker.cmd(" ".join(args))
    brace = output.rfind("{")
    if brace == -1:
        raise RuntimeError(f"attacker produced no run-record for {cell.cell_id}:\n{output}")
    return json.loads(output[brace:])


def _read_summary(cell: ExperimentCell) -> dict | None:
    summary_path = Path(cell.csv_path).with_suffix(".summary.csv")
    if not summary_path.exists():
        return None
    with summary_path.open() as f:
        rows = list(csv.DictReader(f))
    return rows[-1] if rows else None


def _classify(cell: ExperimentCell, summary: dict | None) -> tuple[bool | None, str]:
    if cell.expected_saturated is None:
        return None, "no PASS/FAIL classification for this cell (data-only)"
    if summary is None:
        return False, "no summary row written -- metrics collector never polled"
    saturated = summary["saturated"] in ("True", "true", "1")
    if saturated == cell.expected_saturated:
        return True, f"saturated={saturated} matches expected={cell.expected_saturated}"
    return False, f"saturated={saturated} does NOT match expected={cell.expected_saturated}"


def run_cell(cell: ExperimentCell) -> CellResult:
    """Run one cell end to end: env -> controller + Mininet -> attacker ->
    bounded wait -> teardown -> classify against the cell's expectation."""
    Path(cell.csv_path).parent.mkdir(parents=True, exist_ok=True)
    env = _cell_env(cell)

    subprocess.run(["mn", "-c"], capture_output=True)  # idempotent pre-cell cleanup

    controller_proc = subprocess.Popen([sys.executable, str(_CONTROLLER_LAUNCHER)], env=env)
    net = Mininet(
        topo=ECMPTopo(),
        switch=OVSSwitch,
        controller=RemoteController("c0", ip=CONTROLLER_LISTEN_ADDR, port=CONTROLLER_LISTEN_PORT),
        autoSetMacs=False,
    )
    run_record: dict | None = None
    summary: dict | None = None
    reason = ""
    try:
        net.start()
        if not _wait_for_datapaths():
            reason = "leaf/spine datapaths never registered"
            return CellResult(cell=cell, run_record=None, summary=None, passed=False, reason=reason)

        run_record = _run_attacker(cell, env, net)

        # host.cmd() above already blocked for the send duration; sleep out
        # the rest of the run so the metrics collector's poll loop catches up.
        time.sleep(RUN_DURATION_SECONDS)

        summary = _read_summary(cell)
    finally:
        net.stop()
        controller_proc.terminate()
        try:
            controller_proc.wait(timeout=_CONTROLLER_TERM_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            controller_proc.kill()
            controller_proc.wait()
        subprocess.run(["mn", "-c"], capture_output=True)  # idempotent post-cell cleanup

    passed, classify_reason = _classify(cell, summary)
    return CellResult(cell=cell, run_record=run_record, summary=summary, passed=passed, reason=classify_reason)


__all__ = ["CellResult", "run_cell"]
