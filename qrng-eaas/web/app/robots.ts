import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: "/api/",
    },
    sitemap: "https://qrng.peterjas.sk/sitemap.xml",
    host: "https://qrng.peterjas.sk",
  };
}
