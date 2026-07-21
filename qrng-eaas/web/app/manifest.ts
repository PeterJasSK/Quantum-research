import type { MetadataRoute } from "next";

// EPIC 13 AC-9: PWA manifest served at /manifest.webmanifest, linked from
// metadata. Icons reuse the existing logo.png; theme matches the neon-cyan
// design tokens.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Q-EaaS — Quantum Entropy as a Service",
    short_name: "Q-EaaS",
    description:
      "Quantum-seeded randomness, seeds & post-quantum key material — with a live dice player.",
    start_url: "/",
    display: "standalone",
    background_color: "#01040b",
    theme_color: "#00aaff",
    icons: [
      {
        src: "/logo.png",
        sizes: "512x512",
        type: "image/png",
      },
    ],
  };
}
