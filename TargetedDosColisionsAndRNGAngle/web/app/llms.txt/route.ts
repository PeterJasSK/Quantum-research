import { API_URL, WEB_URL } from "@/lib/urls";

// App Router route handler (folder literally named "llms.txt") serving a short
// text/plain agent index. Static template string, reliable on static export.
// Mirrors qrng-eaas/web/app/llms.txt/route.ts.

export const dynamic = "force-static";

function body(): string {
  return `# The Attacker in the Gap — ECMP Salt-Collision DoS

A live lab and study of a link-flooding attack on ECMP (Equal-Cost Multi-Path)
load balancing: guess a switch's hash salt and a single host — no botnet — crafts
flows that all hash onto one deep fabric link, starving a victim while slipping
under the rate limits built to stop volumetric floods. The defence is to rotate
the salt faster than it can be reconstructed. Every salt is drawn from QEaaS
quantum entropy and ships a signed provenance receipt.

## What it is
- Interactive k=6 fat-tree lab showing ECMP load balancing and the precision collision attack
- Flow-level simulation over the real SHA-256 ECMP hash (JS/Python parity-checked)
- A computable salt-rotation cadence as a moving-target defence
- QEaaS-supplied, attestable quantum entropy for every per-switch salt

## Pages
- Home / live lab: ${WEB_URL}/
- Agent integration: ${WEB_URL}/agents
- Expanded index: ${WEB_URL}/llms-full.txt

## Entropy provider (QEaaS) — agent & MCP discovery
- Agent manifest: ${API_URL}/.well-known/agent.json
- MCP discovery: ${API_URL}/.well-known/mcp.json
- MCP endpoint (JSON-RPC 2.0, POST): ${API_URL}/mcp
- Tool descriptors: ${API_URL}/v1/agent/tools
- OpenAPI: ${API_URL}/openapi.json
`;
}

export async function GET() {
  return new Response(body(), {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}
