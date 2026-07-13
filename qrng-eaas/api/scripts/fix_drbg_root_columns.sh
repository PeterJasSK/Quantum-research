#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?Set DATABASE_URL to your production connection string before running this script}"

python3 -c "
import os, psycopg
with psycopg.connect(os.environ['DATABASE_URL']) as conn, conn.cursor() as cur:
    cur.execute('ALTER TABLE drbg_root ADD COLUMN IF NOT EXISTS nonce bytea;')
    cur.execute('ALTER TABLE drbg_root ADD COLUMN IF NOT EXISTS tag bytea;')
    conn.commit()
print('done')
"


