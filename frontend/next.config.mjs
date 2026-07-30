/** @type {import('next').NextConfig} */
const nextConfig = {
  // PathOS uses dynamic BFF routes (`/api/pathos/preview`,
  // `/api/ai/*`) that rely on `request.url`, and `useSearchParams()`
  // for URL view-state sync. Both require a server runtime; the
  // static export mode (`output: 'export'`) was inherited from the
  // initial scaffold and is incompatible with these needs. The
  // `images.unoptimized` flag is preserved because we serve user-
  // uploaded logos / campus photos that don't go through Next's image
  // optimizer.
  images: { unoptimized: true },
  experimental: {
    typedRoutes: false,
    // The Preview adapter reads immutable JSON artifacts through node:fs.
    // Explicit tracing keeps those files inside Vercel's server functions.
    outputFileTracingIncludes: {
      "/api/pathos/preview": ["./data/preview/**/*"],
      "/api/ai/context": ["./data/preview/**/*"],
      "/api/ai/analyze": ["./data/preview/**/*"],
      "/university/[id]": ["./data/preview/**/*"]
    }
  }
};

export default nextConfig;
