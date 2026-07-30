import type { Metadata, Viewport } from "next";
import "./globals.css";
import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";
import { DataSourceProvider } from "@/services/data-source-provider";
import { THEME_INIT_SCRIPT } from "@/lib/theme";

export const metadata: Metadata = {
  title: { default: "PathOS — 面向中国家庭的留学选校决策平台", template: "%s | PathOS" },
  description: "PathOS 提供留学地图、自主测验、AI 学校评估和 AI 清单分析，帮助中国家庭做更理性的美国本科/研究生选校决策。",
  keywords: ["留学地图", "美国大学", "中国家庭留学", "PathOS", "选校"],
  authors: [{ name: "PathOS" }], robots: { index: true, follow: true },
  openGraph: { title: "PathOS — 留学选校决策平台", description: "面向中国家庭的美国留学咨询平台。交互式地图、自主测验、AI 学校评估和 AI 清单分析。", type: "website", locale: "zh_CN", siteName: "PathOS" },
  twitter: { card: "summary_large_image" },
  metadataBase: new URL("http://localhost:3000")
};
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // `themeColor` is overridden at runtime by the theme controller —
  // these are just initial hints for the browser chrome.
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f3ed" },
    { media: "(prefers-color-scheme: dark)",  color: "#11161a" },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        {/* No-flash theme bootstrap — runs before React mounts and
            * synchronously* writes the correct class / data-theme /
            * color-scheme on <html> based on localStorage. Without
            * this, a dark-mode reload briefly paints the light
            * theme before React hydrates. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="min-h-screen bg-surface-base text-text-primary antialiased">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-control focus:bg-cobalt focus:px-4 focus:py-2 focus:text-paper focus:no-underline focus:outline-none"
        >
          跳至主要内容
        </a>
        <NavBar />
        <DataSourceProvider>
          <div id="main-content" className="flex min-h-[calc(100vh-3.5rem)] flex-col">
            {children}
          </div>
        </DataSourceProvider>
        <Footer />
      </body>
    </html>
  );
}