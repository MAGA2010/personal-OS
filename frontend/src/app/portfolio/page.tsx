"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Bookmark, Brain, Download, Plus, Sparkles, Trash2, X } from "lucide-react";
import { SearchInput } from "@/components/shared/SearchInput";
import { useDataSource } from "@/services/data-source-provider";
import { useUniversitySummaries } from "@/hooks/use-data-source";

const STORAGE_KEY = "pathos_portfolio";

type PortfolioItem = { id: string; addedAt: string };
type AnalysisResult = {
  source: string;
  summary: string;
  portfolio: {
    reachCount: number | null;
    targetCount: number | null;
    safetyCount: number | null;
    averageFitScore: number | null;
    majorRisks: string[];
    parentQuestions: string[];
  };
  recommended: Array<{ id: string; name: string; chineseName: string; fitScore: number; tier: string; reasons: string[]; warnings: string[] }>;
  nextActions: string[];
};

function loadPortfolio(): PortfolioItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function savePortfolio(items: PortfolioItem[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {}
}

const tierLabel: Record<string, string> = { reach: "冲刺", target: "匹配", safety: "保底" };
const tierTone: Record<string, string> = { reach: "bg-persimmon/10 text-persimmon", target: "bg-cobalt/10 text-cobalt", safety: "bg-jade/10 text-jade" };

const LOCAL_AI_PORTFOLIO_DEMO: AnalysisResult = {
  source: "本地 Demo 示例",
  summary: "这是本地交互示例，用于展示 AI 清单分析的输出结构。它不会连接外部 AI，也不会推断任何学校的录取概率。",
  portfolio: {
    reachCount: null,
    targetCount: null,
    safetyCount: null,
    averageFitScore: null,
    majorRisks: ["学校组合仍需结合学生背景逐校核验。", "未报告或待审核字段不能用于形成录取结论。"],
    parentQuestions: ["预算上限是否包含住宿、保险与旅行费用？", "目标专业和申请年份是否已最终确认？"],
  },
  recommended: [],
  nextActions: ["补齐目标专业与申请年份。", "逐校核验语言、标化和专业要求。", "完成后再生成正式家庭讨论版本。"],
};

export default function PortfolioPage() {
  const dataSource = useDataSource();
  const summariesState = useUniversitySummaries(dataSource);
  const all = useMemo(
    () => (summariesState.state.status === "ready" ? (summariesState.state.data as unknown as any[]) : []),
    [summariesState.state],
  );
  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [query, setQuery] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  useEffect(() => setItems(loadPortfolio()), []);

  const schools = useMemo(() => items.map((item) => {
    const school = all.find((candidate: any) => candidate.id === item.id);
    return school ? { ...school, addedAt: item.addedAt } : null;
  }).filter(Boolean), [all, items]);

  const filtered = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return all.slice(0, 10);
    return all.filter((school: any) => school.chineseName.toLowerCase().includes(keyword) || school.name.toLowerCase().includes(keyword) || (school.city || "").toLowerCase().includes(keyword)).slice(0, 10);
  }, [all, query]);

  // Gate-bloker repair #RG-P0-D: the previous totalCost reducer used
