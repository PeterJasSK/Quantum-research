const QEAAS_URL = "https://qeaas.eu";

/** Findings-grounded product callout. Ties the three results this lab shows
 * (entropy is the whole game; SAD-DNS state beats raw source quality; QRNG ties
 * CSPRNG on defence but wins on provenance) to the deployable service the paper
 * promotes -- QEaaS at qeaas.eu. */
export default function QeaasCallout() {
  return (
    <section className="flex flex-col gap-4">
      <span className="eyebrow">
        <span className="eyebrow-rule" />
        From the research
      </span>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {[
          {
            k: "Entropy is the whole race",
            b: "A cache poisoner wins only by guessing the resolver's TXID+port before the authoritative reply lands. Above the cliff the guess space is astronomically large and the flood loses; drop below it and poisoning becomes near-certain.",
          },
          {
            k: "Provenance beats raw quality",
            b: "The SAD-DNS side channel leaks port bits and collapses even a 'safe' CSPRNG curve toward the guessable line. What saves you is not a fancier source but knowing the state of the randomness — exactly what a provenance receipt gives you.",
          },
          {
            k: "Quantum buys attestation, not a bigger hammer",
            b: "An honest null result: QRNG and a strong CSPRNG defend the race identically. QRNG's real edge is a signed, per-draw provenance receipt a CSPRNG cannot produce.",
          },
        ].map((c) => (
          <div key={c.k} className="panel card-hover flex flex-col gap-2 p-5">
            <h3 className="text-sm font-semibold text-(--color-heading)">{c.k}</h3>
            <p className="text-xs leading-relaxed text-(--color-text) opacity-85">{c.b}</p>
          </div>
        ))}
      </div>

      <div className="panel card-hover flex flex-col gap-6 p-6 md:flex-row md:items-center md:justify-between md:gap-10">
        <div className="flex flex-col gap-3">
          <span className="eyebrow">
            <span className="eyebrow-rule" />
            Deployable today
          </span>
          <h2 className="hero-title max-w-xl text-2xl md:text-3xl">
            The missing piece is <span className="hero-accent">auditable entropy as a service</span>.
          </h2>
          <p className="max-w-xl text-sm leading-relaxed text-(--color-text) opacity-90">
            <strong>QEaaS</strong> serves quantum entropy over a plain HTTP API — strong enough to keep a resolver&apos;s
            TXID/port draw out of a poisoner&apos;s reach, and every draw ships a signed receipt (entropy epoch, request
            id, Ed25519 signature) you can hand an auditor. Exactly the capability this lab shows a resolver is missing.
          </p>
          <div className="flex flex-wrap gap-2">
            <span className="chip">signed provenance</span>
            <span className="chip">quantum-seeded</span>
            <span className="chip">one HTTP call</span>
            <span className="chip">offline-verifiable</span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <a href={QEAAS_URL} target="_blank" rel="noopener noreferrer" className="pill px-5 py-2.5 text-sm font-semibold">
              Explore QEaaS ↗
            </a>
            <a
              href={`${QEAAS_URL}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-semibold text-(--color-accent) hover:underline"
            >
              API docs
            </a>
          </div>
        </div>

        <div className="w-full max-w-md shrink-0 rounded-2xl border border-(--color-border) bg-[color-mix(in_srgb,var(--color-bg-deep)_60%,transparent)] p-4">
          <div className="mb-2 flex items-center gap-2 text-xs text-(--color-text) opacity-70">
            <span className="lamp lamp-green" aria-hidden />
            api.qeaas.eu
          </div>
          <pre className="overflow-x-auto text-xs leading-relaxed text-(--color-text) font-(family-name:--font-mono)">
{`$ curl -H "X-API-Key: $KEY" \\
    "https://api.qeaas.eu/v1/random/bytes?size=32&format=hex"

{
  "request_id": "11f1500a…",
  "entropy_epoch": 30,
  "data": "fb81abcd…",
  "receipt": "qeaas1.eyJ…"   # Ed25519, verifiable
}`}
          </pre>
        </div>
      </div>
    </section>
  );
}
