from __future__ import annotations

import os

os.environ.setdefault("MASTER_KEY", "00" * 32)
os.environ.setdefault("DATABASE_URL", "postgresql://unused/unused")
os.environ.setdefault("REDIS_URL", "redis://unused")
