"use client";
import { useState, useMemo } from "react";
import universityData from "@/data/universities.json";
import rankingData from "@/data/university-rankings.json";
import regionMetrics from "@/data/region-metrics.json";
import { Sparkles, Target, DollarSign, Shield, TrendingUp, Users, GraduationCap, ChevronDown, ChevronUp, Map, Bookmark } from "lucide-react";
import Link from "next/link";

const TIER_S: Record<string, number> = { top20: 1.0, top50: 0.7, top100: 0.4, other: 0.1 };
const COMM_S: Record<string, number> = { high: 1.0, medium: 0.6, low: 0.2 };
const WT = [0, 0, 0.25, 0.5, 0.75, 1.0];
const DIM = ["费用", "排名", "安全", "就业", "华人", "录取"];
const LABELS_5 = ["不在乎", "较低", "中等", "重视", "非常重视"];
const fmt = (n: number) => "¥" + (n / 10000).toFixed(0) + "万";

function livingLabel(rent: number | undefined): string {
  if (!rent) return "标准型";
  return rent > 10000 ? "舒适型" : rent > 5000 ? "标准型" : "节俭型";
}

export default function SmartMatchPage() {
  const all = (universityData as any).universities as any[];
  const empMap: Record<string, number> = {};
  for (const r of ((regionMetrics as any).records ?? [])) {
    if (r.metricId === "employment") empMap[r.fipsCode] = r.value;
  }

  const [prefs, setPrefs] = useState({
    budget: 550000, rank: 3, safety: 3, employ: 3, community: 3, admit: 3,
  });

  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggle = (id: string) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const matches = useMemo(() => {
    return all
      .map((u: any) => {
        const c = u.annualCostRmb;
        const maxB = prefs.budget;
        const costR = maxB > 0
          ? (c <= maxB ? 0.8 + 0.2 * (1 - c / maxB) : Math.max(0, 1 - (c / maxB - 1) * 3))
          : 1;
        const rankR = TIER_S[u.rankingTier as string] ?? 0.1;
        const safeR = u.safetyScore / 100;
        const empR = empMap[u.stateFips as string] ?? 0.5;
        const commR = COMM_S[u.chineseCommunity as string] ?? 0.3;
        const admR = Math.min(1, u.admissionRate / 40);
        const scores = [costR, rankR, safeR, empR, commR, admR];
        const w = [prefs.budget, prefs.rank, prefs.safety, prefs.employ, prefs.community, prefs.admit].map(
          (v) => WT[v] ?? 0
        );
        const tw = w.reduce((a: number, b: number) => a + b, 0);
        const match =
          tw > 0
            ? Math.round((scores.reduce((s: number, sc: number, i: number) => s + sc * w[i], 0) / tw) * 100)
            : 0;
        return { ...u, match, scores };
      })
      .sort((a: any, b: any) => b.match - a.match);
  }, [prefs]);

  const sliders = [
    { key: "budget", label: "预算上限", min: 350000, max: 750000, step: 50000, icon: DollarSign, fmt: (v: number) => "¥" + (v / 10000).toFixed(0) + "万" },
    { key: "rank", label: "排名重视", min: 1, max: 5, step: 1, icon: Target },
    { key: "safety", label: "安全要求", min: 1, max: 5, step: 1, icon: Shield },
    { key: "employ", label: "就业重视", min: 1, max: 5, step: 1, icon: TrendingUp },
    { key: "community", label: "华人社区", min: 1, max: 5, step: 1, icon: Users },
    { key: "admit", label: "录取难度", min: 1, max: 5, step: 1, icon: GraduationCap },
  ];

  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-line bg-panel px-5 py-3">
        <div className="mx-auto flex max-w-6xl items-center gap-3">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-ink text-panel">
            <Sparkles size={18} />
          </div>
          <div>
            <h1 className="text-base font-semibold text-ink">② 智能匹配</h1>
            <p className="text-xs text-ink/52">六大维度综合评估，你的专属选校优先级排名</p>
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 lg:flex-row">
        {/* Preferences Sidebar */}
        <div className="w-full shrink-0 lg:w-72">
          <div className="rounded-xl border border-line/50 bg-white/90 p-4 shadow-sm sticky top-20">
            <h2 className="mb-3 flex items-center gap-1.5 text-xs font-semibold text-ink/60">
              <Target size={14} />我的偏好
            </h2>
            <div className="space-y-4">
              {sliders.map((s) => {
                const val = (prefs as any)[s.key];
                const Icon = s.icon;
                const isNumeric = s.step >= 10000;
                return (
                  <div key={s.key}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="flex items-center gap-1 text-ink/60">
                        <Icon size={11} />
                        {s.label}
                      </span>
                      <span className="font-medium text-ink/80 tabular-nums">
                        {isNumeric && s.fmt ? s.fmt(val) : LABELS_5[val - 1]}
                      </span>
                    </div>
                    <input
                      type="range"
                      min={s.min}
                      max={s.max}
                      step={s.step}
                      value={val}
                      onChange={(e) =>
                        setPrefs((p) => ({ ...p, [s.key]: Number(e.target.value) }))
                      }
                      className="w-full h-1.5 rounded-full appearance-none bg-ink/10 cursor-pointer accent-ink"
                    />
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Results */}
        <div className="min-w-0 flex-1">
          <p className="mb-3 text-xs text-ink/40">{matches.length} 所大学匹配结果</p>
          <div className="space-y-2.5">
            {matches.map((u: any, i: number) => {
              const scoreColor =
                u.match >= 80 ? "text-jade" : u.match >= 60 ? "text-persimmon" : "text-ink/40";
              const barColor =
                u.match >= 80 ? "bg-jade" : u.match >= 60 ? "bg-persimmon" : "bg-ink/20";
              const isOpen = expanded[u.id] ?? false;
              return (
                <div
                  key={u.id}
                  className="rounded-xl border border-line/40 bg-white/90 px-4 py-3 shadow-sm transition hover:shadow-md"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] font-medium text-ink/30">#{i + 1}</span>
                        <span className="text-sm font-semibold text-ink truncate">
                          {u.chineseName}
                        </span>
                      </div>
                      <p className="text-[11px] text-ink/50 truncate">
                        {u.name} · {fmt(u.annualCostRmb)}/年 · {u.rankingTier}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className={"text-lg font-bold leading-tight " + scoreColor}>
                        {u.match}%
                      </div>
                      <div className="text-[10px] text-ink/30">匹配</div>
                    </div>
                  </div>
                  <div className="mt-2 h-1.5 rounded-full bg-ink/6 overflow-hidden">
                    <div
                      className={"h-full rounded-full " + barColor}
                      style={{ width: u.match + "%" }}
                    />
                  </div>
                  {/* Dimension sub-scores */}
                  <div className="mt-2 grid grid-cols-6 gap-1">
                    {DIM.map((dim, di) => (
                      <div key={di} className="text-center">
                        <div className="text-[9px] text-ink/30">{dim}</div>
                        <div className="mt-0.5 h-1 rounded-full bg-ink/6 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-cobalt"
                            style={{ width: Math.max(3, u.scores[di] * 100) + "%" }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                  {/* Expand button */}
                  <button
                    onClick={() => toggle(u.id)}
                    className="mt-2.5 flex items-center gap-1 text-[10px] text-ink/40 hover:text-ink/70 transition-colors"
                  >
                    {isOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    {isOpen ? "收起详情" : "查看费用与操作"}
                  </button>
                  {/* Expandable detail */}
                  {isOpen && (
                    <div className="mt-3 space-y-2 border-t border-line/30 pt-3">
                      {/* Cost breakdown */}
                      <div className="grid grid-cols-2 gap-2 text-[11px]">
                        <div className="rounded-md bg-ink/4 px-2 py-1.5">
                          <span className="text-ink/40">总费用/年</span>
                          <div className="font-semibold text-ink/80">{fmt(u.annualCostRmb)}</div>
                        </div>
                        <div className="rounded-md bg-ink/4 px-2 py-1.5">
                          <span className="text-ink/40">生活费档</span>
                          <div className="font-semibold text-ink/80">{livingLabel(u.nearby?.avgRentRmb)}</div>
                        </div>
                        <div className="rounded-md bg-ink/4 px-2 py-1.5">
                          <span className="text-ink/40">安全评分</span>
                          <div className="font-semibold text-ink/80">{u.safetyScore}分</div>
                        </div>
                        <div className="rounded-md bg-ink/4 px-2 py-1.5">
                          <span className="text-ink/40">录取率</span>
                          <div className="font-semibold text-ink/80">{u.admissionRate}%</div>
                        </div>
                      </div>
                      {/* Actions */}
                      <div className="flex gap-2 pt-1">
                        <Link
                          href="/map"
                          className="inline-flex items-center gap-1 rounded-md border border-cobalt/30 bg-cobalt/5 px-3 py-1 text-[11px] font-medium text-cobalt hover:bg-cobalt/10 transition"
                        >
                          <Map size={11} /> 查看地图
                        </Link>
                        <Link
                          href="/portfolio"
                          className="inline-flex items-center gap-1 rounded-md border border-jade/30 bg-jade/5 px-3 py-1 text-[11px] font-medium text-jade hover:bg-jade/10 transition"
                        >
                          <Bookmark size={11} /> 加入清单
                        </Link>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}

