"""EPIC 13 Decision 4: minimal base-URL config for agent-first discovery.

Reads only `PUBLIC_API_URL` / `PUBLIC_WEB_URL` (localhost defaults) so every
emitted absolute link (agent.json, manifest, tool descriptors, MCP discovery)
uses the real domains in production and localhost in dev -- never a hard-coded
host. This is intentionally *not* the centralised settings module (EPIC 14):
keep Part 1 small and additive.
"""

from __future__ import annotations

import os

_DEFAULT_API_URL = "http://localhost:8000"
_DEFAULT_WEB_URL = "http://localhost:3000"


def api_url() -> str:
    """Canonical API base, e.g. `https://api.qeaas.eu`. No trailing slash."""
    return os.environ.get("PUBLIC_API_URL", _DEFAULT_API_URL).rstrip("/")


def web_url() -> str:
    """Canonical web base, e.g. `https://qeaas.eu`. No trailing slash."""
    return os.environ.get("PUBLIC_WEB_URL", _DEFAULT_WEB_URL).rstrip("/")
