"""Victim throughput via `iperf3` (P4, AC-6). Out-of-band from the
controller -- needs host/netns exec (victim = server, `bg` host = client),
not the OpenFlow channel. `run_server`/`run_client` are launched by a
Mininet host.cmd or a manual operator; the controller only calls
`latest_mbps` to read the rolling output file. Degrades to `None` (empty CSV
column) if `iperf3` is unavailable or the file is missing/unparsable --
never a crash (plan-4 Risks).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def detect_iperf3() -> str | None:
    """`iperf3` supports `--json-stream` (one JSON object per line), which
    `latest_mbps` below relies on; plain `iperf` has no equivalent, so it is
    not supported here (Risks: iperf/iperf3 format skew)."""
    return "iperf3" if shutil.which("iperf3") else None


def run_server(output_path: str, *, port: int = 5201) -> subprocess.Popen:
    """Start an `iperf3` server on the victim host, streaming one JSON
    report per interval to `output_path`. Caller owns the process
    lifetime."""
    binary = detect_iperf3()
    if binary is None:
        raise RuntimeError("iperf3 not found on PATH")
    out = open(output_path, "w")
    return subprocess.Popen([binary, "-s", "-p", str(port), "--json-stream"], stdout=out)


def run_client(server_ip: str, duration_seconds: int, *, port: int = 5201) -> subprocess.Popen:
    """Start an `iperf3` client (the `bg` host) against `server_ip` for
    `duration_seconds`."""
    binary = detect_iperf3()
    if binary is None:
        raise RuntimeError("iperf3 not found on PATH")
    return subprocess.Popen([binary, "-c", server_ip, "-p", str(port), "-t", str(duration_seconds)])


def latest_mbps(output_path: str) -> float | None:
    """Read the server's `--json-stream` output and return the most recent
    interval's throughput in Mbps, or `None` if unavailable/unparsable."""
    path = Path(output_path)
    if not path.exists():
        return None
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return None

    last_mbps = None
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
            last_mbps = record["data"]["streams"][0]["bits_per_second"] / 1_000_000
        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            continue
        break
    return last_mbps
