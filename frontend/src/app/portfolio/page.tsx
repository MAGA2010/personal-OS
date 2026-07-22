"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Bookmark, Brain, CheckCircle2, Download, Loader2, Plus, Search, Sparkles, Trash2, X } from "lucide-react";
import { ProductJourney } from "@/components/ProductJourney";
import universityData from "@/data/universities.json";

const STORAGE_KEY = "pathos_portfolio";
const PROFILE_KEY = "pathos_student_profile";

type PortfolioItem = { id: string; addedAt: string };
type AnalysisResult = {
  source: string;
  summary: string;
  portfolio: {
    reachCount: number;
    targetCount: number;
    safetyCount: number;
    averageFitScore: number;
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

function loadProfile() {
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    return raw ? JSON.parse(raw) : { budgetRmb: 550000, targetMajor: "Computer Science", priorities: ["employment", "safety", "recognition"] };
  } catch {
    return { budgetRmb: 550000, targetMajor: "Computer Science", priorities: ["employment", "safety", "recognition"] };
  }
}

const tierLabel: Record<string, string> = { reach: "冲刺", target: "匹配", safety: "保底" };
const tierTone: Record<string, string> = { reach: "bg-persimmon/10 text-persimmon", target: "bg-cobalt/10 text-cobalt", safety: "bg-jade/10 text-jade" };

export default function PortfolioPage() {
  const all = (universityData as any).universities as any[];
  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [query, setQuery] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const totalCost = useMemo(() => schools.reduce((sum: number, school: any) => sum + (school.annualCostRmb || 0), 0), [schools]);
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
    const data = schools.map((school: any) => ({ id: school.id, name: school.name, chineseName: school.chineseName, city: school.city, state: school.state, annualCostRmb: school.annualCostRmb, rankingTier: school.rankingTier }));
    const blob = new Blob([JSON.stringify({ exportedAt: new Date().toISOString(), universities: data, aiAnalysis: result }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "pathos-ai-portfolio-review.json";
    anchor.click();
    URL.revokeObjectURL(url);
  }, [result, schools]);

  const runAiReview = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/ai/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: "portfolio_review",
          profile: loadProfile(),
          schools: schools.map((school: any) => ({ id: school.id, name: school.name, chineseName: school.chineseName })),
          notes: "Review the balance of this school list for a Chinese family.",
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "AI 清单分析失败");
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI 清单分析失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(196,95,54,0.12),transparent_34%),linear-gradient(180deg,#f6f3ed_0%,#fffaf1_62%,#f6f3ed_100%)]">
      <header className="border-b border-line/50 bg-panel/85 px-5 py-5 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-persimmon text-white shadow-lg shadow-persimmon/15"><Bookmark size={22} /></div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-persimmon/75">AI portfolio review</p>
            <h1 className="text-xl font-semibold tracking-tight text-ink">AI 测验：选校清单分析</h1>
            <p className="mt-1 text-sm text-ink/55">清单管理保留，但核心动作改为调用 AI 分析冲刺/匹配/保底结构。</p>
          </div>
          <Link href="/assessment" className="ml-auto inline-flex items-center gap-2 rounded-full bg-ink px-4 py-2 text-xs font-semibold text-panel shadow-sm transition hover:-translate-y-0.5 hover:bg-ink/90"><Brain size={14} /> 先做学校评估</Link>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 pt-5"><ProductJourney active="portfolio" compact /></div>

      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-6 lg:grid-cols-[390px_1fr]">
        <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <section className="rounded-[1.6rem] border border-white/70 bg-white/85 p-5 shadow-xl shadow-ink/5">
            <div className="mb-4 flex items-center justify-between gap-3"><div><p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-jade/80">List input</p><h2 className="mt-1 text-base font-semibold text-ink">清单输入</h2></div><button onClick={() => setShowAdd((prev) => !prev)} className="inline-flex items-center gap-1.5 rounded-full bg-cobalt px-3 py-1.5 text-xs font-semibold text-white"><Plus size={13} /> 添加</button></div>
            <div className="grid grid-cols-2 gap-3">
              <Stat label="学校" value={schools.length} />
              <Stat label="年均费用" value={schools.length ? "¥" + Math.round(totalCost / schools.length / 10000) + "万" : "-"} />
              <Stat label="冲刺" value={roughTiers.reach} />
              <Stat label="保底" value={roughTiers.safety} />
            </div>
            <div className="mt-4 flex gap-2"><button disabled={schools.length === 0} onClick={runAiReview} className="inline-flex flex-1 items-center justify-center gap-2 rounded-full bg-ink px-4 py-2.5 text-sm font-semibold text-panel transition hover:bg-ink/90 disabled:cursor-not-allowed disabled:opacity-45">{loading ? <Loader2 size={16} className="animate-spin" /> : <Brain size={16} />} AI 分析清单</button><button disabled={schools.length === 0} onClick={exportSchools} className="rounded-full border border-line/60 bg-panel px-3 text-ink/55 transition hover:text-ink disabled:opacity-40"><Download size={16} /></button></div>
            {schools.length > 0 && <button onClick={clearSchools} className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-ink/38 transition hover:text-persimmon"><Trash2 size={13} /> 清空清单</button>}
            {error && <div className="mt-4 rounded-2xl border border-persimmon/25 bg-persimmon/8 p-3 text-sm text-persimmon"><AlertTriangle size={15} className="mr-1 inline" />{error}</div>}
          </section>

          {showAdd && <section className="rounded-[1.6rem] border border-white/70 bg-white/85 p-5 shadow-xl shadow-ink/5">
            <div className="relative"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink/30" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索学校 / 城市" className="w-full rounded-xl border border-line/60 bg-panel py-2 pl-9 pr-3 text-sm outline-none focus:border-cobalt/45" /></div>
            <div className="mt-3 grid gap-2">{filtered.map((school: any) => <button key={school.id} onClick={() => addSchool(school.id)} className="flex items-center justify-between rounded-xl border border-line/45 bg-panel/70 px-3 py-2 text-left text-xs transition hover:border-cobalt/30 hover:bg-cobalt/5"><span><span className="font-semibold text-ink">{school.chineseName}</span><span className="ml-2 text-ink/38">{school.name}</span></span><Plus size={14} className="text-cobalt" /></button>)}</div>
          </section>}

          <section className="rounded-[1.4rem] border border-line/50 bg-ink p-5 text-panel shadow-xl shadow-ink/10"><p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-panel/45">Difference</p><h3 className="mt-2 text-base font-semibold">清单页不再只是收藏夹</h3><p className="mt-3 text-sm leading-relaxed text-panel/66">学校清单现在是 AI 测验的一类输入，负责检查组合结构、风险暴露和家长追问点；自主匹配留在 /match。</p></section>
        </aside>

        <section className="space-y-4">
          <div className="rounded-[1.7rem] border border-white/70 bg-white/85 p-5 shadow-xl shadow-ink/5">
            <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-persimmon/75">Portfolio</p><h2 className="mt-1 text-xl font-semibold text-ink">当前选校清单</h2><p className="mt-1 text-sm text-ink/50">添加目标学校后，点击 AI 分析清单生成家庭讨论版本。</p></div><Link href="/match" className="inline-flex items-center gap-2 rounded-full border border-line/60 bg-panel px-4 py-2 text-xs font-semibold text-ink/60 transition hover:border-cobalt/35 hover:text-cobalt"><Sparkles size={14} /> 从自主测验添加</Link></div>
            {schools.length === 0 ? <div className="mt-8 rounded-[1.4rem] border border-dashed border-line/70 bg-panel/60 p-10 text-center"><Bookmark size={32} className="mx-auto text-ink/20" /><h3 className="mt-3 text-base font-semibold text-ink/62">清单还是空的</h3><p className="mt-1 text-sm text-ink/42">先添加学校，或从自主测验结果加入清单。</p><button onClick={() => setShowAdd(true)} className="mt-5 rounded-full bg-ink px-5 py-2 text-sm font-semibold text-panel">添加学校</button></div> : <div className="mt-5 grid gap-3">{schools.map((school: any, index: number) => <article key={school.id} className="rounded-[1.4rem] border border-line/45 bg-panel/70 p-4 transition hover:border-cobalt/30 hover:bg-white"><div className="flex items-start gap-3"><div className="grid h-9 w-9 place-items-center rounded-2xl bg-ink text-xs font-bold text-panel">{index + 1}</div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className="text-sm font-semibold text-ink">{school.chineseName}</h3><span className="text-xs text-ink/38">{school.name}</span><span className="rounded-full bg-cobalt/8 px-2 py-0.5 text-[11px] font-semibold text-cobalt">{school.rankingTier}</span></div><p className="mt-1 text-xs text-ink/45">{school.city}, {school.state} · ¥{Math.round((school.annualCostRmb || 0) / 10000)}万/年 · 加入于 {school.addedAt}</p>{school.programs?.length > 0 && <div className="mt-3 flex flex-wrap gap-1.5">{school.programs.slice(0, 5).map((program: string) => <span key={program} className="rounded-full bg-white px-2 py-0.5 text-[10px] font-medium text-ink/45">{program}</span>)}</div>}</div><button onClick={() => removeSchool(school.id)} className="rounded-full p-1.5 text-ink/30 transition hover:bg-red-50 hover:text-red-500"><X size={15} /></button></div></article>)}</div>}
          </div>

          {result && <section className="rounded-[1.7rem] border border-white/70 bg-ink p-5 text-panel shadow-xl shadow-ink/10">
            <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-panel/45">AI output · {result.source}</p><h2 className="mt-1 text-xl font-semibold">清单分析结果</h2></div><div className="rounded-full bg-panel/10 px-3 py-1.5 text-xs font-semibold text-panel/70">平均适配 {result.portfolio.averageFitScore}%</div></div>
            <p className="mt-4 rounded-2xl bg-panel/10 p-4 text-sm leading-relaxed text-panel/76">{result.summary}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-4"><Metric label="冲刺" value={result.portfolio.reachCount} /><Metric label="匹配" value={result.portfolio.targetCount} /><Metric label="保底" value={result.portfolio.safetyCount} /><Metric label="风险" value={result.portfolio.majorRisks.length} /></div>
            <div className="mt-5 grid gap-3 lg:grid-cols-3">
              <Panel title="结构风险">{(result.portfolio.majorRisks.length ? result.portfolio.majorRisks : ["暂未发现明显结构风险"]).map((risk) => <Item key={risk}>{risk}</Item>)}</Panel>
              <Panel title="家长追问">{result.portfolio.parentQuestions.slice(0, 4).map((question) => <Item key={question}>{question}</Item>)}</Panel>
              <Panel title="下一步动作">{result.nextActions.map((action) => <Item key={action}>{action}</Item>)}</Panel>
            </div>
            <div className="mt-5"><h3 className="mb-2 text-sm font-semibold text-panel/85">优先复核学校</h3><div className="grid gap-2 md:grid-cols-3">{result.recommended.map((school) => <div key={school.id} className="rounded-2xl bg-panel/10 p-3"><div className="flex items-center justify-between gap-2"><span className="font-semibold text-panel">{school.chineseName}</span><span className={(tierTone[school.tier] || "bg-panel/10 text-panel/70") + " rounded-full px-2 py-0.5 text-[11px]"}>{tierLabel[school.tier] || school.tier}</span></div><p className="mt-1 text-xs text-panel/55">适配 {school.fitScore}%</p></div>)}</div></div>
          </section>}
        </section>
      </main>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-2xl border border-line/40 bg-panel/70 p-3 text-center"><div className="text-lg font-black text-ink">{value}</div><div className="text-[11px] text-ink/42">{label}</div></div>;
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-2xl bg-panel/10 p-3 text-center"><div className="text-2xl font-black text-panel">{value}</div><div className="text-xs text-panel/45">{label}</div></div>;
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section><h3 className="mb-2 text-sm font-semibold text-panel/85">{title}</h3><div className="space-y-2">{children}</div></section>;
}

function Item({ children }: { children: React.ReactNode }) {
  return <div className="rounded-2xl bg-panel/10 p-3 text-sm leading-relaxed text-panel/70">{children}</div>;
}
