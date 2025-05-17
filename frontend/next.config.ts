import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  reactStrictMode: true,
  images: {unoptimized: true }, // Disable image optimization for static export
};

export default nextConfig;
