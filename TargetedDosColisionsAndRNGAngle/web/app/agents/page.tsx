import type { Metadata } from "next";
import Link from "next/link";
import StructuredData from "@/components/StructuredData";
import { API_URL, WEB_URL } from "@/lib/urls";

// Human- and crawler-readable onboarding page. The ECMP lab is a static demo of
// the salt-collision study; the agent/MCP surface it exposes is the QEaaS entropy
// service that supplies every salt. Reuses this site's design tokens/utilities.
export const metadata: Metadata = {
  title: "Agent integration · ECMP Salt-Collision DoS lab",
  description:
    "Discovery documents, MCP endpoint, and the QEaaS quantum-entropy API behind this ECMP salt-collision DoS lab — everything an agent needs to integrate.",
  alternates: { canonical: "/agents" },
  openGraph: {
    title: "Agent integration — ECMP Salt-Collision DoS lab",
    description:
      "Discovery documents, MCP endpoint, and the QEaaS entropy API behind the ECMP salt-collision DoS lab.",
    url: `${WEB_URL}/agents`,
  },
};

const PAGE_JSON_LD: Record<string, unknown>[] = [
  {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "ECMP Salt-Collision DoS lab",
    applicationCategory: "SecurityApplication",
    operatingSystem: "Any",
    url: `${WEB_URL}/agents`,
    description:
      "Live k=6 fat-tree lab for an ECMP salt-collision link-flooding attack and the salt-rotation defence, backed by QEaaS quantum entropy over HTTP and MCP.",
    offers: { "@type": "Offer", price: "0", priceCurrency: "EUR", description: "Free" },
  },
  {
    "@context": "https://schema.org",
    "@type": "APIReference",
    name: "QEaaS API",
    url: `${API_URL}/openapi.json`,
    description: "OpenAPI 3 description of the QEaaS entropy endpoints used for the salts.",
  },
];

const DISCOVERY = [
  { label: "Agent manifest", href: `${API_URL}/.well-known/agent.json` },
  { label: "MCP discovery", href: `${API_URL}/.well-known/mcp.json` },
  { label: "Tool descriptors", href: `${API_URL}/v1/agent/tools` },
  { label: "Onboarding manifest", href: `${API_URL}/v1/agent/manifest` },
  { label: "OpenAPI / Swagger", href: `${API_URL}/openapi.json` },
  { label: "llms.txt", href: `${WEB_URL}/llms.txt` },
  { label: "llms-full.txt", href: `${WEB_URL}/llms-full.txt` },
];

export default function AgentsPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-8 px-6 py-12">
      <StructuredData data={PAGE_JSON_LD} />

      <header className="flex flex-col gap-4">
        <span className="eyebrow">
          <span className="eyebrow-rule" />
          Agent &amp; MCP integration
        </span>
        <h1 className="hero-title">Integrate the entropy behind this lab</h1>
        <p className="max-w-2xl text-base leading-relaxed text-(--color-text)">
          This is a static lab for an <strong>ECMP</strong> (Equal-Cost Multi-Path) salt-collision
          link-flooding attack and its salt-rotation defence. It has no backend of its own — the
          agent-facing surface is <strong>QEaaS</strong>, the quantum-entropy service that supplies a
          fresh, attestable salt for every switch. Point your agent or MCP client at the discovery
          documents below.
        </p>
        <Link href="/" className="text-sm text-(--color-accent) hover:underline">
          ← back to the live lab
        </Link>
      </header>

      <div className="hairline" />

      <section className="panel flex flex-col gap-3 p-6">
        <h2 className="text-lg font-semibold text-(--color-heading)">Discovery documents</h2>
        <ul className="flex flex-col gap-2 text-sm">
          {DISCOVERY.map((d) => (
            <li key={d.href} className="flex flex-col sm:flex-row sm:gap-2">
              <span className="text-(--color-text) opacity-70">{d.label}:</span>
              <a href={d.href} className="break-all text-(--color-accent) hover:underline" rel="noreferrer">
                {d.href}
              </a>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel flex flex-col gap-3 p-6">
        <h2 className="text-lg font-semibold text-(--color-heading)">How to get a key</h2>
        <p className="text-sm leading-relaxed text-(--color-text)">
          QEaaS public endpoints (health, random, dice, verify, pubkey) need no key. Developer and
          KEM endpoints require the header{" "}
          <code className="rounded bg-(--color-bg-deep) px-1.5 py-0.5 font-(family-name:--font-mono) text-(--color-accent)">
            X-API-Key
          </code>
          . Keys are admin-minted, revocable, and quota-metered — request one from the operator.
          Over-limit requests return HTTP 429.
        </p>
      </section>

      <section className="panel flex flex-col gap-3 p-6">
        <h2 className="text-lg font-semibold text-(--color-heading)">Worked example</h2>
        <pre className="overflow-x-auto rounded-lg bg-(--color-bg-deep) p-4 font-(family-name:--font-mono) text-xs text-(--color-text)">
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
    </div>
  );
}
