import type { MetadataRoute } from "next";
import { WEB_URL } from "@/lib/urls";

// Single-page demo: the whole spectacle lives at `/`.
export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: `${WEB_URL}/`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 1.0,
    },
  ];
}
