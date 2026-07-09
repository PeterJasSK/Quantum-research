#!/usr/bin/env bash
# Tear down the disposable Postgres + Redis containers started by dev_db_up.sh.
set -euo pipefail

docker stop qeaas-pg qeaas-redis 2>/dev/null || true
echo "Stopped (containers were --rm, so they're already gone)."
