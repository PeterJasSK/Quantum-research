import type { MetadataRoute } from "next";

const BASE = "https://qrng.peterjas.sk";

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  return [
    {
      url: `${BASE}/`,
      lastModified,
      changeFrequency: "monthly",
      priority: 1.0,
    },
    {
      url: `${BASE}/demo`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      url: `${BASE}/dice`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.8,
    },
  ];
}
