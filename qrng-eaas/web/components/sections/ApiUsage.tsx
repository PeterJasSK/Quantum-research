interface Endpoint {
  method: string;
  path: string;
  purpose: string;
  params: string;
  notes: string;
  curl: string;
}

interface Group {
  title: string;
  entries: Endpoint[];
}

const GROUPS: Group[] = [
  {
    title: "Public (anonymous, rate-limited, no key)",
    entries: [
      {
        method: "GET",
        path: "/health",
        purpose: "Liveness + entropy status",
        params: "—",
        notes: "{status, quantum_entropy_level, pool_bytes_remaining, drbg_reseeds, uptime}",
        curl: `curl -s "<base>/health"`,
      },
      {
        method: "GET",
        path: "/random?bytes=N",
        purpose: "Small DRBG byte draw (powers dice)",
        params: "bytes 1–64 (default 32)",
        notes: "base64; anon daily ceiling applies",
        curl: `curl -s "<base>/random?bytes=32"`,
      },
      {
        method: "POST",
        path: "/dice",
        purpose: "Rejection-sampled dice rolls",
        params: `{"sides":2–100, "count":1–6}`,
        notes: "echoes the DRBG bytes drawn",
        curl: `curl -s -X POST <base>/dice \\
  -H 'content-type: application/json' \\
  -d '{"sides":20,"count":3}'`,
      },
    ],
  },
  {
    title: "Developer (require X-API-Key, quota-metered)",
    entries: [
      {
        method: "GET",
        path: "/v1/random/bytes?size=N&format=hex|base64",
        purpose: "Canonical dev entropy",
        params: "size 32–4096, format (default hex)",
        notes: "returns request_id, data, entropy_epoch, timestamp, receipt",
        curl: `curl -s "<base>/v1/random/bytes?size=32&format=hex" \\
  -H "X-API-Key: <your-key>"`,
      },
      {
        method: "GET",
        path: "/v1/seed?bytes=N&format=hex|base64",
        purpose: "Alias of the above",
        params: "bytes 32–4096, format",
        notes: "same engine/limits (compat)",
        curl: `curl -s "<base>/v1/seed?bytes=32&format=hex" \\
  -H "X-API-Key: <your-key>"`,
      },
      {
        method: "POST",
        path: "/v1/kem/keypair",
        purpose: "QRNG-seeded ML-KEM-768 keypair",
        params: `{"include_secret_key": bool}`,
        notes: "public_key always; secret_key demo-only",
        curl: `curl -s -X POST <base>/v1/kem/keypair \\
  -H "X-API-Key: <your-key>" -H 'content-type: application/json' -d '{}'`,
      },
      {
        method: "POST",
        path: "/v1/kem/encapsulate",
        purpose: "Encapsulate to an ek",
        params: `{"public_key": b64, "include_shared_secret": bool}`,
        notes: "ciphertext always; shared_secret/demo_key demo-only",
        curl: `curl -s -X POST <base>/v1/kem/encapsulate \\
  -H "X-API-Key: <your-key>" -H 'content-type: application/json' \\
  -d '{"public_key":"<ek>","include_shared_secret":true}'`,
      },
    ],
  },
  {
    title: "Provenance (anonymous)",
    entries: [
      {
        method: "POST",
        path: "/v1/verify",
        purpose: "Verify a receipt / resolve a request",
        params: `{"request_id": str} and/or {"receipt": str}`,
        notes: `{request_id, verified, provenance, note}; not a value oracle`,
        curl: `curl -s -X POST <base>/v1/verify \\
  -H 'content-type: application/json' -d '{"receipt":"qeaas1...."}'`,
      },
      {
        method: "GET",
        path: "/v1/pubkey",
        purpose: "Published Ed25519 receipt-signing key",
        params: "—",
        notes: `{algorithm:"Ed25519", format:"base64", public_key}`,
        curl: `curl -s <base>/v1/pubkey`,
      },
    ],
  },
  {
    title: "Admin (require X-Admin-Token)",
    entries: [
      {
        method: "POST",
        path: "/admin/keys",
        purpose: "Mint an API key",
        params: `{"owner", "tier"?, "daily_quota_bytes"?}`,
        notes: "returns the plaintext key once",
        curl: `curl -s -X POST <base>/admin/keys \\
  -H "X-Admin-Token: <token>" -H 'content-type: application/json' \\
  -d '{"owner":"you","tier":"default"}'`,
      },
      {
        method: "POST",
        path: "/admin/keys/revoke",
        purpose: "Revoke a key (instant)",
        params: `{"key_hash"}`,
        notes: "takes effect on the next request",
        curl: `curl -s -X POST <base>/admin/keys/revoke \\
  -H "X-Admin-Token: <token>" -H 'content-type: application/json' \\
  -d '{"key_hash":"<hash>"}'`,
      },
      {
        method: "POST",
        path: "/admin/ingest",
        purpose: "Refill the entropy pool",
        params: "multipart .txt of 0/1, ≤10 MB",
        notes: "AES-256-GCM encrypted at rest",
        curl: `curl -s -X POST <base>/admin/ingest \\
  -H "X-Admin-Token: <token>" -F "file=@bits.txt"`,
      },
    ],
  },
];

