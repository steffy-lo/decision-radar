import type { NextConfig } from "next";
import { resolve } from "node:path";

const nextConfig: NextConfig = {
  outputFileTracingRoot: resolve(import.meta.dirname, "../.."),
  outputFileTracingIncludes: {
    "/api/v1/projects/*/fixture": ["../../fixtures/vendor-delay.json"],
  },
};

export default nextConfig;
