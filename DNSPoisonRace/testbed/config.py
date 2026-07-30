"""Testbed constants -- the single environment source-of-truth (epic §4).

Every value below is read from the environment with a documented default, so
no module ever hardcodes a knob P2-P5 will want to sweep. Grouped by the plan
that introduces the block; later plans only *consume* these, they don't add
their own ad-hoc env reads.
"""
from __future__ import annotations

import os

# --- P1: race-engine placeholder (AC-1.1) ---

TXID_BITS = 16
PORT_BITS = int(os.environ.get("PORT_BITS", "16"))  # OQ-1: OS ephemeral range is ~11-16 bits

# P1's draw is a static hardcoded placeholder (epic §3.3's "static salt" analogue).
# P2 replaces this with draw_source(kind) -- P1 imports nothing from P2.
STATIC_DRAW_TXID = 4242
STATIC_DRAW_PORT = 33333

RTT_SECONDS = float(os.environ.get("RTT_SECONDS", "0.02"))
RETRANSMIT_SECONDS = float(os.environ.get("RETRANSMIT_SECONDS", "0.5"))
PARALLEL_QUERIES = int(os.environ.get("PARALLEL_QUERIES", "1"))

# --- P1: Q-EaaS connection (epic Appendix A.3/A.4) ---
# Key from env only, never committed/printed/logged. P2 is the first consumer;
# declared here so config.py stays the one place all env-overridable knobs live.

QEAAS_BASE_URL = os.environ.get("QEAAS_BASE_URL", "https://api.qeaas.eu")
QEAAS_API_KEY = os.environ.get("QEAAS_API_KEY", "")

PRNG_SEED = int(os.environ.get("PRNG_SEED", "0"))

# --- P5: effective-entropy sweep (OQ-2, declared now per AC-1.2) ---

EFF_BITS_MIN = int(os.environ.get("EFF_BITS_MIN", "8"))
EFF_BITS_MAX = int(os.environ.get("EFF_BITS_MAX", "32"))
EFF_BITS_STEP = int(os.environ.get("EFF_BITS_STEP", "1"))
TRIALS_PER_CELL = int(os.environ.get("TRIALS_PER_CELL", "10000"))

# --- P4/P5: attacker send-rate axis (OQ-3) ---

SEND_RATE_PPS = [
    int(v) for v in os.environ.get("SEND_RATE_PPS", "100,1000,10000,100000").split(",")
]

# --- P2/P5: SAD-DNS port-leak knob (OQ-4) ---

SAD_DNS_LEAK_BITS = int(os.environ.get("SAD_DNS_LEAK_BITS", "0"))

# --- P2: draw sources ---

FIXED_PORT = int(os.environ.get("FIXED_PORT", "33333"))

# --- P3: off-path attacker ---

ATTACKER_SEND_RATE_PPS = int(os.environ.get("ATTACKER_SEND_RATE_PPS", "10000"))
RTT_JITTER_FRAC = float(os.environ.get("RTT_JITTER_FRAC", "0.1"))
MAX_RETRANSMITS = int(os.environ.get("MAX_RETRANSMITS", "3"))

# --- P4: resolver cache + metrics ---

CACHE_TTL_SECONDS = float(os.environ.get("CACHE_TTL_SECONDS", "300"))
RESULTS_CSV_PATH = os.environ.get("RESULTS_CSV_PATH", "results/metrics.csv")
RESULTS_RECORD_DIR = os.environ.get("RESULTS_RECORD_DIR", "results/records")
