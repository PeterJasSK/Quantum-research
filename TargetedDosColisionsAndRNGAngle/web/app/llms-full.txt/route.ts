import { API_URL, WEB_URL } from "@/lib/urls";

// Expanded text/plain index — background, the QEaaS entropy API it depends on,
// and agent/MCP discovery. Static template string (no live cross-fetch).
// Mirrors qrng-eaas/web/app/llms-full.txt/route.ts.

export const dynamic = "force-static";

function body(): string {
  return `# The Attacker in the Gap — ECMP Salt-Collision DoS — full index

## Summary
ECMP (Equal-Cost Multi-Path) spreads traffic across the many equal-cost parallel
links between two points by hashing each flow's 5-tuple with a secret per-switch
salt, so a flow's packets stay in order while overall load fans out. If that salt
is weak or guessable, an attacker solves the hash offline and hand-picks source
ports whose flows all collide onto the same deep core→aggregation link. A single
host then floods that one link — a targeted collision DoS that evades volumetric
rate limits and connection caps. The defence: rotate the salt faster than it can
be reconstructed (a cadence this study derives and measures), and source that salt
from strong, fresh, attestable entropy.

## Base URLs
- Web: ${WEB_URL}
- Entropy API (QEaaS): ${API_URL}

## What the lab shows
- A full k=6 fat-tree (47 switches + 2 WAN, 36 hosts, 9 equal-cost paths per pod)
- Packets forwarded along the real ECMP-hashed routes, live
- A precision collision attacker that locks onto one link under a weak salt and
  scatters harmlessly under CSPRNG/QRNG
- Jain's fairness index and hash-polarization computed live from delivered packets
- A signed QEaaS provenance receipt for the quantum salt draws

## Threat model (honest scope)
- Single-switch entropy quality is invisible; polarization is a multi-stage effect
  that only appears when switches on a path share a salt.
- A strong CSPRNG blunts the attack as well as QRNG here; QRNG's distinguishing
  contribution is attestable provenance and deliver-as-a-service deployability.

## Entropy provider (QEaaS) — endpoints used for the salts
- GET  /health                                   Service health & entropy level (public)
- GET  /random?bytes=N                            Anonymous random bytes, N<=64 (public)
- GET  /v1/random/bytes?size=N&format=hex|base64  Developer bytes (X-API-Key)
- POST /v1/verify                                 Verify a provenance receipt (public)
- GET  /v1/pubkey                                 Ed25519 receipt-signing public key (public)
- POST /mcp                                       MCP server (JSON-RPC 2.0, Streamable-HTTP)

## Agent & MCP discovery (QEaaS)
- Agent manifest:      ${API_URL}/.well-known/agent.json
- ai-plugin manifest:  ${API_URL}/.well-known/ai-plugin.json
- MCP discovery:       ${API_URL}/.well-known/mcp.json
- Tool descriptors:    ${API_URL}/v1/agent/tools
- Onboarding manifest: ${API_URL}/v1/agent/manifest?profile=<http|openai-tools|anthropic-tools|mcp>
- OpenAPI:             ${API_URL}/openapi.json
- Human/agent page:    ${WEB_URL}/agents

## Quickstart (curl — QEaaS entropy)
    # anonymous
    curl -s "${API_URL}/random?bytes=32"

    # MCP (JSON-RPC 2.0)
    curl -s -X POST "${API_URL}/mcp" \\
      -H 'content-type: application/json' \\
      -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
`;
}

export async function GET() {
  return new Response(body(), {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}
