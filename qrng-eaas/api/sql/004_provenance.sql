-- EPIC 9, AC-3/AC-8: metadata-only provenance log for signed receipts.
-- No output bytes column exists here or ever will -- verify provenance, not the secret.
CREATE TABLE IF NOT EXISTS issue_log (
    request_id text PRIMARY KEY,
    principal text NOT NULL,
    endpoint text NOT NULL,
    size bigint NOT NULL DEFAULT 0,
    epoch_id bigint NOT NULL DEFAULT 0,
    ts timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS issue_log_ts ON issue_log (ts);
