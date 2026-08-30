import type { NextConfig } from "next";

const staticExport = process.env.LOOP_STATIC === "1";

const nextConfig: NextConfig = {
  output: staticExport ? "export" : undefined,
  images: staticExport ? { unoptimized: true } : undefined,
};

if (!staticExport) {
  nextConfig.rewrites = async () => {
    const api = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";
    return [
      { source: "/backend/:path*", destination: `${api}/:path*` },
      { source: "/shop", destination: "/shop/index.html" },
    ];
  };
}

export default nextConfig;
