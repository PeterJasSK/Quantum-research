import type { Metadata } from "next";
import PageHero from "@/components/PageHero";
import StructuredData from "@/components/StructuredData";
import { API_URL, WEB_URL } from "@/lib/urls";

// EPIC 13 AC-7: human- and crawler-readable onboarding page. Reuses the design
// tokens (.glow/.panel/.pill); linked from the header nav and footer.
export const metadata: Metadata = {
  title: "Agent integration",
  description:
    "Integrate Q-EaaS from an AI agent: discovery documents, MCP endpoint, how to get a key, and a worked example.",
  alternates: { canonical: "/agents" },
  openGraph: {
    title: "Agent integration — Q-EaaS",
    description:
      "Discovery documents, MCP endpoint, and a worked example for integrating Q-EaaS.",
    url: `${WEB_URL}/agents`,
  },
};

// AC-9: SoftwareApplication (with free-tier offers) + APIReference structured data.
const PAGE_JSON_LD: Record<string, unknown>[] = [
  {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "Quantum Entropy-as-a-Service",
    applicationCategory: "DeveloperApplication",
    operatingSystem: "Any",
    url: `${WEB_URL}/agents`,
    description:
      "Quantum-seeded randomness, seeds & post-quantum ML-KEM key material over HTTP and MCP.",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "EUR",
      description: "Free tier",
    },
  },
  {
    "@context": "https://schema.org",
    "@type": "APIReference",
    name: "Q-EaaS API",
    url: `${API_URL}/openapi.json`,
    description: "OpenAPI 3 description of the Q-EaaS endpoints.",
  },
];

const DISCOVERY = [
  { label: "Agent manifest", href: `${API_URL}/.well-known/agent.json` },
  { label: "Tool descriptors", href: `${API_URL}/v1/agent/tools` },
  {
    label: "Onboarding manifest",
    href: `${API_URL}/v1/agent/manifest`,
  },
  { label: "OpenAPI / Swagger", href: `${API_URL}/openapi.json` },
  { label: "MCP discovery", href: `${API_URL}/.well-known/mcp.json` },
  { label: "llms.txt", href: `${WEB_URL}/llms.txt` },
];

export default function AgentsPage() {
  return (
    <PageHero title="Integrate Q-EaaS from an agent">
      <StructuredData data={PAGE_JSON_LD} />

      <p className="max-w-xl text-center text-sm text-text/90 sm:text-base">
        Q-EaaS supplies high-quality entropy from a quantum random number
        generator (QRNG) that seeds a standards HMAC-DRBG. Only DRBG-derived
        bytes, seeds, and ML-KEM key material are served — raw QRNG bits are
        never exposed. The quantum part is the entropy source; post-quantum
        resistance comes from ML-KEM.
      </p>

      <section className="panel w-full max-w-2xl p-5 sm:p-6">
        <h2 className="glow mb-3 text-lg font-semibold text-heading">
          Discovery documents
        </h2>
        <ul className="flex flex-col gap-2 text-sm">
          {DISCOVERY.map((d) => (
            <li key={d.href} className="flex flex-col sm:flex-row sm:gap-2">
              <span className="text-text/70">{d.label}:</span>
              <a
                href={d.href}
                className="break-all text-accent hover:underline"
                rel="noreferrer"
              >
                {d.href}
              </a>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel w-full max-w-2xl p-5 sm:p-6">
        <h2 className="glow mb-3 text-lg font-semibold text-heading">
          How to get a key
        </h2>
        <p className="text-sm text-text/90">
          Public endpoints (health, random, dice, verify, pubkey) need no key.
          Developer and KEM endpoints require the header{" "}
          <code className="rounded bg-bg-deep px-1.5 py-0.5 font-mono text-accent">
            X-API-Key
          </code>
          . Keys are admin-minted, revocable, and quota-metered — request one
          from the operator. Over-limit requests return HTTP 429.
        </p>
      </section>

      <section className="panel w-full max-w-2xl p-5 sm:p-6">
        <h2 className="glow mb-3 text-lg font-semibold text-heading">
          Tool specification
        </h2>
        <p className="mb-3 text-sm text-text/90">
          Machine-readable tool descriptors (one per callable endpoint, with
          JSON Schema) — ready to register in a function-calling or MCP runtime.
          The onboarding manifest also renders framework-shaped quickstarts via{" "}
          <code className="rounded bg-bg-deep px-1.5 py-0.5 font-mono text-accent">
            ?profile=http|openai-tools|anthropic-tools|mcp
          </code>
          .
        </p>
        <a
          href={`${API_URL}/v1/agent/tools`}
          className="pill px-5 py-2 text-sm font-semibold"
          rel="noreferrer"
        >
          Download tool descriptors
        </a>
      </section>

      <section className="panel w-full max-w-2xl p-5 sm:p-6">
        <h2 className="glow mb-3 text-lg font-semibold text-heading">
          Worked example
        </h2>
        <pre className="overflow-x-auto rounded-lg bg-bg-deep p-4 font-mono text-xs text-text/90">
          <code>{`# anonymous — no key needed
curl -s "${API_URL}/random?bytes=32"

# developer endpoint — needs a key
curl -s -H "X-API-Key: $QEAAS_API_KEY" \\
  "${API_URL}/v1/random/bytes?size=64&format=hex"

# MCP (JSON-RPC 2.0, Streamable-HTTP)
curl -s -X POST "${API_URL}/mcp" \\
  -H 'content-type: application/json' \\
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'`}</code>
        </pre>
      </section>
    </PageHero>
  );
}
