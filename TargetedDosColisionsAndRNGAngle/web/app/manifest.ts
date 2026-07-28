import type { MetadataRoute } from "next";

// PWA manifest served at /manifest.webmanifest, linked from metadata.
// Theme matches the shared QEaaS neon-cyan design tokens.
export const dynamic = "force-static";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "The Attacker in the Gap — ECMP Salt-Collision DoS",
    short_name: "ECMP DoS Lab",
    description:
      "Live k=6 fat-tree lab: an ECMP salt-collision link-flooding attack and the salt-rotation defence, with QEaaS quantum entropy for every salt.",
    start_url: "/",
    display: "standalone",
    background_color: "#052e44",
    theme_color: "#00aaff",
  };
}
