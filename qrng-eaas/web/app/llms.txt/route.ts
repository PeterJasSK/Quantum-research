import { API_URL, WEB_URL } from "@/lib/urls";

// EPIC 13 AC-6 / Decision 7: App Router route handler (folder literally named
// "llms.txt") serving a short text/plain agent index. Static template string,
// no live cross-fetch, so it is reliable on the edge.

export const dynamic = "force-static";

function body(): string {
  return `# Quantum Entropy-as-a-Service (Q-EaaS)

Q-EaaS supplies high-quality entropy from a quantum random number generator (QRNG)
that seeds a standards HMAC-DRBG (SP 800-90A). Only DRBG-derived bytes, seeds, and
ML-KEM key material are served -- raw QRNG bits are never exposed. The quantum part
is the entropy source; post-quantum resistance comes from ML-KEM (FIPS 203).

## What it does
- Quantum-seeded random bytes and cryptographic seeds (with signed provenance receipts)
- QRNG-seeded ML-KEM-768 (Kyber) keypair generation + encapsulation (post-quantum demo)
- Anonymous, rate-limited dice roller
- Offline receipt verification via a published Ed25519 public key

## Agent discovery
- Agent manifest: ${API_URL}/.well-known/agent.json
- Tool descriptors: ${API_URL}/v1/agent/tools
- Onboarding manifest: ${API_URL}/v1/agent/manifest
- OpenAPI: ${API_URL}/openapi.json
- MCP endpoint (JSON-RPC 2.0, POST): ${API_URL}/mcp
- Human/agent page: ${WEB_URL}/agents
- Expanded index: ${WEB_URL}/llms-full.txt

Auth: public endpoints need no key; developer endpoints require the header
X-API-Key (admin-minted, revocable, quota-metered).
`;
}

export async function GET() {
  return new Response(body(), {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}
