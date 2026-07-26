import type { NextConfig } from "next";

// D-web: static export satisfies the "static HTML page" AC. No `next export`
// step exists on Next 16 -- `next build` alone emits web/out/ when
// output: 'export' is set.
const repoBasePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export",
  basePath: repoBasePath,
  assetPrefix: repoBasePath,
  images: {
    unoptimized: true,
  },
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
