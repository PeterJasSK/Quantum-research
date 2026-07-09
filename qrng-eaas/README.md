# Quantum Entropy-as-a-Service (Q-EaaS)

Monorepo: `/web` (Next.js App Router + Tailwind), `/api` (FastAPI), `/shared` (docs, diagrams, spikes).
See `claude/QRNG_EaaS_BUILD_PLAN.md` for the full epic plan.

## Local dev

**API** (from `api/`):

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000 --env-file .env
```

That starts the app, but every route touches Postgres (`DATABASE_URL`) and most touch Redis
(`REDIS_URL`) — without real values in `.env` every request 500s. See the next section for a
throwaway local backend.

**Web** (from `web/`):

```
npm install
npm run dev
```

## Running the API locally against a real (throwaway) backend

The app needs a real Postgres (root key + entropy pool + API keys) and Redis (DRBG output
counter). If you don't have Neon/Upstash dev credentials, spin up disposable containers with
Docker — this is exactly how EPIC 2 was verified.

### 1. Start Postgres + Redis (one command)

From `api/`:

```bash
./scripts/dev_db_up.sh
```

This starts two disposable containers (`qeaas-pg`, `qeaas-redis`, both `--rm` so they vanish
on stop), waits for Postgres to actually be ready, and applies both SQL migrations. It prints
the env vars to export.

To skip the copy/paste, export them straight into your shell instead:

```bash
eval "$(./scripts/dev_db_up.sh --print-env)"
```

Running it again while the containers are still up will refuse (it tells you to run
`dev_db_down.sh` first) rather than silently reusing/duplicating them.

### 2. Configure the environment

If you used `eval "$(...--print-env)"` above, skip this — it's already exported. Otherwise
copy the block the plain `dev_db_up.sh` run printed, or put it in `api/.env` and pass
`--env-file .env` to uvicorn.

### 3. Seed the entropy pool

The DRBG root key bootstraps itself from the pool on first use, and `/health` reports
`quantum_entropy_level: "degraded"` below 64 KiB of pool bytes (gated routes 503 until then).
Feed it a `0`/`1` bits file:

```bash
python3 -c "
import random
random.seed(1)
open('/tmp/bits.txt','w').write(''.join(random.choice('01') for _ in range(700000)))
"
python scripts/ingest_bits.py /tmp/bits.txt seed
```

(Real deployments ingest actual QRNG output; for local testing any `0/1` text works — it's
only exercising the pipeline, not measuring quantumness.)

### 4. Mint a dev API key

`/v1/random/bytes` and `/v1/seed` require `X-API-Key`. There's no HTTP mint route yet
(EPIC 3); use the CLI, which prints the plaintext key once:

```bash
python -m scripts.mint_key --owner devtest --tier default
# api key for 'devtest' (tier=default): <plaintext key>  <-- copy this
```

### 5. Start the app

```bash
uvicorn main:app --port 8000
```

### 6. Confirm it's actually working

```bash
curl -s http://127.0.0.1:8000/health          # {"status":"ok","quantum_entropy_level":"healthy",...}
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/openapi.json   # 200
open http://127.0.0.1:8000/docs               # interactive Swagger UI, every route typed
```

Then exercise the actual routes (replace `<key>` with the value from step 4):

```bash
# public, ungated
curl -s "http://127.0.0.1:8000/random?bytes=32"
curl -s -X POST http://127.0.0.1:8000/dice -H 'content-type: application/json' \
  -d '{"sides":6,"count":2}'

# key-gated (canonical dev endpoint + alias)
curl -s -H "X-API-Key: <key>" "http://127.0.0.1:8000/v1/random/bytes?size=64&format=hex"
curl -s -H "X-API-Key: <key>" "http://127.0.0.1:8000/v1/seed?bytes=64"

# provenance stub
curl -s -X POST http://127.0.0.1:8000/v1/verify -H 'content-type: application/json' \
  -d '{"request_id":"abc"}'

# admin-only pool refill
echo -n "01010101" > /tmp/small.txt
curl -s -X POST http://127.0.0.1:8000/admin/ingest -H "X-Admin-Token: devtoken" \
  -F "file=@/tmp/small.txt"
```

Edge cases worth checking (each should return the flat `{"error": "<slug>"}` body):

| Request | Expected |
|---|---|
| `/random?bytes=65` | `422` |
| `/dice {"sides":6,"count":7}` | `422` |
| `/v1/random/bytes` with no `X-API-Key` | `401 missing_api_key` |
| `/v1/random/bytes` with a revoked key | `401 invalid_api_key` |
| `/admin/ingest` with wrong `X-Admin-Token` | `401` |
| `/admin/ingest` with a file > 10 MB | `413` |
| pool below 64 KiB (skip step 3, or don't seed enough) | `/v1/random/bytes`, `/v1/seed` → `503` |

To revoke the test key and confirm the `401`:

```bash
docker exec qeaas-pg psql -U postgres -d qeaas -c "UPDATE api_keys SET revoked=true;"
```

### 7. Tear down

```bash
pkill -f "uvicorn main:app"
./scripts/dev_db_down.sh
```

## Spikes

- `shared/spikes/mlkem_seed_spike.py` — proves DRBG bytes deterministically drive ML-KEM-768 keygen
  and that encaps/decaps round-trips (S0.2). Run with `api/venv/bin/python shared/spikes/mlkem_seed_spike.py`.
