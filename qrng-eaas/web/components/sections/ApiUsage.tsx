const SNIPPETS = [
  {
    title: "Anonymous random bytes",
    curl: `curl -s "https://q-eaas.example/random?bytes=32"`,
  },
  {
    title: "Roll dice",
    curl: `curl -s -X POST https://q-eaas.example/dice \\
  -H 'content-type: application/json' \\
  -d '{"sides":20,"count":3}'`,
  },
  {
    title: "Keyed developer entropy",
    curl: `curl -s "https://q-eaas.example/v1/random/bytes?size=32&format=hex" \\
  -H 'X-API-Key: <your-key>'`,
  },
];

export default function ApiUsage() {
  return (
    <section className="mx-auto max-w-3xl px-4 py-16">
      <h2 className="glow mb-4 text-2xl font-semibold text-heading">
        How to use the API
      </h2>
      <p className="mb-6 text-text/90">
        Every response is DRBG-derived — raw QRNG bits are never served. The
        anonymous endpoints (<code>/random</code>, <code>/dice</code>) are
        rate-limited and need no key. Higher-volume developer access goes
        through <code>GET /v1/random/bytes</code>, which requires an{" "}
        <code>X-API-Key</code> minted by an admin (see the project README for
        the key-minting flow).
      </p>
      <div className="flex flex-col gap-4">
        {SNIPPETS.map((snippet) => (
          <div key={snippet.title} className="panel p-4">
            <p className="mb-2 text-sm font-semibold text-heading">
              {snippet.title}
            </p>
            <pre className="overflow-x-auto text-xs text-accent">
              <code>{snippet.curl}</code>
            </pre>
          </div>
        ))}
      </div>
    </section>
  );
}