// `(school.annualCostRmb || 0)` which treated missing cost as ¥0.
// That both under-reported the budget exposure and let schools
// with no data appear to be the cheapest in the list. We now
// filter out missing values from the sum and report a "data
// incomplete" hint when at least one school lacks cost data.
function readCostRmb(school: any): number | null {
  const v = school?.annualCostRmb;
  if (typeof v !== "number" || !Number.isFinite(v) || v <= 0) return null;
  return v;
}
const costSummary = useMemo(() => {
  let sum = 0;
  let missing = 0;
  for (const school of schools as any[]) {
    const c = readCostRmb(school);
    if (c === null) missing += 1;
    else sum += c;
  }
  return { sum, missing };
}, [schools]);
const hasIncompleteCost = costSummary.missing > 0;
const costCount = schools.length - costSummary.missing;
  const roughTiers = useMemo(() => schools.reduce((acc: { reach: number; target: number; safety: number }, school: any) => {
    if (school.rankingTier === "top20") acc.reach += 1;
    else if (school.rankingTier === "top50") acc.target += 1;
    else acc.safety += 1;
    return acc;
  }, { reach: 0, target: 0, safety: 0 }), [schools]);

  const addSchool = useCallback((id: string) => {
    setItems((prev) => {
      if (prev.some((item) => item.id === id)) return prev;
      const next = [...prev, { id, addedAt: new Date().toISOString().split("T")[0] }];
      savePortfolio(next);
      return next;
    });
    setShowAdd(false);
    setQuery("");
  }, []);

  const removeSchool = useCallback((id: string) => {
    setItems((prev) => {
      const next = prev.filter((item) => item.id !== id);
      savePortfolio(next);
      return next;
    });
  }, []);

  const clearSchools = useCallback(() => {
    if (confirm("确定清空当前清单？")) {
      setItems([]);
      savePortfolio([]);
      setResult(null);
    }
  }, []);

  const exportSchools = useCallback(() => {
    const data = schools.map((school: any) => ({ id: school.id, name: school.name, chineseName: school.chineseName, city: school.city, state: school.state, annualCostRmb: typeof school.annualCostRmb === "number" ? school.annualCostRmb : null, rankingTier: school.rankingTier }));
    const blob = new Blob([JSON.stringify({ exportedAt: new Date().toISOString(), universities: data, aiAnalysis: result, hasIncompleteCost }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "pathos-ai-portfolio-review.json";
    anchor.click();
    URL.revokeObjectURL(url);
  }, [hasIncompleteCost, result, schools]);

  const runAiReview = () => {
    setResult(LOCAL_AI_PORTFOLIO_DEMO);
  };

  return (
    <div className="min-h-screen bg-surface-base">
      <header className="border-b border-border-soft bg-surface-1/70 backdrop-blur">
        <div className="mx-auto flex max-w-page flex-wrap items-center gap-3 px-4 py-3 sm:gap-4 sm:px-6">
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-control bg-persimmon text-paper"><Bookmark size={18} aria-hidden="true" /></div>
          <div className="min-w-0 flex-1">
            <p className="text-label uppercase tracking-[0.12em] text-persimmon">AI 清单分析</p>
            <h1 className="text-page text-text-primary">冲刺 / 匹配 / 保底结构</h1>
            <p className="mt-0.5 text-caption text-text-secondary">本地 Demo 示例：点击即可查看输出结构，不连接外部 AI。</p>
          </div>
          <Link href="/assessment" className="ml-auto inline-flex h-control items-center gap-1.5 rounded-control bg-ink px-3 text-[12px] font-semibold text-paper transition hover:bg-ink/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"><Brain size={13} aria-hidden="true" /> 先做学校评估</Link>
        </div>
      </header>

      <main className="mx-auto grid max-w-page gap-6 px-4 py-5 sm:px-6 lg:grid-cols-[390px_1fr]">
        <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <section className="rounded-[1.6rem] border border-white/70 bg-white/85 p-5 shadow-xl shadow-ink/5">
            <div className="mb-4 flex items-center justify-between gap-3"><div><p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-jade/80">清单输入</p><h2 className="mt-1 text-base font-semibold text-ink">清单输入</h2></div><button onClick={() => setShowAdd((prev) => !prev)} className="inline-flex items-center gap-1.5 rounded-full bg-cobalt px-3 py-1.5 text-xs font-semibold text-white"><Plus size={13} /> 添加</button></div>
            <div className="grid grid-cols-2 gap-3">
              <Stat label="学校" value={schools.length} />
              <Stat label="年均费用" value={
                costCount > 0 && !hasIncompleteCost
                  ? "¥" + Math.round(costSummary.sum / costCount / 10000) + "万"
                  : hasIncompleteCost
                    ? "数据补充中"
                    : "—"
              } />
              <Stat label="冲刺" value={roughTiers.reach} />
              <Stat label="保底" value={roughTiers.safety} />
            </div>
            <div className="mt-4 flex gap-2"><button onClick={runAiReview} className="inline-flex flex-1 items-center justify-center gap-2 rounded-full bg-ink px-4 py-2.5 text-sm font-semibold text-panel transition hover:bg-ink/90"><Brain size={16} /> 查看 AI Demo</button><button disabled={schools.length === 0} onClick={exportSchools} className="rounded-full border border-line/60 bg-panel px-3 text-ink/55 transition hover:text-ink disabled:opacity-40"><Download size={16} /></button></div>
            {schools.length > 0 && <button onClick={clearSchools} className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-ink/38 transition hover:text-persimmon"><Trash2 size={13} /> 清空清单</button>}
          </section>

          {showAdd && <section className="rounded-[1.6rem] border border-white/70 bg-white/85 p-5 shadow-xl shadow-ink/5">
            <div className="relative"><SearchInput value={query} onChange={setQuery} /></div>
            <div className="mt-3 grid gap-2">{filtered.map((school: any) => <button key={school.id} onClick={() => addSchool(school.id)} className="flex items-center justify-between rounded-xl border border-line/45 bg-panel/70 px-3 py-2 text-left text-xs transition hover:border-cobalt/30 hover:bg-cobalt/5"><span><span className="font-semibold text-ink">{school.chineseName}</span><span className="ml-2 text-ink/38">{school.name}</span></span><Plus size={14} className="text-cobalt" /></button>)}</div>
          </section>}

          <section className="rounded-[1.4rem] border border-line/50 bg-ink p-5 text-panel shadow-xl shadow-ink/10"><p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-panel/45">功能说明</p><h3 className="mt-2 text-base font-semibold">清单页不再只是收藏夹</h3><p className="mt-3 text-sm leading-relaxed text-panel/66">学校清单现在是 AI 测验的一类输入，负责检查组合结构、风险暴露和家长追问点；自主匹配留在 /match。</p></section>
        </aside>

        <section className="space-y-4">
          <div className="rounded-[1.7rem] border border-white/70 bg-white/85 p-5 shadow-xl shadow-ink/5">
            <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-persimmon/75">当前清单</p><h2 className="mt-1 text-xl font-semibold text-ink">当前选校清单</h2><p className="mt-1 text-sm text-ink/50">点击 AI Demo 立即查看示例；非真实 AI 结论。</p></div><Link href="/match" className="inline-flex items-center gap-2 rounded-full border border-line/60 bg-panel px-4 py-2 text-xs font-semibold text-ink/60 transition hover:border-cobalt/35 hover:text-cobalt"><Sparkles size={14} /> 从自主测验添加</Link></div>
            {schools.length === 0 ? <div className="mt-8 rounded-[1.4rem] border border-dashed border-line/70 bg-panel/60 p-10 text-center"><Bookmark size={32} className="mx-auto text-ink/20" /><h3 className="mt-3 text-base font-semibold text-ink/62">清单还是空的</h3><p className="mt-1 text-sm text-ink/42">先添加学校，或从自主测验结果加入清单。</p><button onClick={() => setShowAdd(true)} className="mt-5 rounded-full bg-ink px-5 py-2 text-sm font-semibold text-panel">添加学校</button></div> : <div className="mt-5 grid gap-3">{schools.map((school: any, index: number) => <article key={school.id} className="rounded-[1.4rem] border border-line/45 bg-panel/70 p-4 transition hover:border-cobalt/30 hover:bg-white"><div className="flex items-start gap-3"><div className="grid h-9 w-9 place-items-center rounded-2xl bg-ink text-xs font-bold text-panel">{index + 1}</div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className="text-sm font-semibold text-ink">{school.chineseName}</h3><span className="text-xs text-ink/38">{school.name}</span><span className="rounded-full bg-cobalt/8 px-2 py-0.5 text-[11px] font-semibold text-cobalt">{school.rankingTier}</span></div><p className="mt-1 text-xs text-ink/45">
                  {school.city}, {school.state} ·{" "}
                  {readCostRmb(school) !== null
                    ? `¥${Math.round((readCostRmb(school) as number) / 10000)}万/年`
                    : "学费数据补充中"}{" "}
                  · 加入于 {school.addedAt}
                </p>{school.programs?.length > 0 && <div className="mt-3 flex flex-wrap gap-1.5">{school.programs.slice(0, 5).map((program: string) => <span key={program} className="rounded-full bg-white px-2 py-0.5 text-[10px] font-medium text-ink/45">{program}</span>)}</div>}</div><button onClick={() => removeSchool(school.id)} className="rounded-full p-1.5 text-ink/30 transition hover:bg-red-50 hover:text-red-500"><X size={15} /></button></div></article>)}</div>}
          </div>

          {result && <section className="rounded-[1.7rem] border border-white/70 bg-ink p-5 text-panel shadow-xl shadow-ink/10">
            <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-panel/45">本地示例 · {result.source}</p><h2 className="mt-1 text-xl font-semibold">清单分析 Demo</h2></div><div className="rounded-full bg-panel/10 px-3 py-1.5 text-xs font-semibold text-panel/70">示例不评分</div></div>
            <p className="mt-4 rounded-2xl bg-panel/10 p-4 text-sm leading-relaxed text-panel/76">{result.summary}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-4"><Metric label="冲刺" value={result.portfolio.reachCount} /><Metric label="匹配" value={result.portfolio.targetCount} /><Metric label="保底" value={result.portfolio.safetyCount} /><Metric label="风险" value="示例" /></div>
            <div className="mt-5 grid gap-3 lg:grid-cols-3">
              <Panel title="结构风险">{(result.portfolio.majorRisks.length ? result.portfolio.majorRisks : ["暂未发现明显结构风险"]).map((risk) => <Item key={risk}>{risk}</Item>)}</Panel>
              <Panel title="家长追问">{result.portfolio.parentQuestions.slice(0, 4).map((question) => <Item key={question}>{question}</Item>)}</Panel>
              <Panel title="下一步动作">{result.nextActions.map((action) => <Item key={action}>{action}</Item>)}</Panel>
            </div>
            <div className="mt-5"><h3 className="mb-2 text-sm font-semibold text-panel/85">优先复核学校</h3><div className="rounded-2xl bg-panel/10 p-3 text-sm text-panel/70">Demo 不生成学校排序或录取判断。</div></div>
          </section>}
        </section>
      </main>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-2xl border border-line/40 bg-panel/70 p-3 text-center"><div className="text-lg font-black text-ink">{value}</div><div className="text-[11px] text-ink/42">{label}</div></div>;
}

function Metric({ label, value }: { label: string; value: number | string | null }) {
  return <div className="rounded-2xl bg-panel/10 p-3 text-center"><div className="text-2xl font-black text-panel">{value ?? "—"}</div><div className="text-xs text-panel/45">{label}</div></div>;
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section><h3 className="mb-2 text-sm font-semibold text-panel/85">{title}</h3><div className="space-y-2">{children}</div></section>;
}

function Item({ children }: { children: React.ReactNode }) {
  return <div className="rounded-2xl bg-panel/10 p-3 text-sm leading-relaxed text-panel/70">{children}</div>;
}
