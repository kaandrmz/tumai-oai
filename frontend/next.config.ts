import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "cdn.shopify.com",
      },
      {
        protocol: "https",
        hostname: "via.placeholder.com",
      },
      {
        protocol: "http",
        hostname: "127.0.0.1",
      },
      {
        protocol: "https",
        hostname: "xfiiitzbdzaqiynnemdi.supabase.co",
      },
      {
        protocol: "https",
        hostname: "rjetsktbezdpgmlscodu.supabase.co",
      },
      {
        protocol: "https",
        hostname: "*",
      },
    ],
  },
};

export default nextConfig;
