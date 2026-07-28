// Canonical base URLs from env, never hard-coded. Mirrors qrng-eaas/web/lib/urls.ts.
// WEB_URL is the canonical site host (sitemap/robots/metadataBase); API_URL is the
// QEaaS API host used for the discovery links shown on /agents and in llms.txt —
// this static ECMP lab has no backend of its own, so agent/MCP integration flows
// through the QEaaS entropy service it depends on.
export const WEB_URL = process.env.NEXT_PUBLIC_WEB_URL ?? "https://ecmp.peterjas.sk";
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://api.qeaas.eu";
