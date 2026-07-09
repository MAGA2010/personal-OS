import type { Metadata, Viewport } from "next";
import "./globals.css";

// ── SEO / Metadata ───────────────────────────────────────────────────────────

export const metadata: Metadata = {
  title: {
    default: "留学地图 | PathOS",
    template: "%s | PathOS"
  },
  description:
    "PathOS — 面向中国家庭的美国留学咨询平台。交互式地图、六大核心指标、学校 POI 探索，从数据出发找到最适合您孩子的大学。",
  keywords: [
    "留学地图",
    "美国大学",
    "中国家庭留学",
    "PathOS",
    "choropleth",
    "选校",
    "US universities",
    "study abroad",
    "Chinese students"
  ],
  authors: [{ name: "PathOS" }],
  robots: { index: true, follow: true },
  openGraph: {
    title: "留学地图 | PathOS",
    description:
      "面向中国家庭的美国留学咨询平台。交互式地图、六大核心指标、学校 POI 探索。",
    type: "website",
    locale: "zh_CN",
    siteName: "PathOS"
    // TODO: Set url and images when deployed
  },
  twitter: {
    card: "summary_large_image"
    // TODO: Set twitter:site and twitter:image when social accounts are live
  },
  metadataBase: new URL(
    // TODO: Replace with production URL once deployed (e.g. "https://pathos.app")
    "http://localhost:3000"
  )
};

// ── Viewport ──────────────────────────────────────────────────────────────────

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#f6f3ed" // paper
};

// ── Root Layout ───────────────────────────────────────────────────────────────

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-paper text-ink antialiased">
        {/* Skip-to-content for keyboard users */}
        {/* eslint-disable-next-line jsx-a11y/anchor-is-valid */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-cobalt focus:px-4 focus:py-2 focus:text-panel focus:no-underline focus:outline-none"
        >
          跳至主要内容
        </a>

        <div id="main-content" className="flex min-h-screen flex-col">
          {children}
        </div>

        {/*
          ── Global providers placeholder ──────────────────────────────────

          TODO: When ready, wrap children with:
            - Supabase session provider (auth)
            - React Query / TanStack Query provider (server-state caching)
            - Analytics provider (Vercel Analytics / Plausible / etc.)

          Example shape expected:
            <Providers>
              <AuthProvider>      // session from @supabase/ssr
                <QueryProvider>   // QueryClientProvider
                  <AnalyticsProvider>
                    {children}
                  </AnalyticsProvider>
                </QueryProvider>
              </AuthProvider>
            </Providers>
        */}
      </body>
    </html>
  );
}
