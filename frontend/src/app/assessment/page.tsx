"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Brain, CheckCircle2, ClipboardCheck, Plus, Sparkles, Trash2 } from "lucide-react";
import { SearchInput } from "@/components/shared/SearchInput";
import { useDataSource } from "@/services/data-source-provider";
import { useUniversitySummaries } from "@/hooks/use-data-source";

const PROFILE_KEY = "pathos_student_profile";

type Profile = {
  nickname: string;
  grade: string;
  gpa: string;
  toefl: string;
  sat: string;
  targetMajor: string;
  targetDegree: string;
  budgetRmb: number;
  background: string;
  priorities: string[];
};

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
  ai?: unknown;
};

const DEFAULT_PROFILE: Profile = {
  nickname: "",
  grade: "11",
  gpa: "3.7",
  toefl: "100",
  sat: "1450",
  targetMajor: "Computer Science",
  targetDegree: "bachelor",
  budgetRmb: 550000,
  background: "中国高中学生，计划申请美国本科。",
  priorities: ["employment", "safety", "recognition"],
};

const PRIORITIES = [
  { id: "employment", label: "就业" },
  { id: "safety", label: "安全" },
  { id: "recognition", label: "认可度" },
  { id: "cost", label: "成本" },
  { id: "community", label: "华人社区" },
];

const tierLabel: Record<string, string> = { reach: "冲刺", target: "匹配", safety: "保底" };
const tierTone: Record<string, string> = { reach: "bg-persimmon/10 text-persimmon", target: "bg-cobalt/10 text-cobalt", safety: "bg-jade/10 text-jade" };

function analysisSourceLabel(source: string): string {
  if (source === "deepseek") return "DeepSeek + PathOS 数据";
  if (source === "local-model") return "PathOS 规则引擎";
  if (source === "external-ai") return "外部 AI + PathOS 数据";
  return source;
}

function readCostRmb(school: any): number | null {
  const direct = school?.annualCostRmb;
  if (typeof direct === "number" && Number.isFinite(direct) && direct > 0) return direct;
  const usd = school?.costSummary?.maximumUsd ?? school?.costSummary?.minimumUsd;
  return typeof usd === "number" && Number.isFinite(usd) && usd > 0
    ? Math.round(usd * 7.2)
    : null;
}

const LOCAL_AI_ASSESSMENT_DEMO: AnalysisResult = {
  source: "本地 Demo 示例",
  summary: "这是本地交互示例，用于展示 AI 学校评估的输出结构。它不会连接外部 AI，也不会生成录取结论或学校适配分数。",
  portfolio: {
    reachCount: null,
    targetCount: null,
    safetyCount: null,
    averageFitScore: null,
    majorRisks: [],
    parentQuestions: [],
  },
  recommended: [],
  nextActions: [
    "先核对目标专业、预算与申请年份是否完整。",
    "逐校确认语言、标化与专业要求；未核实字段继续显示为数据补充中。",
    "将最终学校组合交给顾问或家庭成员进行第二轮人工复核。",
  ],
};

