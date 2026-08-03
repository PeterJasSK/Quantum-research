"""Figure renderer package (epic §9 P5) -- the first module in the study allowed
pandas/matplotlib (confined here, epic §3, P4 `csv_writer` docstring).
"""
from __future__ import annotations

from .graphs import render_cliff, render_collapse, render_graphs

__all__ = ["render_cliff", "render_collapse", "render_graphs"]
