// Canonical base URLs from env, never hard-coded. Mirrors the twin's lib/urls.ts.
// WEB_URL is the canonical site host (sitemap/robots/metadataBase); API_URL is the
// QEaaS API host shown in the provenance callout. The production domain for this
// DNS-poison-race demo is not chosen yet (plan OQ-6.2, deferred), so WEB_URL
// defaults to a neutral, env-overridable localhost value.
export const WEB_URL = process.env.NEXT_PUBLIC_WEB_URL ?? "http://localhost:3000";
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://api.qeaas.eu";
