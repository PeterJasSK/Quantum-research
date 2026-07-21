// EPIC 13 AC-11: canonical base URLs from env, never hard-coded. WEB_URL is the
// canonical site host (sitemap/robots/metadataBase); API_URL is the API host
// used for the absolute discovery links shown on /agents and in llms.txt.
// These are display/link hosts and are distinct from NEXT_PUBLIC_API_BASE in
// lib/api.ts, which is the runtime fetch base (often the same-origin proxy).

export const WEB_URL = process.env.NEXT_PUBLIC_WEB_URL ?? "https://qeaas.eu";
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://api.qeaas.eu";
