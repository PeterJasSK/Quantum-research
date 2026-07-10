-- AC-8: abuse-spotting log for keyed issues + admin mint/revoke. `principal` is the
-- client IP for anon or the key hash for keyed requests; anon /random /dice are not
-- logged here (Q7) -- they are visible via the Redis rate/quota counters instead.
CREATE TABLE IF NOT EXISTS usage_log (
    id bigserial PRIMARY KEY,
    ts timestamptz NOT NULL DEFAULT now(),
    principal text NOT NULL,
    endpoint text NOT NULL,
    nbytes bigint NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS usage_log_principal_ts ON usage_log (principal, ts);
