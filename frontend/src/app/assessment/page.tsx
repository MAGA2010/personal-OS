"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Brain, CheckCircle2, ClipboardCheck, Loader2, Plus, Search, Sparkles, Trash2 } from "lucide-react";
import { ProductJourney } from "@/components/ProductJourney";
import universityData from "@/data/universities.json";

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
    reachCount: number;
    targetCount: number;
    safetyCount: number;
    averageFitScore: number;
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

export default function AssessmentPage() {
  const all = (universityData as any).universities as any[];
  const [profile, setProfile] = useState<Profile>(DEFAULT_PROFILE);
  const [query, setQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>(() => all.slice(0, 5).map((school) => school.id));
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/ai/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "school_assessment", profile, schools: selectedSchools.map((school: any) => ({ id: school.id, name: school.name, chineseName: school.chineseName })) }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "AI 分析失败");
      setResult(data);
      saveProfile();
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI 分析失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_right,rgba(49,93,159,0.13),transparent_32%),linear-gradient(180deg,#fffaf1_0%,#f6f3ed_100%)]">
      <header className="border-b border-line/50 bg-panel/85 px-5 py-5 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-cobalt text-white shadow-lg shadow-cobalt/15"><Brain size={22} /></div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cobalt/70">AI school assessment</p>
            <h1 className="text-xl font-semibold tracking-tight text-ink">AI 测验：学校评估</h1>
            <p className="mt-1 text-sm text-ink/55">接入 /api/ai/analyze，对学生画像与目标学校做 AI 风险体检。</p>
          </div>
          <Link href="/match" className="ml-auto inline-flex items-center gap-2 rounded-full border border-line/60 bg-white/70 px-4 py-2 text-xs font-semibold text-ink/65 transition hover:border-cobalt/35 hover:text-cobalt"><Sparkles size={14} /> 返回自主测验</Link>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 pt-5"><ProductJourney active="assessment" compact /></div>

      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-6 lg:grid-cols-[390px_1fr]">
        <section className="space-y-4">
          <div className="rounded-[1.6rem] border border-white/70 bg-white/85 p-5 shadow-xl shadow-ink/5">
            <div className="mb-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-jade/80">Student profile</p>
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
            <div className="relative"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink/30" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索学校 / 城市" className="w-full rounded-xl border border-line/60 bg-panel py-2 pl-9 pr-3 text-sm outline-none focus:border-cobalt/45" /></div>
            <div className="mt-3 grid gap-2">
              {filtered.map((school: any) => <button key={school.id} onClick={() => addSchool(school.id)} className="flex items-center justify-between rounded-xl border border-line/45 bg-panel/70 px-3 py-2 text-left text-xs transition hover:border-cobalt/30 hover:bg-cobalt/5"><span><span className="font-semibold text-ink">{school.chineseName}</span><span className="ml-2 text-ink/38">{school.name}</span></span><Plus size={14} className="text-cobalt" /></button>)}
            </div>
          </div>
        </section>

        <section className="space-y-4">
          <div className="rounded-[1.7rem] border border-white/70 bg-white/85 p-5 shadow-xl shadow-ink/5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-persimmon/75">AI test input</p><h2 className="mt-1 text-xl font-semibold text-ink">待评估学校</h2><p className="mt-1 text-sm text-ink/50">AI 会基于画像、学校数据和本地基准算法输出风险判断。</p></div>
              <button disabled={loading || selectedSchools.length === 0} onClick={runAiAssessment} className="inline-flex items-center gap-2 rounded-full bg-cobalt px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cobalt/15 transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50">{loading ? <Loader2 size={16} className="animate-spin" /> : <Brain size={16} />} 开始 AI 分析</button>
            </div>
            {error && <div className="mt-4 rounded-2xl border border-persimmon/25 bg-persimmon/8 p-3 text-sm text-persimmon"><AlertTriangle size={15} className="mr-1 inline" />{error}</div>}
            <div className="mt-5 grid gap-3 md:grid-cols-2">
              {selectedSchools.map((school: any) => <article key={school.id} className="rounded-2xl border border-line/45 bg-panel/70 p-3"><div className="flex items-start justify-between gap-3"><div><h3 className="text-sm font-semibold text-ink">{school.chineseName}</h3><p className="text-xs text-ink/40">{school.name}</p><p className="mt-1 text-xs text-ink/45">{school.city}, {school.state} · ¥{Math.round((school.annualCostRmb || 0) / 10000)}万/年</p></div><button onClick={() => removeSchool(school.id)} className="rounded-full p-1.5 text-ink/30 transition hover:bg-red-50 hover:text-red-500"><Trash2 size={14} /></button></div></article>)}
            </div>
          </div>

          {result && <div className="rounded-[1.7rem] border border-white/70 bg-ink p-5 text-panel shadow-xl shadow-ink/10">
            <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-panel/45">AI output · {result.source}</p><h2 className="mt-1 text-xl font-semibold">学校评估结果</h2></div><div className="rounded-full bg-panel/10 px-3 py-1.5 text-xs font-semibold text-panel/70">平均适配 {result.portfolio.averageFitScore}%</div></div>
            <p className="mt-4 rounded-2xl bg-panel/10 p-4 text-sm leading-relaxed text-panel/76">{result.summary}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3"><Metric label="冲刺" value={result.portfolio.reachCount} /><Metric label="匹配" value={result.portfolio.targetCount} /><Metric label="保底" value={result.portfolio.safetyCount} /></div>
            <div className="mt-5 grid gap-3 lg:grid-cols-2">
              <Panel title="推荐优先关注">
                {result.recommended.map((school) => <div key={school.id} className="rounded-2xl bg-panel/10 p-3"><div className="flex items-center justify-between gap-2"><span className="font-semibold text-panel">{school.chineseName}</span><span className={(tierTone[school.tier] || "bg-panel/10 text-panel/70") + " rounded-full px-2 py-0.5 text-[11px]"}>{tierLabel[school.tier] || school.tier}</span></div><p className="mt-1 text-xs text-panel/55">适配 {school.fitScore}% · {school.reasons[0]}</p></div>)}
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

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-2xl bg-panel/10 p-3 text-center"><div className="text-2xl font-black text-panel">{value}</div><div className="text-xs text-panel/45">{label}</div></div>;
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section><h3 className="mb-2 text-sm font-semibold text-panel/85">{title}</h3><div className="space-y-2">{children}</div></section>;
}
