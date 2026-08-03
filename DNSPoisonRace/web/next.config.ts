import type { NextConfig } from "next";

// P6: static export satisfies the "static HTML page" AC (AC-6.6). No `next export`
// step exists on Next 16 -- `next build` alone emits web/out/ when
// output: 'export' is set. basePath/assetPrefix from NEXT_PUBLIC_BASE_PATH lets
// the bundle deploy under a GitHub-Pages subpath (epic OQ-6).
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
