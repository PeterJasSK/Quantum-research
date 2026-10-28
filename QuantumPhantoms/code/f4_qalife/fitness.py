"""F4 classical fitness + selection (plan §4, AC-3, Q6).

Explicitly classical, deterministic, and NON-learned — no training, no patient data
(epic §6, keeps the arm non-QML). This is the "classical host" half of Mode A: the
quantum device rolls division + fate; the host scores survival.

Fitness (plan Q6):
    score = 1.0 * [fate == proliferative]
          + 0.5 * [fate == quiescent]
          + size_preference(mid-band)
Selection keeps the top-k candidates; ties broken by decode order (lowest first) so
the loop is fully reproducible on a fixed seed/sim.

Death is narrated as environment-driven selection, NOT engineered decoherence
(parent plan §5.2.5 trap 1): losers are dropped by the host, not damped on the device.
"""

from __future__ import annotations

# 2-qubit fate codes: value 0,1,2 -> these fates; spare code 3 -> most common (proliferative).
FATES = ("proliferative", "quiescent", "necrotic")

# Mid-size preference target (mm): nodules near this band score highest.
_MID_MM = 10.0

_FATE_BONUS = {"proliferative": 1.0, "quiescent": 0.5, "necrotic": 0.0}


def decode_fate(f_msb: int, f_lsb: int) -> str:
    """Two fate bits (big-endian f_msb f_lsb) -> fate label; spare code 3 remapped."""
    v = ((f_msb & 1) << 1) | (f_lsb & 1)
    return FATES[v] if v < len(FATES) else FATES[0]


def size_preference(size_mm: float) -> float:
    """Smooth 0..1 preference peaking at the mid size band."""
    return 1.0 / (1.0 + abs(size_mm - _MID_MM) / _MID_MM)


def score(size_mm: float, fate: str) -> float:
    """Classical fitness of one candidate cell (plan Q6)."""
    return _FATE_BONUS.get(fate, 0.0) + size_preference(size_mm)


def select(candidates: list[dict], k: int) -> list[dict]:
    """Keep the top-k candidates by score; tie-break by `order` (decode index).

    `candidates` are dicts carrying at least `score` and `order`. Returns a new list
    of length min(k, len(candidates)).
    """
    ordered = sorted(candidates, key=lambda c: (-c["score"], c["order"]))
    return ordered[: max(0, k)]
