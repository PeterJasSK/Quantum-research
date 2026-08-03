"""Experiment matrix package (epic §9 P5). Sibling of `testbed/resolver/`,
`testbed/analysis/`. Re-exports the sweep surface P5/P6 consume as frozen data.
"""
from __future__ import annotations

from .matrix import BIRTHDAY, CLIFF, COLLAPSE, ExperimentCell, cells_for

__all__ = ["ExperimentCell", "cells_for", "CLIFF", "COLLAPSE", "BIRTHDAY"]
