# Quantum Entropy-as-a-Service (Q-EaaS)

Monorepo: `/web` (Next.js App Router + Tailwind), `/api` (FastAPI), `/shared` (docs, diagrams, spikes).
See `claude/QRNG_EaaS_BUILD_PLAN.md` for the full epic plan.

## Local dev

**API** (from `api/`):

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local
uvicorn main:app --reload --port 8000
```

**Web** (from `web/`):

```
npm install
npm run dev
```

## Spikes

- `shared/spikes/mlkem_seed_spike.py` — proves DRBG bytes deterministically drive ML-KEM-768 keygen
  and that encaps/decaps round-trips (S0.2). Run with `api/venv/bin/python shared/spikes/mlkem_seed_spike.py`.
