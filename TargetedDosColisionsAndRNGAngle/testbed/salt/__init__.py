"""Salt engine package (P2): three interchangeable salt sources feeding the
frozen `hash_core.ecmp_link` (epic ss3.5)."""
from __future__ import annotations

from .sources import SaltKind, SaltProvenance, SaltResult, salt_source

__all__ = ["SaltKind", "SaltProvenance", "SaltResult", "salt_source"]
