import Link from "next/link";
import type { Metadata } from "next";
import { Compass, Map, ArrowRight } from "lucide-react";

export const metadata: Metadata = {
  title: "PathOS — 面向中国家庭的留学地图",
  description: "PathOS 是面向中国家庭的留学数据平台，交互式地图 + 六大指标探索。"
};

export default function HomePage() {
  return (
    <main className="min-h-screen bg-paper flex flex-col items-center justify-center px-4 text-center">
      <div className="grid h-14 w-14 place-items-center rounded-lg bg-ink text-panel mb-6">
        <Compass aria-hidden="true" size={28} />
      </div>
      <h1 className="text-3xl font-bold text-ink sm:text-4xl">PathOS</h1>
      <p className="mt-2 max-w-md text-base text-ink/62 leading-relaxed">
        面向中国家庭的留学数据平台。交互式等值线地图 + 六大核心指标探索。
      </p>

      <div className="mt-8 flex flex-wrap gap-4">
        <Link
          href="/map"
          className="inline-flex items-center gap-2 rounded-lg bg-ink px-5 py-3 text-sm font-semibold text-panel shadow-sm transition hover:bg-jade"
        >
          <Map size={18} />
          探索地图
          <ArrowRight size={16} />
        </Link>
      </div>

      <footer className="mt-16 text-xs text-ink/36">
        PathOS · 面向中国家庭的留学数据平台 · MVP 骨架阶段
      </footer>
    </main>
  );
}
