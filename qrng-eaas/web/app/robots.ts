import type { MetadataRoute } from "next";
import { WEB_URL } from "@/lib/urls";

// EPIC 13 AC-8: canonical host qeaas.eu; allow the /.well-known/ discovery path;
// explicitly allow the major classic + AI crawlers.
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

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/.well-known/"],
        disallow: "/api/",
      },
      {
        userAgent: AI_CRAWLERS,
        allow: ["/", "/.well-known/"],
        disallow: "/api/",
      },
    ],
    sitemap: `${WEB_URL}/sitemap.xml`,
    host: WEB_URL,
  };
}
