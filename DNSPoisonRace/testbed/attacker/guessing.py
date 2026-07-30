"""Off-path guess model (epic ss5, OQ-P3.1/OQ-P3.2). Imports P2's
`effective_bits` -- never re-derives the entropy-reduction math (epic ss3.5).
Guesses and targets both live at the *effective-index* level: an integer in
`[0, 2**effective_bits)` encoding exactly the `(TXID, port)` bits the attacker
still has to search, with the SAD-DNS-leaked `k` port bits pinned to the
draw's true values."""
from __future__ import annotations

from dataclasses import dataclass, field

from testbed.draw.sad_dns import effective_bits
from testbed.types import Draw

from .portable_prng import bounded


def effective_index(draw: Draw, port_bits: int, k: int) -> int:
    """Map a true `Draw` to its target index: full TXID entropy plus the
    unleaked low port bits (the leaked high `k` bits are pinned by
    construction -- they never enter the searched index)."""
    leaked_bits = min(k, port_bits)
    searched_port_bits = port_bits - leaked_bits
    searched_port = draw.port & ((1 << searched_port_bits) - 1) if searched_port_bits else 0
    return (draw.txid << searched_port_bits) | searched_port


def guess_space_size(txid_bits: int, port_bits: int, k: int) -> int:
    """`2 ** effective_bits(...)` -- the size of the space `GuessStream`
    searches."""
    return 1 << effective_bits(txid_bits, port_bits, k)


@dataclass
class GuessStream:
    """Seeded, portable-PRNG-ordered stream of **distinct** effective-index
    guesses (OQ-P3.2: no replacement within a search round). Realised by
    rejection sampling with a seen-set bounded by the packet budget --
    `space_size` (up to `2**32`) is never materialised as a whole."""

    space_size: int
    state: int
    _seen: set[int] = field(default_factory=set, init=False, repr=False)

    def reset_round(self) -> None:
        """Start a fresh search round (OQ-P3.2: reset per retransmit round)."""
        self._seen.clear()

    def next(self) -> int:
        if len(self._seen) >= self.space_size:
            self.reset_round()
        while True:
            guess, self.state = bounded(self.state, self.space_size)
            if guess not in self._seen:
                self._seen.add(guess)
                return guess
