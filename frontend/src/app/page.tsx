import Link from "next/link";
import type { Metadata } from "next";
import { Compass, Map, Sparkles, ClipboardCheck, Bookmark, Newspaper, TrendingUp, ArrowRight, BarChart3, Globe2, GraduationCap } from "lucide-react";

export const metadata: Metadata = {
  title: "PathOS — 面向中国家庭的留学选校数据平台",
  description: "交互式留学地图、自主测验、AI 学校评估与 AI 清单分析。数据驱动，让选校更理性。",
};

const FEATURES = [
  {
    title: "留学地图",
    desc: "安全系数 · 就业指数 · 留学成本 · 华人水平 · 收入水平 · 录取率，六大指标交互式可视化",
    href: "/map",
    icon: Map,
    tags: ["可视化", "六大指标"],
    color: "from-emerald-500 to-teal-600",
  },
  {
    title: "自主测验",
    desc: "学生自主拉取六维百分比和权重，再匹配学校的数据百分比",
    href: "/match",
    icon: Sparkles,
    tags: ["自主权重", "百分比匹配"],
    color: "from-violet-500 to-purple-600",
  },
  {
    title: "AI 学校评估",
    desc: "融入 AI 分析接口，对学生画像与目标学校做风险体检",
    href: "/assessment",
    icon: ClipboardCheck,
    tags: ["AI 测验", "风险体检"],
    color: "from-amber-500 to-orange-600",
  },
  {
    title: "AI 清单分析",
    desc: "把候选学校清单交给 AI，分析冲刺、匹配、保底比例和家长追问点",
    href: "/portfolio",
    icon: Bookmark,
    tags: ["清单分析", "家庭讨论"],
    color: "from-blue-500 to-indigo-600",
  },
  {
    title: "排名对比",
    desc: "综合 US News、QS、THE 等排名体系，多维度交叉对比院校实力",
    href: "/match",
    icon: BarChart3,
    tags: ["交叉对比", "排名分析"],
    color: "from-rose-500 to-pink-600",
  },
  {
    title: "留学资讯",
    desc: "最新签证政策、申请动态、留学生活指南，一站式留学信息聚合",
    href: "/news",
    icon: Newspaper,
    tags: ["政策动态", "申请攻略"],
    color: "from-cyan-500 to-sky-600",
  },
];

export default function HomePage() {
  return (
    <div className="flex-1 bg-paper">
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-line/30">
        <div className="absolute inset-0 bg-gradient-to-br from-ink/3 via-transparent to-cobalt/5 pointer-events-none" />
        <div className="relative mx-auto max-w-5xl px-4 py-20 sm:py-28 text-center">
          <div className="mx-auto mb-6 grid h-16 w-16 place-items-center rounded-2xl bg-ink text-panel shadow-lg ring-1 ring-ink/10">
            <Compass size={30} />
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-ink sm:text-5xl">
            PathOS
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-base leading-relaxed text-ink/50 sm:text-lg">
            面向中国家庭的美国留学选校数据平台。<br />
            交互式地图 · 自主测验 · AI 测验
          </p>
          
          {/* Stats bar */}
          <div className="mt-8 flex flex-wrap justify-center gap-x-10 gap-y-3">
            <div className="text-center">
              <div className="text-2xl font-bold text-ink">40+</div>
              <div className="text-xs text-ink/40 mt-0.5">所美国大学</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-ink">18</div>
              <div className="text-xs text-ink/40 mt-0.5">个州覆盖</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-ink">6</div>
              <div className="text-xs text-ink/40 mt-0.5">大核心指标</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-ink">3</div>
              <div className="text-xs text-ink/40 mt-0.5">种评估维度</div>
            </div>
          </div>

          {/* Search / CTA */}
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link
              href="/map"
              className="inline-flex items-center gap-2 rounded-lg bg-ink px-6 py-3 text-sm font-semibold text-panel shadow transition hover:bg-ink/90 active:scale-[0.97]"
            >
              <Map size={18} />
              探索留学地图
            </Link>
            <Link
              href="/match"
              className="inline-flex items-center gap-2 rounded-lg border border-line/60 bg-white px-6 py-3 text-sm font-semibold text-ink/70 shadow-sm transition hover:border-ink/30 active:scale-[0.97]"
            >
              <Sparkles size={18} />
              开始自主测验
            </Link>
          </div>
        </div>
      </section>

      {/* Features Grid - Parallel tools */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
        <div className="text-center mb-10">
          <h2 className="text-xl font-semibold text-ink">选校工具箱</h2>
          <p className="mt-1.5 text-sm text-ink/40">所有工具平行开放，按需使用</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <Link
                key={f.href}
                href={f.href}
                className="group block rounded-xl border border-line/40 bg-white/90 p-5 shadow-sm transition hover:shadow-md hover:border-line/80 active:scale-[0.98]"
              >
                <div className="flex items-start gap-4">
                  <div className={"flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br text-white shadow-sm " + f.color}>
                    <Icon size={18} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold text-ink group-hover:text-ink/90 transition-colors">
                      {f.title}
                      <ArrowRight size={14} className="inline ml-1 opacity-0 group-hover:opacity-60 transition-all" />
                    </h3>
                    <p className="mt-1 text-xs leading-relaxed text-ink/50">{f.desc}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {f.tags.map((t) => (
                        <span key={t} className="rounded-full bg-ink/5 px-2 py-0.5 text-[10px] font-medium text-ink/40">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="border-t border-line/30 bg-ink/5">
        <div className="mx-auto max-w-2xl px-4 py-14 text-center">
          <GraduationCap size={28} className="mx-auto text-ink/30" />
          <h2 className="mt-3 text-lg font-semibold text-ink">不确定从哪里开始？</h2>
          <p className="mt-1 text-sm text-ink/50">先做自主测验，再用 AI 测验校验学校与清单风险</p>
          <div className="mt-5 flex justify-center gap-3">
            <Link
              href="/match"
              className="inline-flex items-center gap-2 rounded-lg bg-ink px-5 py-2.5 text-sm font-semibold text-panel shadow transition hover:bg-ink/90"
            >
              <ClipboardCheck size={16} />
              开始自主测验
            </Link>
          </div>
        </div>
      </section>

      <footer className="py-8 text-center text-xs text-ink/25">
        PathOS — 面向中国家庭的留学选校决策平台 · MVP
      </footer>
    </div>
  );
}