const GETTING_STARTED = [
  {
    title: "Get a key",
    body: (
      <>
        an admin mints one (<code>POST /admin/keys</code> with your{" "}
        <code>owner</code>/<code>tier</code>); the plaintext key is shown{" "}
        <strong>once</strong>, store it securely (the server keeps only a
        hash).
      </>
    ),
  },
  {
    title: "Authenticate",
    body: (
      <>
        send it as the <code>X-API-Key</code> header on every
        developer/KEM call.
      </>
    ),
  },
  {
    title: "First call",
    body: (
      <>
        <code>GET /v1/random/bytes?size=32&format=hex</code> → you get{" "}
        <code>data</code> plus provenance (<code>request_id</code>,{" "}
        <code>entropy_epoch</code>, <code>timestamp</code>,{" "}
        <code>receipt</code>).
      </>
    ),
  },
  {
    title: "Check provenance",
    body: (
      <>
        <code>{`POST /v1/verify {"receipt": "<the receipt>"}`}</code> →{" "}
        <code>verified:true</code> and the QRNG batch/epoch it came from.
        The value itself is never stored or echoed.
      </>
    ),
  },
  {
    title: "Watch your limits",
    body: (
      <>
        <code>GET /health</code> shows entropy status; over-quota/over-rate
        calls return <code>429</code>; a degraded pool returns{" "}
        <code>503</code> on developer/KEM endpoints (dice keeps working).
      </>
    ),
  },
];

export default function ApiUsage() {
  return (
    <section className="mx-auto max-w-3xl px-4 py-12 sm:py-16">
      <h2 className="glow mb-4 text-xl font-semibold text-heading sm:text-2xl">
        How to use the API
      </h2>
      <p className="mb-8 text-sm text-text/90 sm:mb-10 sm:text-base">
        Every response is DRBG-derived — raw QRNG bits are never served. The
        anonymous endpoints need no key and are rate-limited. Developer
        endpoints need an <code>X-API-Key</code> minted by an admin and are
        quota-metered per tier. Every developer/KEM issue returns a{" "}
        <strong>signed receipt</strong> you can check at{" "}
        <code>POST /v1/verify</code> without the value ever being stored.
        Admin endpoints need an <code>X-Admin-Token</code>.
      </p>

      <div className="flex flex-col gap-8 sm:gap-10">
        {GROUPS.map((group) => (
          <div key={group.title}>
            <h3 className="mb-4 text-base font-semibold text-heading sm:text-lg">
              {group.title}
            </h3>
            <div className="flex flex-col gap-4">
              {group.entries.map((entry) => (
                <div key={`${entry.method} ${entry.path}`} className="panel p-4">
                  <p className="mb-1 text-sm font-semibold text-heading">
                    {entry.method} {entry.path}
                  </p>
                  <p className="mb-1 text-sm text-text/90">{entry.purpose}</p>
                  <p className="mb-1 text-xs text-text/60">
                    Params/body: {entry.params}
                  </p>
                  <p className="mb-3 text-xs text-text/60">{entry.notes}</p>
                  <pre className="overflow-x-auto text-xs text-accent">
                    <code>{entry.curl}</code>
                  </pre>
                </div>
              ))}
            </div>
          </div>
        ))}

        <div>
          <h3 className="mb-4 text-base font-semibold text-heading sm:text-lg">
            Getting started with the API
          </h3>
          <ol className="flex flex-col gap-3 text-sm text-text/90">
            {GETTING_STARTED.map((step, index) => (
              <li key={step.title} className="panel p-4">
                <span className="mb-1 block font-semibold text-heading">
                  {index + 1}. {step.title}
                </span>
                {step.body}
              </li>
            ))}
          </ol>
        </div>

        <div className="panel p-4 sm:p-6">
          <h3 className="mb-4 text-base font-semibold text-heading sm:text-lg">
            Rules of usage
          </h3>
          <ul className="flex list-disc flex-col gap-3 pl-5 text-sm text-text/90">
            <li>
              <strong>Anonymous:</strong> 60 requests/min per IP;{" "}
              <code>/random</code> capped at 64 bytes/request; global anon
              output ceiling <strong>5 MiB/day</strong> (
              <code>daily_limit_reached</code> <code>429</code> over it).
            </li>
            <li>
              <strong>API-key tiers</strong> (per-key rate → daily byte
              quota): <code>default</code> 120/min →{" "}
              <strong>256 KiB/day</strong>; <code>iot</code> 600/min →{" "}
              <strong>10 MiB/day</strong>; <code>trusted</code> 1200/min →{" "}
              <strong>500 MiB/day</strong>. A per-key{" "}
              <code>daily_quota_bytes</code> override wins over the tier
              default. Over-rate → <code>rate_limited</code>; over-quota →{" "}
              <code>quota_exceeded</code> (both <code>429</code>, with{" "}
              <code>Retry-After</code>).
            </li>
            <li>
              <strong>Low-entropy gate:</strong> when the pool is degraded,
              developer/KEM endpoints return <code>503 low_quantum_entropy</code>;
              anon dice/<code>/random</code> keep serving from the current
              DRBG.
            </li>
            <li>
              <strong>Invariants:</strong> raw QRNG bits are{" "}
              <strong>never</strong> served (all output is DRBG-derived);
              revocation is instant; <code>/v1/verify</code> proves{" "}
              <strong>provenance, not the secret</strong> — it never stores
              or confirms a value.
            </li>
            <li>
              <strong>Error envelope:</strong> every error is{" "}
              <code>{`{"error": "<slug>"}`}</code> (<code>bad_request</code>{" "}
              422, <code>missing_api_key</code>/<code>invalid_api_key</code>/
              <code>unauthorized</code> 401, <code>rate_limited</code>/
              <code>daily_limit_reached</code>/<code>quota_exceeded</code>{" "}
              429, <code>low_quantum_entropy</code> 503,{" "}
              <code>file_too_large</code> 413, <code>not_found</code> 404).
            </li>
          </ul>
        </div>
      </div>
    </section>
  );
}
