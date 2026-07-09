"""AC-3, AC-5: keyed DRBG output is deterministic per (root_key, counter) and
distinct across concurrent counter values."""

from __future__ import annotations

import itertools
from datetime import datetime

import qeaas.keyed_drbg as keyed_drbg
from qeaas import db

ROOT_KEY = b"\x01" * 32


def _fixed_root_row() -> db.RootKeyRow:
    return db.RootKeyRow(
        id=1,
        root_key=ROOT_KEY,
        reseed_counter=0,
        outputs_since_reseed=0,
        rotated_at=datetime.now(),
    )


def _patch_common(monkeypatch, counters) -> None:
    monkeypatch.setattr(keyed_drbg, "_cache", None)
    monkeypatch.setattr(db, "get_root_key", lambda: _fixed_root_row())
    monkeypatch.setattr(db, "bump_outputs_since_reseed", lambda root_id: None)
    counter_iter = iter(counters)
    monkeypatch.setattr(keyed_drbg, "incr_counter", lambda: next(counter_iter))


def test_distinct_counters_give_distinct_output(monkeypatch) -> None:
    _patch_common(monkeypatch, [1, 2])
    first = keyed_drbg.output(32)
    second = keyed_drbg.output(32)
    assert first != second


def test_same_counter_is_deterministic(monkeypatch) -> None:
    _patch_common(monkeypatch, [7])
    first = keyed_drbg.output(32)

    _patch_common(monkeypatch, [7])
    second = keyed_drbg.output(32)

    assert first == second