export default function AssessmentPage() {
  const dataSource = useDataSource();
  const summariesState = useUniversitySummaries(dataSource);
  const all = useMemo(
    () => (summariesState.state.status === "ready" ? (summariesState.state.data as unknown as any[]) : []),
    [summariesState.state],
  );
  const [profile, setProfile] = useState<Profile>(DEFAULT_PROFILE);
  const [query, setQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>(() => all.slice(0, 5).map((school) => school.id));
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const selectedSchools = useMemo(() => selectedIds.map((id) => all.find((school) => school.id === id)).filter(Boolean), [all, selectedIds]);
  const filtered = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return all.slice(0, 8);
    return all.filter((school) => school.chineseName.toLowerCase().includes(keyword) || school.name.toLowerCase().includes(keyword) || (school.city || "").toLowerCase().includes(keyword)).slice(0, 8);
  }, [all, query]);

  const updateProfile = <K extends keyof Profile>(key: K, value: Profile[K]) => setProfile((prev) => ({ ...prev, [key]: value }));
  const togglePriority = (id: string) => setProfile((prev) => ({ ...prev, priorities: prev.priorities.includes(id) ? prev.priorities.filter((item) => item !== id) : [...prev.priorities, id] }));
  const addSchool = (id: string) => setSelectedIds((prev) => prev.includes(id) ? prev : [...prev, id]);
  const removeSchool = (id: string) => setSelectedIds((prev) => prev.filter((item) => item !== id));

  const saveProfile = () => {
    try {
      localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
      setSaved(true);
      setTimeout(() => setSaved(false), 1800);
    } catch {}
  };

  const runAiAssessment = async () => {
    saveProfile();
    setAnalyzing(true);
    setAiError(null);
    setResult(null);
    const selectedSchools = selectedIds.map((id) => all.find((school) => school.id === id)).filter(Boolean);
    try {
      const r = await fetch("/api/ai/analyze", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ mode: "school_assessment", profile, schools: selectedSchools }),
      });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const data = await r.json();
      setResult(data);
    } catch (error: unknown) {
      console.warn("ai analyze failed, falling back to local demo", error instanceof Error ? error.message : error);
      setAiError("分析接口暂不可用，已切换为离线结构示例。");
      setResult(LOCAL_AI_ASSESSMENT_DEMO);
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-base">
      <header className="border-b border-border-soft bg-surface-1/70 backdrop-blur">
        <div className="mx-auto flex max-w-page flex-wrap items-center gap-3 px-4 py-3 sm:gap-4 sm:px-6">
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-control bg-cobalt text-paper"><Brain size={18} aria-hidden="true" /></div>
          <div className="min-w-0 flex-1">
            <p className="text-label uppercase tracking-[0.12em] text-cobalt">AI 学校评估</p>
            <h1 className="text-page text-text-primary">画像与目标校风险体检</h1>
            <p className="mt-0.5 text-caption text-text-secondary">使用当前 Supabase 学校数据运行规则评估；配置 DeepSeek 后自动叠加模型分析。</p>
          </div>
          <Link href="/match" className="ml-auto inline-flex h-control items-center gap-1.5 rounded-control border border-border-soft bg-surface-1 px-3 text-[12px] font-semibold text-text-primary transition hover:border-cobalt/40 hover:text-cobalt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"><Sparkles size={13} aria-hidden="true" /> 返回自主测验</Link>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-6 lg:grid-cols-[390px_1fr]">
        <div className="lg:col-span-2">
          <div
            role="note"
            className="flex items-start gap-2 rounded-control border border-persimmon/30 bg-persimmon/8 px-3 py-2 text-caption text-persimmon"
          >
            <AlertTriangle size={13} aria-hidden="true" className="mt-0.5 shrink-0" />
            <p>
              区域指标（安全 / 就业 / 华人社区）当前仅在地图上作环境参考，
              未进入 AI 评估与自主匹配分数；区域数据接入完整数据源后会再次校准评分口径。
            </p>
          </div>
        </div>

        <section className="space-y-4">
          <div className="rounded-[1.6rem] border border-white/70 bg-white/85 p-5 shadow-xl shadow-ink/5">
            <div className="mb-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-jade/80">学生画像</p>
              <h2 className="mt-1 text-base font-semibold text-ink">AI 输入画像</h2>
              <p className="mt-1 text-xs text-ink/48">这里是 AI 测验的输入，不再与自主权重匹配混在一起。</p>
            </div>
            <div className="grid gap-3">
              <label className="text-xs font-semibold text-ink/58">称呼<input value={profile.nickname} onChange={(event) => updateProfile("nickname", event.target.value)} placeholder="如：小明" className="mt-1 w-full rounded-xl border border-line/60 bg-panel px-3 py-2 text-sm font-normal text-ink outline-none focus:border-cobalt/45" /></label>
              <div className="grid grid-cols-2 gap-3">
                <label className="text-xs font-semibold text-ink/58">GPA<input value={profile.gpa} onChange={(event) => updateProfile("gpa", event.target.value)} className="mt-1 w-full rounded-xl border border-line/60 bg-panel px-3 py-2 text-sm font-normal text-ink outline-none focus:border-cobalt/45" /></label>
                <label className="text-xs font-semibold text-ink/58">预算<input type="number" value={profile.budgetRmb} onChange={(event) => updateProfile("budgetRmb", Number(event.target.value))} className="mt-1 w-full rounded-xl border border-line/60 bg-panel px-3 py-2 text-sm font-normal text-ink outline-none focus:border-cobalt/45" /></label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="text-xs font-semibold text-ink/58">TOEFL<input value={profile.toefl} onChange={(event) => updateProfile("toefl", event.target.value)} className="mt-1 w-full rounded-xl border border-line/60 bg-panel px-3 py-2 text-sm font-normal text-ink outline-none focus:border-cobalt/45" /></label>
                <label className="text-xs font-semibold text-ink/58">SAT/ACT<input value={profile.sat} onChange={(event) => updateProfile("sat", event.target.value)} className="mt-1 w-full rounded-xl border border-line/60 bg-panel px-3 py-2 text-sm font-normal text-ink outline-none focus:border-cobalt/45" /></label>
              </div>
              <label className="text-xs font-semibold text-ink/58">目标专业<input value={profile.targetMajor} onChange={(event) => updateProfile("targetMajor", event.target.value)} className="mt-1 w-full rounded-xl border border-line/60 bg-panel px-3 py-2 text-sm font-normal text-ink outline-none focus:border-cobalt/45" /></label>
              <label className="text-xs font-semibold text-ink/58">背景补充<textarea value={profile.background} onChange={(event) => updateProfile("background", event.target.value)} rows={3} className="mt-1 w-full resize-none rounded-xl border border-line/60 bg-panel px-3 py-2 text-sm font-normal text-ink outline-none focus:border-cobalt/45" /></label>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {PRIORITIES.map((item) => {
                const active = profile.priorities.includes(item.id);
                return <button key={item.id} onClick={() => togglePriority(item.id)} className={(active ? "border-cobalt/40 bg-cobalt/10 text-cobalt" : "border-line/50 bg-panel text-ink/52") + " rounded-full border px-3 py-1.5 text-xs font-semibold transition"}>{item.label}</button>;
              })}
            </div>
            <button onClick={saveProfile} className="mt-4 inline-flex items-center gap-2 rounded-full bg-ink px-4 py-2 text-xs font-semibold text-panel transition hover:bg-ink/90"><CheckCircle2 size={14} /> {saved ? "已保存画像" : "保存画像"}</button>
          </div>

          <div className="rounded-[1.6rem] border border-white/70 bg-white/85 p-5 shadow-xl shadow-ink/5">
            <div className="mb-4 flex items-center justify-between"><h2 className="text-base font-semibold text-ink">目标学校</h2><span className="rounded-full bg-ink/5 px-2.5 py-1 text-xs font-semibold text-ink/50">{selectedSchools.length} 所</span></div>
            <div className="relative"><SearchInput value={query} onChange={setQuery} /></div>
            <div className="mt-3 grid gap-2">
              {filtered.map((school: any) => <button key={school.id} onClick={() => addSchool(school.id)} className="flex items-center justify-between rounded-xl border border-line/45 bg-panel/70 px-3 py-2 text-left text-xs transition hover:border-cobalt/30 hover:bg-cobalt/5"><span><span className="font-semibold text-ink">{school.chineseName}</span><span className="ml-2 text-ink/38">{school.name}</span></span><Plus size={14} className="text-cobalt" /></button>)}
            </div>
          </div>
        </section>

        <section className="space-y-4">
          <div className="rounded-[1.7rem] border border-white/70 bg-white/85 p-5 shadow-xl shadow-ink/5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-persimmon/75">评估输入</p><h2 className="mt-1 text-xl font-semibold text-ink">待评估学校</h2><p className="mt-1 text-sm text-ink/50">基于当前学校数据生成风险分层；结果不等同于录取概率。</p></div>
              <button onClick={runAiAssessment} disabled={analyzing || selectedIds.length === 0} className="inline-flex items-center gap-2 rounded-full bg-cobalt px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cobalt/15 transition hover:-translate-y-0.5 disabled:opacity-60 disabled:cursor-not-allowed"><Brain size={16} /> {analyzing ? "评估中…" : "运行 AI 评估"}</button>
            </div>
            {aiError ? <div role="alert" className="mt-2 rounded-md border border-persimmon/30 bg-persimmon/8 px-3 py-2 text-xs text-persimmon">{aiError}</div> : null}
            <div className="mt-5 grid gap-3 md:grid-cols-2">
              {selectedSchools.map((school: any) => <article key={school.id} className="rounded-2xl border border-line/45 bg-panel/70 p-3"><div className="flex items-start justify-between gap-3"><div><h3 className="text-sm font-semibold text-ink">{school.chineseName}</h3><p className="text-xs text-ink/40">{school.name}</p><p className="mt-1 text-xs text-ink/45">
                        {school.city}, {school.state} ·{" "}
                        {readCostRmb(school) !== null
                          ? `¥${Math.round((readCostRmb(school) as number) / 10000)}万/年`
                          : "学费数据补充中"}
                      </p></div><button onClick={() => removeSchool(school.id)} className="rounded-full p-1.5 text-ink/30 transition hover:bg-red-50 hover:text-red-500"><Trash2 size={14} /></button></div></article>)}
            </div>
          </div>

          {result && <div className="rounded-[1.7rem] border border-white/70 bg-ink p-5 text-panel shadow-xl shadow-ink/10">
            <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-panel/45">数据驱动 · {analysisSourceLabel(result.source)}</p><h2 className="mt-1 text-xl font-semibold">学校评估结果</h2></div><div className="rounded-full bg-panel/10 px-3 py-1.5 text-xs font-semibold text-panel/70">仅供决策参考</div></div>
            <p className="mt-4 rounded-2xl bg-panel/10 p-4 text-sm leading-relaxed text-panel/76">{result.summary}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-4"><Metric label="冲刺" value={result.portfolio.reachCount} /><Metric label="匹配" value={result.portfolio.targetCount} /><Metric label="保底" value={result.portfolio.safetyCount} /><Metric label="平均适配" value={result.portfolio.averageFitScore !== null ? `${result.portfolio.averageFitScore}%` : null} /></div>
            <div className="mt-5 grid gap-3 lg:grid-cols-3">
              <Panel title="优先复核学校">
                {result.recommended.length > 0 ? result.recommended.map((school) => <article key={school.id} className="rounded-2xl bg-panel/10 p-3"><div className="flex items-center justify-between gap-2"><p className="text-sm font-semibold text-panel">{school.chineseName}</p><span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${tierTone[school.tier] ?? "bg-panel/10 text-panel/70"}`}>{tierLabel[school.tier] ?? school.tier}</span></div><p className="mt-1 text-xs text-panel/50">适配度 {school.fitScore}%</p>{school.reasons[0] ? <p className="mt-2 text-xs leading-relaxed text-panel/70">{school.reasons[0]}</p> : null}{school.warnings[0] ? <p className="mt-2 text-[11px] leading-relaxed text-persimmon/90">{school.warnings[0]}</p> : null}</article>) : <div className="rounded-2xl bg-panel/10 p-3 text-sm text-panel/70">当前没有可排序结果，请补充学校或稍后重试。</div>}
              </Panel>
              <Panel title="主要风险">
                {(result.portfolio.majorRisks.length > 0 ? result.portfolio.majorRisks : ["暂无明显结构性风险"]).map((risk) => <div key={risk} className="rounded-2xl bg-panel/10 p-3 text-sm text-panel/70">{risk}</div>)}
              </Panel>
              <Panel title="下一步动作">
                {result.nextActions.map((action) => <div key={action} className="rounded-2xl bg-panel/10 p-3 text-sm text-panel/70">{action}</div>)}
              </Panel>
            </div>
          </div>}
        </section>
      </main>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string | null }) {
  return <div className="rounded-2xl bg-panel/10 p-3 text-center"><div className="text-2xl font-black text-panel">{value ?? "—"}</div><div className="text-xs text-panel/45">{label}</div></div>;
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section><h3 className="mb-2 text-sm font-semibold text-panel/85">{title}</h3><div className="space-y-2">{children}</div></section>;
}
