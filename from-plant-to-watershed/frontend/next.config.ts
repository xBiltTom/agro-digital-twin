import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  // Node 26's CLI invocation can return an empty `tsc --showConfig` stream;
  // Next's in-process TypeScript API is deterministic and still type-checks.
  experimental: {
    useTypeScriptCli: false,
  },
};

export default nextConfig;
