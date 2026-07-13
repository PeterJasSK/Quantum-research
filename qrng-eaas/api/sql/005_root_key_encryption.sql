-- EPIC 10 (S10.4/AC-1/AC-7): the DRBG root seed is now encrypted at rest under the
-- `drbg-root-encryption-key` HKDF sub-key (AES-256-GCM). `root_key` holds ciphertext;
-- `nonce`/`tag` are nullable only to tolerate a pre-migration row until it is
-- re-encrypted on first read (see `keyed_drbg._load_cache`).
ALTER TABLE drbg_root ADD COLUMN IF NOT EXISTS nonce bytea;
ALTER TABLE drbg_root ADD COLUMN IF NOT EXISTS tag bytea;
