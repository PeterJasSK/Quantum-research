"""Per-source attacker-advantage model (epic §3.2/§6a, M1 source ordering).

Pure, stateless, dependency-free (mirrors `sad_dns.py`) so P5's sweep and P6's
JS mirror can both import the *same* collapse logic without pulling in
`sources.py`'s QRNG/HTTP dependency.

The defender configures a *nominal* effective entropy (`effective_bits`, the
cliff x-axis). What the off-path attacker actually has to brute-force can be
smaller when the source is weak -- that gap is the whole M1 story:

  * ``fixed``  -- source port is pinned to a publicly-known constant
    (pre-2008 deployment, epic §6a). The attacker fixes those bits to their
    known values and never searches them, so only the TXID is unknown:
    ``search_bits = txid_bits`` regardless of the nominal axis. Its poison
    curve is a flat ceiling -- always poisonable.
  * ``prng``   -- `random.Random` (Mersenne Twister) is state-recoverable and
    typically low-entropy-seeded, so an attacker who observes a few draws
    infers a fixed discount of ``prng_leak_bits`` off the search: its cliff
    sits `prng_leak_bits` to the right of the CSPRNG cliff (harder-looking
    nominal entropy, same real difficulty as a smaller space).
  * ``csprng`` / ``qrng`` -- full-entropy, non-recoverable. The attacker gets
    no discount: ``search_bits = nominal effective_bits``. These two overlap
    exactly (epic §3.2 null result); QRNG's differentiator is the signed
    provenance receipt (M5), not a lower rate.
"""
from __future__ import annotations

from testbed.draw.sad_dns import effective_bits


def attacker_search_bits(
    kind: str,
    *,
    txid_bits: int,
    port_bits: int,
    k: int,
    prng_leak_bits: int,
) -> int:
    """Bits the *attacker* must actually brute-force for one window, given the
    draw source. Always ``<= effective_bits(txid_bits, port_bits, k)`` (the
    defender's nominal entropy); the poison probability is ``g_live /
    2**search_bits``, so a smaller value means an easier attack."""
    nominal = effective_bits(txid_bits, port_bits, k)
    if kind == "fixed":
        # Known port -> only the TXID is unknown (never above the nominal cap).
        return min(txid_bits, nominal)
    if kind == "prng":
        # Recoverable weak RNG -> fixed search discount, floored at 0 bits.
        return max(0, nominal - prng_leak_bits)
    # csprng / qrng: full-entropy, no attacker advantage.
    return nominal
