import type { Metadata, Viewport } from "next";
import "./globals.css";
import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: { default: "PathOS — 面向中国家庭的留学选校决策平台", template: "%s | PathOS" },
  description: "PathOS 把学生画像、智能匹配、留学地图和选校清单串成一条连续的选校决策路径。面向中国家庭的美国本科/研究生选校平台。",
  keywords: ["留学地图", "美国大学", "中国家庭留学", "PathOS", "选校"],
  authors: [{ name: "PathOS" }], robots: { index: true, follow: true },
  openGraph: { title: "PathOS — 留学选校决策平台", description: "面向中国家庭的美国留学咨询平台。交互式地图、智能匹配、选校清单。", type: "website", locale: "zh_CN", siteName: "PathOS" },
  twitter: { card: "summary_large_image" },
  metadataBase: new URL("http://localhost:3000")
};
export const viewport = { width: "device-width", initialScale: 1, themeColor: "#f6f3ed" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-paper text-ink antialiased">
        <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-cobalt focus:px-4 focus:py-2 focus:text-panel focus:no-underline focus:outline-none">跳至主要内容</a>
        <NavBar />
        <div id="main-content" className="flex min-h-[calc(100vh-3.5rem)] flex-col">{children}</div>
        <Footer />
      </body>
    </html>
  );
}