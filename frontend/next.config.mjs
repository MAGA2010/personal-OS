/** @type {import(''next'').NextConfig} */
const nextConfig = {
  // Render Web Service runs the full Next.js app (pages + BFF).
  // data/preview/ is no longer read at runtime — Supabase Postgres is.
  images: { unoptimized: true },
  experimental: {
    typedRoutes: false,
  },
};

export default nextConfig;
