"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Bookmark, Brain, Check, DollarSign, GraduationCap, Map, Percent, Shield, Sparkles, Target, TrendingUp, Users } from "lucide-react";
import { ProductJourney } from "@/components/ProductJourney";
import universityData from "@/data/universities.json";
import regionMetrics from "@/data/region-metrics.json";

const STORAGE_KEY = "pathos_portfolio";

type DimensionKey = "budget" | "rank" | "safety" | "employment" | "community" | "admission";

type StudentInputs = Record<DimensionKey, number>;

type PortfolioItem = { id: string; addedAt: string };

const DIMENSIONS: Array<{ key: DimensionKey; label: string; helper: string; icon: typeof Target; studentHint: string }> = [
  { key: "budget", label: "预算适配", helper: "费用越低、越接近预算越高分", icon: DollarSign, studentHint: "你的预算承受百分比" },
  { key: "rank", label: "排名目标", helper: "学校声誉与排名梯度", icon: Target, studentHint: "你希望冲刺的排名百分位" },
  { key: "safety", label: "安全要求", helper: "城市安全与家长安心度", icon: Shield, studentHint: "你对安全的最低要求" },
  { key: "employment", label: "就业导向", helper: "州就业环境与学校职业认可", icon: TrendingUp, studentHint: "你对就业结果的期待" },
  { key: "community", label: "华人社区", helper: "华人生活便利与支持网络", icon: Users, studentHint: "你需要的社区支持度" },
  { key: "admission", label: "录取友好", helper: "录取难度越友好越高分", icon: GraduationCap, studentHint: "你能接受的录取难度" },
];

const DEFAULT_STUDENT: StudentInputs = { budget: 72, rank: 76, safety: 68, employment: 72, community: 60, admission: 55 };
const DEFAULT_WEIGHTS: StudentInputs = { budget: 20, rank: 20, safety: 18, employment: 18, community: 12, admission: 12 };
const TIER_SCORE: Record<string, number> = { top20: 96, top50: 82, top100: 66, other: 48 };
const COMMUNITY_SCORE: Record<string, number> = { high: 88, medium: 62, low: 36 };
const clamp = (value: number) => Math.max(0, Math.min(100, Math.round(value)));
const formatRmb = (value: number) => "¥" + Math.round(value / 10000) + "万";

function getMetricMap(metricId: string) {
  const records = ((regionMetrics as any).records ?? (regionMetrics as any).metrics ?? []) as any[];
  return records.reduce<Record<string, number>>((acc, item) => {
    if (item.metricId === metricId && item.granularity === "state") acc[item.fipsCode] = Math.round(Number(item.value ?? 0.5) * 100);
    return acc;
  }, {});
}

function schoolPercentages(university: any, maps: Record<string, Record<string, number>>): StudentInputs {
  const budget = clamp(100 - ((university.annualCostRmb ?? 620000) - 320000) / 5000);
  const rank = clamp(university.numericRank ? 100 - (Number(university.numericRank) - 1) * 1.35 : TIER_SCORE[university.rankingTier] ?? 50);
  const safety = clamp(university.safetyScore ?? maps.safety[university.stateFips] ?? 60);
  const employment = clamp((maps.employment[university.stateFips] ?? 62) * 0.65 + (university.recognitionScore ?? 70) * 0.35);
  const community = clamp(COMMUNITY_SCORE[university.chineseCommunity] ?? maps.chinese_population[university.stateFips] ?? 50);
  const admission = clamp(university.admissionRate ? Math.min(100, Number(university.admissionRate) * 2.4) : 105 - rank * 0.75);
  return { budget, rank, safety, employment, community, admission };
}

function matchScore(student: StudentInputs, weights: StudentInputs, school: StudentInputs) {
  const totalWeight = DIMENSIONS.reduce((sum, dim) => sum + weights[dim.key], 0) || 1;
  const weighted = DIMENSIONS.reduce((sum, dim) => {
    const gap = Math.abs(student[dim.key] - school[dim.key]);
    return sum + Math.max(0, 100 - gap) * weights[dim.key];
  }, 0);
  return clamp(weighted / totalWeight);
}

function saveToPortfolio(university: any) {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const items = raw ? (JSON.parse(raw) as PortfolioItem[]) : [];
    if (items.some((item) => item.id === university.id)) return false;
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...items, { id: university.id, addedAt: new Date().toISOString().split("T")[0] }]));
    return true;
  } catch {
    return false;
  }
}

