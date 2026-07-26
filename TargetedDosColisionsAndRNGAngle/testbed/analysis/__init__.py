"""Analysis + graphs package (P5): reads the P4 CSVs, renders the paper's
two key graphs. Offline (no os_ken/root) -- pure data-in, figure-out."""
from __future__ import annotations

from testbed.analysis.graphs import render_graphs
from testbed.analysis.rotation_threshold import rotation_threshold
from testbed.analysis.success import attacker_succeeded

__all__ = ["attacker_succeeded", "render_graphs", "rotation_threshold"]
