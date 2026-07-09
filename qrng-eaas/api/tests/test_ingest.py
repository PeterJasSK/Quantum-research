"""AC-14: parse_bits_file input contract."""

from __future__ import annotations

import pytest

from qeaas.pool import parse_bits_file


def test_parses_plain_bits(tmp_path) -> None:
    path = tmp_path / "bits.txt"
    path.write_text("01000001")  # 'A'
    assert parse_bits_file(path) == b"A"


def test_strips_whitespace_and_newlines(tmp_path) -> None:
    path = tmp_path / "bits.txt"
    path.write_text("0100\n0001 \t\n")
    assert parse_bits_file(path) == b"A"


def test_rejects_non_01_characters(tmp_path) -> None:
    path = tmp_path / "bits.txt"
    path.write_text("0100bits:0001")
    with pytest.raises(ValueError):
        parse_bits_file(path)


def test_msb_first_packing(tmp_path) -> None:
    path = tmp_path / "bits.txt"
    path.write_text("00000001")
    assert parse_bits_file(path) == bytes([1])


def test_drops_trailing_partial_byte(tmp_path) -> None:
    path = tmp_path / "bits.txt"
    path.write_text("01000001101")  # 8 full bits + 3 leftover
    assert parse_bits_file(path) == b"A"
