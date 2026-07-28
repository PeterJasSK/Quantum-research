import type { MetadataRoute } from "next";
import { WEB_URL } from "@/lib/urls";

// Every public page, canonical host. Mirrors qrng-eaas/web/app/sitemap.ts.
export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  return [
    {
      url: `${WEB_URL}/`,
      lastModified,
      changeFrequency: "monthly",
      priority: 1.0,
    },
    {
      url: `${WEB_URL}/agents`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.7,
    },
  ];
}
