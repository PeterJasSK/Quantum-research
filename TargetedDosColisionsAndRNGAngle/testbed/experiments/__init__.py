"""Experiment orchestrator package (P5): drives the frozen P2/P3/P4 pieces
through the matrix; owns no attack/hash/metric logic of its own."""
from __future__ import annotations

from testbed.experiments.matrix import MATRIX, ExperimentCell, cells_for

__all__ = ["ExperimentCell", "MATRIX", "cells_for"]
