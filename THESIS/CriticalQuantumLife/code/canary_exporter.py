#!/usr/bin/env python3
"""Critical Quantum Life — F7: the Prometheus/OpenMetrics exporter (AC-F7.2, AC-F7.6-data).

Serves the Canary probe's per-cycle health record as OpenMetrics text over a local HTTP
endpoint, using only the Python standard library (no new dependency). Slots straight into the
QRMI -> Prometheus -> Grafana stack quantum-cloud operators already run.

Run:
    cd THESIS/CriticalQuantumLife/code
    python canary_exporter.py --w 6 --port 9797 --cycles 200
    # then, elsewhere:
    curl -s localhost:9797/metrics
"""
from __future__ import annotations

import argparse
import functools
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import closed_loop as cl
from canary_probe import CanaryProbe

print = functools.partial(print, flush=True)

# metric name -> (type, help). Gauges only; the Canary is a level monitor, not a counter.
_METRICS: dict[str, tuple[str, str]] = {
    "qcanary_witness_margin": ("gauge", "Entanglement witness signal above the classical null band"),
    "qcanary_witness_signal": ("gauge", "Raw genealogical witness signal (joint-separable)"),
    "qcanary_null_band": ("gauge", "Classical measure-and-resend null band k/sqrt(shots)"),
    "qcanary_surprise": ("gauge", "Free-energy surprise proxy of the latest cycle"),
    "qcanary_sigma": ("gauge", "Branching set-point of the surprise-activity process"),
    "qcanary_adaptation_gap": ("gauge", "Rolling yoked-minus-closed surprise (adaptation signal)"),
    "qcanary_avalanche_rate": ("gauge", "Avalanches per cycle over the rolling window"),
    "qcanary_twoq_err": ("gauge", "Reported two-qubit gate error of the probed chain"),
    "qcanary_readout_err": ("gauge", "Reported readout error of the probed chain"),
    "qcanary_alert": ("gauge", "1 while a health alert is firing, else 0"),
}


class MetricsRegistry:
    """Thread-safe latest-value-per-gauge store."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[str, float] = {name: 0.0 for name in _METRICS}
        self._last_alert: dict[str, Any] | None = None

    def update(self, values: dict[str, float]) -> None:
        with self._lock:
            self._values.update(values)

    def set_alert(self, alert: dict[str, Any] | None) -> None:
        with self._lock:
            self._last_alert = alert
            self._values["qcanary_alert"] = 1.0 if alert else 0.0

    def render(self) -> str:
        with self._lock:
            lines: list[str] = []
            for name, (mtype, help_text) in _METRICS.items():
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} {mtype}")
                lines.append(f"{name} {self._values.get(name, 0.0)}")
            return "\n".join(lines) + "\n"


def record_to_registry(record: dict[str, Any], registry: MetricsRegistry) -> None:
    """Map one probe health record onto the registry gauges (AC-F7.2)."""
    registry.update({
        "qcanary_witness_margin": float(record["witness_margin"]),
        "qcanary_witness_signal": float(record["witness_signal"]),
        "qcanary_null_band": float(record["null_band"]),
        "qcanary_surprise": float(record["surprise"]),
        "qcanary_sigma": float(record["sigma"]) if record["sigma"] is not None else 0.0,
        "qcanary_adaptation_gap": float(record["adaptation_gap"]),
        "qcanary_avalanche_rate": float(record["avalanche_rate"]),
        "qcanary_twoq_err": float(record["twoq_err"]),
        "qcanary_readout_err": float(record["readout_err"]),
    })
    registry.set_alert(record["alert"])


def _make_handler(registry: MetricsRegistry) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            if self.path.rstrip("/") not in ("", "/metrics"):
                self.send_response(404)
                self.end_headers()
                return
            body = registry.render().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: Any) -> None:  # silence per-request logging
            return

    return Handler


def serve(registry: MetricsRegistry, port: int) -> HTTPServer:
    """Start the /metrics HTTP server in a daemon thread; return the server handle."""
    httpd = HTTPServer(("0.0.0.0", port), _make_handler(registry))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"[canary] exporter serving OpenMetrics on http://0.0.0.0:{port}/metrics")
    return httpd


def _writer(session: str) -> Any:
    """Append each record to research_runs/canary_<session>.json (AC-F7.1 artifact)."""
    os.makedirs(cl.OUTPUT_DIR, exist_ok=True)
    path = os.path.join(cl.OUTPUT_DIR, f"canary_{session}.json")
    cycles: list[dict[str, Any]] = []

    def write(record: dict[str, Any]) -> None:
        cycles.append(record)
        with open(path, "w") as f:
            json.dump({"session": session, "cycles": cycles}, f, indent=2, default=str)

    return write, path


def main() -> None:
    ap = argparse.ArgumentParser(description="CQL F7 — Quantum Canary OpenMetrics exporter")
    ap.add_argument("--w", "--width", dest="width", type=int, default=6)
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--port", type=int, default=9797)
    ap.add_argument("--cycles", type=int, default=None, help="default: run forever")
    ap.add_argument("--session", type=str, default="live")
    args = ap.parse_args()

    registry = MetricsRegistry()
    serve(registry, args.port)
    write, path = _writer(args.session)
    print(f"[canary] w={args.width} shots={args.shots} -> {path}")

    def on_record(record: dict[str, Any]) -> None:
        record_to_registry(record, registry)
        write(record)
        flag = f"  ALERT:{record['alert']['id']}" if record["alert"] else ""
        print(f"[canary] cycle {record['cycle']:4d}  margin {record['witness_margin']:+.3f}  "
              f"surprise {record['surprise']:.2f}  sigma "
              f"{record['sigma'] if record['sigma'] is not None else float('nan'):.2f}{flag}")

    probe = CanaryProbe(width=args.width, shots=args.shots, seed=args.seed)
    probe.run(args.cycles, on_record)


if __name__ == "__main__":
    main()
