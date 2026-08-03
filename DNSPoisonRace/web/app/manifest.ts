import type { MetadataRoute } from "next";

// PWA manifest served at /manifest.webmanifest. Theme colours from the P6 palette.
export const dynamic = "force-static";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "DNS Poison Race — how many entropy bits stop a cache poisoner?",
    short_name: "DNS Poison Race",
    description:
      "Live client-side lab: an attacker's forged-answer flood races the authoritative reply into a resolver's cache. Entropy cliff, SAD-DNS reveal, guess-space heatmap, and a signed QRNG provenance receipt.",
    start_url: "/",
    display: "standalone",
    background_color: "#06202f",
    theme_color: "#06b6d4",
  };
}
