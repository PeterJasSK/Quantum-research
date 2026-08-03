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

# M1 source-advantage: bits the off-path attacker infers from the weak,
# state-recoverable `random.Random` source (epic §3.2/§6a). Shifts the prng
# cliff this many bits right of the csprng/qrng cliff -- default 6 puts the
# prng knee at nominal eff≈30 vs csprng≈24, a clear separation. 0 disables
# (prng would then overlap csprng/qrng). See draw/source_model.py.
PRNG_LEAK_BITS = int(os.environ.get("PRNG_LEAK_BITS", "6"))

# --- P5: effective-entropy sweep (OQ-2, declared now per AC-1.2) ---

# Axis floor is TXID_BITS (16): with PORT_BITS=16, eff = 16 + max(0, 16-k), so
# eff < 16 is unreachable -- those cells all collapse onto the fully-leaked-port
# 16-bit TXID space and were degenerate duplicates. Sweep 16 -> 32 (epic §3.2).
EFF_BITS_MIN = int(os.environ.get("EFF_BITS_MIN", "16"))
EFF_BITS_MAX = int(os.environ.get("EFF_BITS_MAX", "32"))
EFF_BITS_STEP = int(os.environ.get("EFF_BITS_STEP", "1"))
# Tight-CI default: 1.96*sqrt(0.25/n) half-width ~= ±0.025 at n=1500, so the
# csprng≈qrng overlap (epic §3.2 null result) is claimable. 400 is the floor.
TRIALS_PER_CELL = int(os.environ.get("TRIALS_PER_CELL", "2000"))

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

# Per-window flood cap (guesses fired into one live window). The analytic race
# is O(windows) regardless, so this is a *realism* bound, not a cost bound:
# leave it None to let g_live run up to the full space, or set it to model an
# attacker whose burst is bandwidth-limited. `None` sentinel via empty string.
_guess_budget_env = os.environ.get("ATTACK_GUESS_BUDGET", "")
ATTACK_GUESS_BUDGET = int(_guess_budget_env) if _guess_budget_env else None

# --- P4: resolver cache + metrics ---

CACHE_TTL_SECONDS = float(os.environ.get("CACHE_TTL_SECONDS", "300"))
RESULTS_CSV_PATH = os.environ.get("RESULTS_CSV_PATH", "results/metrics.csv")
RESULTS_RECORD_DIR = os.environ.get("RESULTS_RECORD_DIR", "results/records")

# --- P5: figures + replay export ---
FIGURES_DIR       = os.environ.get("FIGURES_DIR", "results/figures")
CLIFF_FIG_PATH    = os.path.join(FIGURES_DIR, "entropy_cliff")     # renderer appends .png/.svg
COLLAPSE_FIG_PATH = os.path.join(FIGURES_DIR, "sad_dns_collapse")
WEB_REPLAY_DIR    = os.environ.get("WEB_REPLAY_DIR", "web/public/replay")
PARALLEL_QUERIES_SWEEP = [int(v) for v in os.environ.get("PARALLEL_QUERIES_SWEEP", "1,2,4,8,16").split(",")]  # M3 birthday axis (OQ-P5.3)
# M3 must sit *mid-cliff*, not below the knee: at/under the knee (eff ≤ 24)
# a single window already poisons ~certainly (g_live ≥ S), so q adds nothing.
# eff=28 gives q=1 rate ≈ 0.26, where extra parallel windows visibly amplify.
BIRTHDAY_EFF_BITS      = int(os.environ.get("BIRTHDAY_EFF_BITS", "28"))  # representative cell for M3 (OQ-P5.3)

# Realistic off-path send-rate (a single RTT window at this rate only fires
# g_live = rate*RTT ≈ 2000 ≈ 2^11 guesses -- far too few to poison modern
# entropy in one shot). The attacker's real power is a *sustained Kaminsky
# campaign*: it keeps triggering fresh queries, each opening a new ~RTT window,
# so total guesses G = rate*RTT * (windows over the campaign). The knee sits
# where G ≈ S = 2^eff.
CLIFF_SEND_RATE_PPS = int(os.environ.get("CLIFF_SEND_RATE_PPS", "100000"))
CLIFF_KNEE_BITS = int(os.environ.get("CLIFF_KNEE_BITS", "24"))

# Kaminsky campaign length: how many times the attacker re-triggers each
# structural window (fresh query = fresh target, an independent Bernoulli).
# Total campaign windows W = ATTACK_ATTEMPTS * (MAX_RETRANSMITS+1) * q, and the
# cliff knee lands where W*g_live ≈ 2^CLIFF_KNEE_BITS. Default sizes N to put
# the knee at eff≈24 (~a few minutes of flooding at 100000 pps); eff≈32 would
# need hours. Folded analytically per window (O(1), not materialised).
_g_per_window = max(1, int(CLIFF_SEND_RATE_PPS * RTT_SECONDS))
ATTACK_ATTEMPTS = int(os.environ.get(
    "ATTACK_ATTEMPTS",
    str(max(1, round((1 << CLIFF_KNEE_BITS) / (_g_per_window * (MAX_RETRANSMITS + 1))))),
))
