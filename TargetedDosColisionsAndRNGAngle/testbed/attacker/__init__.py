"""Attacker package (P3): collision crafter, knowledge levels, and traffic
sender against the frozen `hash_core`/salt engine (epic ss3.5)."""
from __future__ import annotations

from .attack import run_attack
from .collision import CollisionCrafter
from .knowledge import KnowledgeLevel, Reconstruction, resolve_salt

__all__ = [
    "CollisionCrafter",
    "KnowledgeLevel",
    "Reconstruction",
    "resolve_salt",
    "run_attack",
]
