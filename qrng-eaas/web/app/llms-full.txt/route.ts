import { API_URL, WEB_URL } from "@/lib/urls";

// EPIC 13 AC-6 / Decision 7: expanded text/plain index -- full endpoint list +
// quickstart. Static template string (no live cross-fetch). The endpoint table
// mirrors the API catalog in qeaas/agent.py (kept static for edge reliability).

export const dynamic = "force-static";

function body(): string {
  return `# Quantum Entropy-as-a-Service (Q-EaaS) — full agent index

Q-EaaS supplies high-quality entropy from a quantum random number generator (QRNG)
that seeds a standards HMAC-DRBG (SP 800-90A). Only DRBG-derived bytes, seeds, and
ML-KEM key material are served -- raw QRNG bits are never exposed. The quantum part
is the entropy source; post-quantum resistance comes from ML-KEM (FIPS 203), not the
randomness itself.

## Base URLs
- Web: ${WEB_URL}
- API: ${API_URL}

## Authentication
Public endpoints (health, random, dice, verify, pubkey) need no key. Developer and
KEM endpoints require the header:

    X-API-Key: <your-key>

Keys are admin-minted, revocable, and quota-metered. Over-limit returns HTTP 429 with
a Retry-After header. Errors use a flat envelope: {"error":"<slug>"}.

## Endpoints
- GET  /health                      Service health & entropy level (public)
- GET  /random?bytes=N              Anonymous random bytes, N<=64 (public)
- POST /dice                        Roll dice, body {sides,count} (public)
- GET  /v1/random/bytes?size=N&format=hex|base64   Developer bytes, 32<=N<=4096 (X-API-Key)
- POST /v1/verify                   Verify a provenance receipt, body {request_id|receipt} (public)
- GET  /v1/pubkey                   Ed25519 receipt-signing public key (public)
- POST /v1/kem/keypair              QRNG-seeded ML-KEM-768 keypair (X-API-Key)
- POST /v1/kem/encapsulate          ML-KEM-768 encapsulation, body {public_key} (X-API-Key)
- POST /mcp                         MCP server (JSON-RPC 2.0, Streamable-HTTP)

## Quickstart (curl)
    # anonymous
    curl -s "${API_URL}/random?bytes=32"
    curl -s -X POST -H 'content-type: application/json' -d '{"sides":6,"count":2}' "${API_URL}/dice"

    # developer (needs a key)
    curl -s -H "X-API-Key: $QEAAS_API_KEY" "${API_URL}/v1/random/bytes?size=64&format=hex"

## Discovery documents
- Agent manifest:      ${API_URL}/.well-known/agent.json
- ai-plugin manifest:  ${API_URL}/.well-known/ai-plugin.json
- MCP discovery:       ${API_URL}/.well-known/mcp.json
- Tool descriptors:    ${API_URL}/v1/agent/tools
- Onboarding manifest: ${API_URL}/v1/agent/manifest?profile=<http|openai-tools|anthropic-tools|mcp>
- OpenAPI:             ${API_URL}/openapi.json
- Human/agent page:    ${WEB_URL}/agents

## Provenance
Every premium response ships a signed receipt over its metadata (request_id, size,
entropy_epoch, timestamp). Output bytes are never stored; POST /v1/verify resolves
provenance only -- never a value-confirmation oracle.
`;
}

export async function GET() {
  return new Response(body(), {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}
