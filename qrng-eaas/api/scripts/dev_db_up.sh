#!/usr/bin/env bash
# Spin up disposable Postgres + Redis containers for local API testing and
# apply the SQL migrations.
#
# Usage:
#   scripts/dev_db_up.sh                    # start + print export lines
#   eval "$(scripts/dev_db_up.sh --print-env)"   # start + export into this shell
set -euo pipefail

cd "$(dirname "$0")/.."

PG_NAME=qeaas-pg
REDIS_NAME=qeaas-redis
PG_PORT=55432
REDIS_PORT=56379
PRINT_ENV=false
[[ "${1:-}" == "--print-env" ]] && PRINT_ENV=true

log() { if ! $PRINT_ENV; then echo "$@" >&2; fi; }

if docker ps -a --format '{{.Names}}' | grep -qx "$PG_NAME"; then
    echo "Container $PG_NAME already exists -- run scripts/dev_db_down.sh first." >&2
    exit 1
fi
if docker ps -a --format '{{.Names}}' | grep -qx "$REDIS_NAME"; then
    echo "Container $REDIS_NAME already exists -- run scripts/dev_db_down.sh first." >&2
    exit 1
fi

log "Starting Postgres ($PG_NAME) on port $PG_PORT..."
docker run -d --rm --name "$PG_NAME" \
    -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=qeaas \
    -p "${PG_PORT}:5432" postgres:16-alpine >/dev/null

log "Starting Redis ($REDIS_NAME) on port $REDIS_PORT..."
docker run -d --rm --name "$REDIS_NAME" \
    -p "${REDIS_PORT}:6379" redis:7-alpine >/dev/null

log "Waiting for Postgres to accept connections..."
# The postgres image restarts itself once after initdb -- pg_isready can report
# ready during that transient instance, so retry the real migration instead of
# trusting a single readiness check.
ready=false
for _ in $(seq 1 30); do
    if docker exec -i "$PG_NAME" psql -U postgres -d qeaas -c '\q' >/dev/null 2>&1; then
        ready=true
        break
    fi
    sleep 1
done
if ! $ready; then
    echo "Postgres never became ready after 30s." >&2
    exit 1
fi

log "Applying SQL migrations..."
docker exec -i "$PG_NAME" psql -U postgres -d qeaas < sql/001_entropy_core.sql >&2
docker exec -i "$PG_NAME" psql -U postgres -d qeaas < sql/002_api_keys.sql >&2
docker exec -i "$PG_NAME" psql -U postgres -d qeaas < sql/003_usage_log.sql >&2

if $PRINT_ENV; then
    cat <<EOF
export MASTER_KEY="00000000000000000000000000000000000000000000000000000000000000"
export DATABASE_URL="postgresql://postgres:pw@127.0.0.1:${PG_PORT}/qeaas"
export REDIS_URL="redis://127.0.0.1:${REDIS_PORT}"
export ADMIN_TOKEN="devtoken"
export WEB_ORIGIN="http://localhost:3000"
EOF
else
    cat <<EOF

Postgres and Redis are up. Export these before running the app:

    export MASTER_KEY="00000000000000000000000000000000000000000000000000000000000000"
    export DATABASE_URL="postgresql://postgres:pw@127.0.0.1:${PG_PORT}/qeaas"
    export REDIS_URL="redis://127.0.0.1:${REDIS_PORT}"
    export ADMIN_TOKEN="devtoken"
    export WEB_ORIGIN="http://localhost:3000"

Or next time: eval "\$(scripts/dev_db_up.sh --print-env)" to skip copy/paste.

Tear down with: scripts/dev_db_down.sh
EOF
fi
