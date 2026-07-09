-- AC-4, Q2: API-key hash-validation table for /v1/random/bytes and /v1/seed.
-- daily_quota_bytes exists now so EPIC 3 needs no migration; unenforced until then.
CREATE TABLE IF NOT EXISTS api_keys (
    key_hash text PRIMARY KEY,
    owner text NOT NULL,
    tier text NOT NULL DEFAULT 'default',
    daily_quota_bytes bigint,
    revoked boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);
