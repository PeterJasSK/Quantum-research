import type { MetadataRoute } from "next";
import { WEB_URL } from "@/lib/urls";

// EPIC 13 AC-8: every public page, canonical host qeaas.eu.
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
      url: `${WEB_URL}/demo`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      url: `${WEB_URL}/dice`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      url: `${WEB_URL}/agents`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.7,
    },
  ];
}
