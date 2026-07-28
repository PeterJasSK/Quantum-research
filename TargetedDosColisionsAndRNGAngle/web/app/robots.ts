import type { MetadataRoute } from "next";
import { WEB_URL } from "@/lib/urls";

// Canonical host + explicit allow for the major classic and AI crawlers.
// Mirrors qrng-eaas/web/app/robots.ts.
const AI_CRAWLERS = [
  "GPTBot",
  "OAI-SearchBot",
  "ChatGPT-User",
  "ClaudeBot",
  "anthropic-ai",
  "Claude-Web",
  "PerplexityBot",
  "Google-Extended",
  "CCBot",
  "Bytespider",
  "Amazonbot",
  "Applebot-Extended",
];

export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: "*", allow: ["/", "/.well-known/"] },
      { userAgent: AI_CRAWLERS, allow: ["/", "/.well-known/"] },
    ],
    sitemap: `${WEB_URL}/sitemap.xml`,
    host: WEB_URL,
  };
}