export default function SmartMatchPage() {
  const universities = (universityData as any).universities as any[];
  const maps = useMemo(() => ({ safety: getMetricMap("safety"), employment: getMetricMap("employment"), chinese_population: getMetricMap("chinese_population") }), []);
  const [student, setStudent] = useState<StudentInputs>(DEFAULT_STUDENT);
  const [weights, setWeights] = useState<StudentInputs>(DEFAULT_WEIGHTS);
  const [addedId, setAddedId] = useState<string | null>(null);

  const matches = useMemo(() => universities.map((university) => {
    const school = schoolPercentages(university, maps);
    return { ...university, school, match: matchScore(student, weights, school) };
  }).sort((a, b) => b.match - a.match).slice(0, 18), [maps, student, universities, weights]);

  const averageTarget = Math.round(DIMENSIONS.reduce((sum, dim) => sum + student[dim.key], 0) / DIMENSIONS.length);
  const totalWeight = DIMENSIONS.reduce((sum, dim) => sum + weights[dim.key], 0);

  return (
    <div className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(35,118,107,0.12),transparent_34%),linear-gradient(180deg,#f6f3ed_0%,#fffaf1_58%,#f6f3ed_100%)]">
      <header className="border-b border-line/50 bg-panel/80 px-5 py-5 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-ink text-panel shadow-lg shadow-ink/10"><Sparkles size={21} /></div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cobalt/70">Self-service quiz</p>
            <h1 className="text-xl font-semibold tracking-tight text-ink">自主测验：拉取你的百分比与权重</h1>
            <p className="mt-1 text-sm text-ink/55">学生先定义自己的六维百分比，再与每所学校的数据百分比做匹配。</p>
          </div>
          <Link href="/assessment" className="ml-auto inline-flex items-center gap-2 rounded-full bg-ink px-4 py-2 text-xs font-semibold text-panel shadow-sm transition hover:-translate-y-0.5 hover:bg-ink/90"><Brain size={14} /> 切到 AI 学校评估</Link>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 pt-5"><ProductJourney active="match" compact /></div>

      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-6 lg:grid-cols-[360px_1fr]">
        <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <section className="rounded-[1.6rem] border border-white/70 bg-white/80 p-5 shadow-xl shadow-ink/5 backdrop-blur">
            <div className="mb-5 flex items-start justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-jade/80">Student pull</p>
                <h2 className="mt-1 text-base font-semibold text-ink">学生百分比</h2>
                <p className="mt-1 text-xs leading-relaxed text-ink/50">不是 AI 自动替你判断，而是由学生主动设定目标强度。</p>
              </div>
              <div className="rounded-full bg-jade/10 px-3 py-1 text-xs font-bold text-jade">均值 {averageTarget}%</div>
            </div>

            <div className="space-y-4">
              {DIMENSIONS.map((dim) => {
                const Icon = dim.icon;
                return (
                  <div key={dim.key} className="rounded-2xl border border-line/40 bg-panel/55 p-3">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="grid h-7 w-7 place-items-center rounded-xl bg-white text-ink/60 shadow-sm"><Icon size={14} /></span>
                        <div><div className="text-sm font-semibold text-ink">{dim.label}</div><div className="text-[11px] text-ink/42">{dim.studentHint}</div></div>
                      </div>
                      <span className="tabular-nums text-sm font-bold text-cobalt">{student[dim.key]}%</span>
                    </div>
                    <input type="range" min={0} max={100} value={student[dim.key]} onChange={(event) => setStudent((prev) => ({ ...prev, [dim.key]: Number(event.target.value) }))} className="h-2 w-full accent-cobalt" aria-label={dim.label + "学生百分比"} />
                    <div className="mt-3 flex items-center justify-between gap-3">
                      <span className="text-[11px] text-ink/42">权重</span>
                      <input type="range" min={0} max={40} value={weights[dim.key]} onChange={(event) => setWeights((prev) => ({ ...prev, [dim.key]: Number(event.target.value) }))} className="h-2 flex-1 accent-jade" aria-label={dim.label + "权重"} />
                      <span className="w-8 text-right text-[11px] font-semibold text-jade">{weights[dim.key]}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="rounded-[1.4rem] border border-line/50 bg-ink p-5 text-panel shadow-xl shadow-ink/10">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-panel/45">Parallel structure</p>
            <h3 className="mt-2 text-base font-semibold">自主测验只负责匹配</h3>
            <div className="mt-4 space-y-3 text-sm text-panel/70">
              <p><span className="font-semibold text-panel">自主测验：</span>学生控制百分比和权重，本页只做学校百分比匹配。</p>
              <p><span className="font-semibold text-panel">AI 测验：</span>学校评估与清单分析走 /api/ai/analyze，可接入外部 AI。</p>
            </div>
            <div className="mt-4 rounded-2xl bg-panel/10 p-3 text-xs text-panel/55">当前总权重：{totalWeight}。权重为 0 的维度不会参与综合匹配。</div>
          </section>
        </aside>

        <section className="space-y-4">
          <div className="rounded-[1.7rem] border border-white/70 bg-white/80 p-5 shadow-xl shadow-ink/5 backdrop-blur">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-persimmon/75">School percentages</p>
                <h2 className="mt-1 text-xl font-semibold text-ink">学校百分比匹配结果</h2>
                <p className="mt-1 text-sm text-ink/50">展示学校六维数据和学生目标之间的距离，不混入 AI 结论。</p>
              </div>
              <div className="flex items-center gap-2 rounded-full border border-line/50 bg-panel px-3 py-1.5 text-xs text-ink/55"><Percent size={14} /> Top {matches.length} / {universities.length}</div>
            </div>
          </div>

          <div className="grid gap-3">
            {matches.map((university, index) => {
              const tone = university.match >= 86 ? "text-jade" : university.match >= 72 ? "text-cobalt" : "text-persimmon";
              return (
                <article key={university.id} className="group overflow-hidden rounded-[1.5rem] border border-line/45 bg-white/90 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-cobalt/30 hover:shadow-xl hover:shadow-ink/8">
                  <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-start">
                    <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-ink text-sm font-bold text-panel">{index + 1}</div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2"><h3 className="text-base font-semibold text-ink">{university.chineseName}</h3><span className="text-xs text-ink/38">{university.name}</span><span className="rounded-full bg-cobalt/8 px-2 py-0.5 text-[11px] font-semibold text-cobalt">{university.rankingTier}</span></div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-ink/48"><span>{university.city}, {university.state}</span><span>·</span><span>{formatRmb(university.annualCostRmb)}/年</span><span>·</span><span>安全 {university.safetyScore ?? "-"}/100</span></div>
                      <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                        {DIMENSIONS.map((dim) => {
                          const schoolValue = university.school[dim.key];
                          const studentValue = student[dim.key];
                          const gap = Math.abs(schoolValue - studentValue);
                          return (
                            <div key={dim.key} className="rounded-2xl bg-paper/80 p-2.5">
                              <div className="flex items-center justify-between text-[11px]"><span className="font-medium text-ink/60">{dim.label}</span><span className="font-semibold text-ink">校 {schoolValue}% / 我 {studentValue}%</span></div>
                              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-line/50"><div className="h-full rounded-full bg-cobalt" style={{ width: schoolValue + "%" }} /></div>
                              <div className="mt-1 text-[10px] text-ink/38">差距 {gap} · {dim.helper}</div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                    <div className="flex shrink-0 flex-row items-center justify-between gap-3 sm:w-28 sm:flex-col sm:items-end">
                      <div className="text-right"><div className={"text-3xl font-black tabular-nums " + tone}>{university.match}%</div><div className="text-[11px] text-ink/40">匹配度</div></div>
                      <div className="flex gap-2 sm:flex-col">
                        <button onClick={() => { saveToPortfolio(university); setAddedId(university.id); setTimeout(() => setAddedId(null), 1800); }} className="inline-flex items-center justify-center gap-1.5 rounded-full border border-line/60 px-3 py-1.5 text-xs font-semibold text-ink/62 transition hover:border-cobalt/40 hover:bg-cobalt/8 hover:text-cobalt">{addedId === university.id ? <Check size={13} /> : <Bookmark size={13} />}{addedId === university.id ? "已加入" : "加清单"}</button>
                        <Link href={"/map?school=" + university.id} className="inline-flex items-center justify-center gap-1.5 rounded-full bg-ink px-3 py-1.5 text-xs font-semibold text-panel transition hover:bg-ink/90"><Map size={13} /> 地图</Link>
                      </div>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </main>
    </div>
  );
}
