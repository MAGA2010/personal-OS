import Link from "next/link";
import type { Metadata } from "next";
import { Compass, Map, ArrowRight, Trophy, TrendingUp } from "lucide-react";

export const metadata: Metadata = {
  title: "PathOS — 面向中国家庭的留学选校决策平台",
  description: "PathOS 是一款留学数据平台。交互式地图 + 六大核心指标 + 智能选校匹配。",
};

const METRICS = [
  { id: "income",           label: "收入水平",   color: "bg-emerald-500/80",   bar: 72, desc: "区域家庭中位年收入" },
  { id: "safety",           label: "安全系数",   color: "bg-blue-500/80",      bar: 55, desc: "基于暴力犯罪率的倒数" },
  { id: "employment",       label: "就业指数",   color: "bg-teal-500/80",      bar: 78, desc: "BLS各州就业率数据" },
  { id: "cost",             label: "留学成本",   color: "bg-orange-500/80",    bar: 65, desc: "学费+生活费综合评估" },
  { id: "admission_rate",   label: "录取率",     color: "bg-red-500/80",       bar: 35, desc: "大学平均录取率" },
  { id: "chinese_population",label: "华人水平",  color: "bg-yellow-500/80",    bar: 60, desc: "华裔人口占比" },
];

export default function HomePage() {
  return (
    <div className="flex-1 bg-paper">
      <main className="mx-auto max-w-5xl px-4 py-16 sm:py-24">
        {/* Hero */}
        <div className="text-center">
          <div className="mx-auto mb-6 grid h-16 w-16 place-items-center rounded-2xl bg-ink text-panel shadow-lg">
            <Compass size={32} />
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-ink sm:text-5xl">PathOS</h1>
          <p className="mx-auto mt-3 max-w-xl text-base leading-relaxed text-ink/60 sm:text-lg">
            面向中国家庭的留学选校决策平台。<br />
            交互式地图 · 六大核心指标 · 智能匹配
          </p>
        </div>

        {/* 6 Metric Cards */}
        <div className="mt-12 grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4">
          {METRICS.map((m) => (
            <div key={m.id} className="rounded-xl border border-line/50 bg-white/90 px-4 py-3.5 shadow-sm transition hover:shadow-md hover:border-line">
              <div className="flex items-center gap-2">
                <div className={"h-2.5 w-2.5 rounded-full " + m.color} />
                <span className="text-sm font-medium text-ink/80">{m.label}</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-ink/6 overflow-hidden">
                <div className={"h-full rounded-full " + m.color + " transition-all"} style={{ width: m.bar + "%" }} />
              </div>
              <p className="mt-1.5 text-[11px] text-ink/40">{m.desc}</p>
            </div>
          ))}
        </div>

        {/* Stats */}
        <div className="mt-10 text-center">
          <p className="text-sm text-ink/48">
            <span className="font-semibold text-ink/70">40</span> 所大学 ·
            <span className="font-semibold text-ink/70"> 18</span> 个州 ·
            <span className="font-semibold text-ink/70"> 6</span> 大核心指标 ·
            覆盖全美主要留学目的地
          </p>
        </div>

        {/* CTA Buttons */}
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link href="/match">
            <Map size={18} />
            探索地图
            <ArrowRight size={16} />
          </Link>
          <Link href="/map/rankings"
            className="inline-flex items-center gap-2 rounded-lg border border-line/70 bg-white px-5 py-3 text-sm font-semibold text-ink/70 shadow-sm transition hover:border-ink/20 active:scale-[0.97]">
            <Trophy size={18} />
            查看排名
          </Link>
          <Link href="/calculator" className="inline-flex items-center gap-2 rounded-lg border border-jade/30 bg-jade/5 px-5 py-3 text-sm font-semibold text-jade shadow-sm transition hover:bg-jade/10 active:scale-[0.97]"><TrendingUp size={18} /> 智能选校
          </Link>
        </div>

        {/* Footer */}
        <footer className="mt-16 text-center text-xs text-ink/30">
          PathOS — 面向中国家庭的留学选校决策平台 · MVP 阶段
        </footer>
      </main>
    </div>
  );
}

