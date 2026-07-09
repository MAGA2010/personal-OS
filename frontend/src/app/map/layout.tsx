import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "留学地图",
  description: "交互式美国留学专题地图 — 六大指标图层 + 学校POI探索",
};

export default function MapLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
