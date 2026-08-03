/** @type {import('next').NextConfig} */
const nextConfig = {
  // Render Web Service runs the full Next.js app (pages + BFF).
  // data/preview/ is no longer read at runtime — Supabase Postgres is.
  images: { unoptimized: true },
  experimental: {
    typedRoutes: false,
  },

  // Security headers (production only — Render runs `next start`).
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-XSS-Protection", value: "1; mode=block" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains",
          },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: https: blob: https://*.basemaps.cartocdn.com",
              "font-src 'self'",
              "connect-src 'self' https://hezccqkbqictwysxkonc.supabase.co https://api.deepseek.com https://*.basemaps.cartocdn.com",
              "worker-src 'self' blob:",
              "frame-src 'none'",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

export default nextConfig;