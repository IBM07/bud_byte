import type { NextConfig } from "next";

// Server-side base URL of the BudByte API (Northflank in prod, localhost in dev).
const API_BASE_URL = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  // The api-client package ships TypeScript source.
  transpilePackages: ["@budbyte/api-client"],
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  // Browser calls go to /api/* on the same origin, so auth cookies stay first-party.
  rewrites() {
    return [{ source: "/api/:path*", destination: `${API_BASE_URL}/:path*` }];
  },
  poweredByHeader: false,
};

export default nextConfig;
