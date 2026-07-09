-- EPIC 1: entropy core tables. Pool bytes are stored as AES-256-GCM
-- ciphertext (AC-12) -- plaintext QRNG bytes are never written here.

CREATE TABLE IF NOT EXISTS entropy_pool (
    id serial PRIMARY KEY,
    ciphertext bytea NOT NULL,
    nonce bytea NOT NULL,
    tag bytea NOT NULL,
    plaintext_len int NOT NULL,
    consumed_offset int NOT NULL DEFAULT 0,
    source_label text,
    uploaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS drbg_root (
    id serial PRIMARY KEY,
    root_key bytea NOT NULL,
    reseed_counter int NOT NULL DEFAULT 0,
    outputs_since_reseed int NOT NULL DEFAULT 0,
    rotated_at timestamptz NOT NULL DEFAULT now()
);
