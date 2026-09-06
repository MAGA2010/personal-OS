"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowUpRight, BookOpen, CheckCircle2, CircleAlert, GraduationCap, Search } from "lucide-react";
import { useDataSource } from "@/services/data-source-provider";
import { useCollegeGuide, useUniversityDetail, useUniversitySummaries } from "@/hooks/use-data-source";
import { DataEmptyState, DataLoadingState } from "@/components/shared/data-states";
import type { CollegeGuide } from "@/domain/dataset";

function formatRate(value: number | null | undefined) {
  if (typeof value !== "number") return "数据补充中";
  return `${(value <= 1 ? value * 100 : value).toFixed(1)}%`;
}

function formatCost(school: any) {
  const value = school?.costSummary?.maximumUsd ?? school?.costSummary?.minimumUsd;
  return typeof value === "number" ? `$${Math.round(value).toLocaleString()}/年` : "费用待核验";
}

export default function GuidesPage() {
  const source = useDataSource();
  const summaries = useUniversitySummaries(source);
  const schools = summaries.state.status === "ready" ? summaries.state.data : [];
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = useUniversityDetail(source, selectedId);
  const guide = useCollegeGuide(source, selectedId);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return schools.slice(0, 20);
    return schools.filter((school) => [school.name, school.nameZh, ...(school.aliases ?? []), school.city, school.state].filter(Boolean).join(" ").toLowerCase().includes(q)).slice(0, 20);
  }, [query, schools]);

  return (
    <main className="min-h-screen bg-surface-base">
      <header className="border-b border-border-soft bg-surface-1/80">
        <div className="mx-auto flex max-w-page flex-wrap items-center gap-4 px-4 py-5 sm:px-6">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-control bg-cobalt text-paper"><BookOpen size={21} /></div>
          <div className="min-w-0 flex-1">
            <p className="text-label uppercase tracking-[0.14em] text-cobalt">COLLEGE GUIDE</p>
            <h1 className="text-page text-text-primary">先读懂大学，再决定要不要申请</h1>
            <p className="mt-1 max-w-2xl text-sm leading-relaxed text-text-secondary">把学校的数字、课程、环境和申请要求放在同一个家庭可以讨论的页面里。</p>
          </div>
          <Link href="/opportunities" className="inline-flex items-center gap-1.5 rounded-control border border-border-soft bg-surface-1 px-3 py-2 text-xs font-semibold text-text-secondary hover:border-cobalt/40 hover:text-cobalt">查看机会动态 <ArrowUpRight size={14} /></Link>
        </div>
      </header>

      <div className="mx-auto grid max-w-page gap-5 px-4 py-5 sm:px-6 lg:grid-cols-[320px_1fr]">
        <aside className="lg:sticky lg:top-20 lg:self-start">
          <div className="border-b border-border-soft pb-3">
            <label className="flex items-center gap-2 rounded-control border border-border-soft bg-surface-1 px-3 py-2.5 text-sm text-text-secondary">
              <Search size={16} /><span className="sr-only">搜索大学</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索大学 / 州 / 城市" className="min-w-0 flex-1 bg-transparent text-text-primary outline-none placeholder:text-text-tertiary" />
            </label>
            <p className="mt-2 text-[11px] text-text-tertiary">选择一所学校，开始五分钟理解。</p>
          </div>
          {summaries.state.status === "loading" && <DataLoadingState message="正在加载院校…" />}
          {summaries.state.status === "ready" && filtered.length === 0 && <DataEmptyState title="没有找到学校" description="试试英文名、中文名或所在州。" />}
          <div className="mt-3 space-y-1.5">
            {filtered.map((school) => <button key={school.id} type="button" onClick={() => setSelectedId(school.id)} className={`w-full border-b border-border-soft px-2 py-3 text-left transition hover:bg-surface-muted ${selectedId === school.id ? "bg-surface-muted" : ""}`}><div className="flex items-start justify-between gap-2"><span className="min-w-0"><span className="block truncate text-sm font-semibold text-text-primary">{school.nameZh}</span><span className="mt-0.5 block truncate text-[11px] text-text-tertiary">{school.name}</span></span><span className="shrink-0 text-[10px] text-text-tertiary">{school.rankingSummary?.nationalRank ? `#${school.rankingSummary.nationalRank}` : "—"}</span></div><p className="mt-1 text-[11px] text-text-secondary">{school.city}, {school.state} · {formatCost(school)}</p></button>)}
          </div>
        </aside>

        <section className="min-w-0">
          {!selectedId && <div className="border border-border-soft bg-surface-1 px-6 py-12 sm:px-10"><p className="text-label uppercase tracking-[0.14em] text-persimmon">START WITH CONTEXT</p><h2 className="mt-2 max-w-xl text-2xl font-semibold text-text-primary">不要先问“它排第几”，先问“它适不适合我的学习方式”。</h2><p className="mt-3 max-w-2xl text-sm leading-7 text-text-secondary">选择左侧学校后，PathOS 会把院校概况、招生数据、专业、费用和来源放在一起。任何缺失或待核验的数据都会保留原本的状态。</p><div className="mt-6 grid gap-3 sm:grid-cols-3"><GuidePoint icon={<GraduationCap size={17} />} title="学习方式" text="课程、规模和专业环境" /><GuidePoint icon={<CircleAlert size={17} />} title="申请现实" text="要求、截止日和竞争程度" /><GuidePoint icon={<CheckCircle2 size={17} />} title="家庭讨论" text="费用、风险和下一步" /></div></div>}
          {selected.state.status === "loading" && <DataLoadingState message="正在打开院校档案…" />}
          {selected.state.status === "ready" && selected.state.data && <GuideDetail detail={selected.state.data} guide={guide.state.status === "ready" ? guide.state.data : null} guideLoading={guide.state.status === "loading"} />}
        </section>
      </div>
    </main>
  );
}

function GuidePoint({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) { return <div className="border border-border-soft bg-surface-1 p-4"><div className="text-cobalt">{icon}</div><p className="mt-3 text-sm font-semibold text-text-primary">{title}</p><p className="mt-1 text-xs leading-relaxed text-text-secondary">{text}</p></div>; }

function GuideDetail({ detail, guide, guideLoading }: { detail: any; guide: CollegeGuide | null; guideLoading: boolean }) {
  const programs = (detail.programs ?? []).slice(0, 8);
  return <article className="border border-border-soft bg-surface-1">
    <div className="border-b border-border-soft px-5 py-5 sm:px-7"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-label uppercase tracking-[0.14em] text-cobalt">COLLEGE GUIDE / {detail.datasetVersion || "SNAPSHOT"}</p><h2 className="mt-2 text-2xl font-semibold text-text-primary">{detail.nameZh}</h2><p className="mt-1 text-sm text-text-secondary">{detail.name} · {detail.city}, {detail.state}</p></div><Link href={`/university/${encodeURIComponent(detail.id)}`} className="inline-flex items-center gap-1.5 rounded-control bg-ink px-3 py-2 text-xs font-semibold text-paper">查看完整档案 <ArrowUpRight size={14} /></Link></div><p className="mt-5 max-w-3xl text-sm leading-7 text-text-secondary">这是一个数据导览页：它帮助家庭先建立学校的基本理解，再进入完整档案核对细节。这里不会把排名直接翻译成录取保证。</p></div>
    <div className="grid divide-y divide-border-soft sm:grid-cols-2 sm:divide-x sm:divide-y-0"><GuideMetric label="录取率" value={formatRate(detail.acceptanceRate)} /><GuideMetric label="毕业率" value={formatRate(detail.graduationRate)} /><GuideMetric label="本科人数" value={detail.enrollmentSummary?.undergraduate?.toLocaleString?.() ?? "数据补充中"} /><GuideMetric label="年均费用" value={formatCost(detail)} /></div>
    <div className="grid gap-0 divide-y divide-border-soft lg:grid-cols-2 lg:divide-x lg:divide-y-0"><GuideBlock title="专业方向" text={programs.length ? programs.map((program: any) => program.name).join(" · ") : "专业数据补充中"} /><GuideBlock title="申请现实" text={detail.previewMetadata?.admissions?.testPolicy?.value ? "请继续核对标化政策、语言要求与申请截止日。" : "申请政策正在补充或核验。"} /><GuideBlock title="来源状态" text={detail.previewOnly ? "当前为可追溯预览数据，部分字段仍待核验。" : "当前档案已连接生产数据源。"} /><GuideBlock title="下一步" text="把这所学校加入申请清单，再与两所不同类型的学校比较。" /></div>
    {guideLoading && <div className="border-t border-border-soft px-5 py-5 sm:px-7"><DataLoadingState message="正在加载 IECG 学校解读…" /></div>}
    {guide ? <ImportedGuide guide={guide} /> : !guideLoading ? <div className="border-t border-border-soft px-5 py-5 sm:px-7 text-sm leading-7 text-text-secondary">这所学校暂时没有关联的 IECG 解读资料。上面的结构化数据仍可用于初步比较，申请政策请以学校官网为准。</div> : null}
  </article>;
}

function GuideMetric({ label, value }: { label: string; value: string }) { return <div className="px-5 py-4 sm:px-7"><p className="text-[11px] text-text-tertiary">{label}</p><p className="mt-1 text-lg font-semibold tabular-nums text-text-primary">{value}</p></div>; }
function GuideBlock({ title, text }: { title: string; text: string }) { return <section className="px-5 py-5 sm:px-7"><p className="text-label uppercase tracking-[0.12em] text-text-tertiary">{title}</p><p className="mt-2 text-sm leading-7 text-text-secondary">{text}</p></section>; }
function ImportedGuide({ guide }: { guide: CollegeGuide }) {
  const structured = guide.structured;
  const sections = guide.sections.filter((section) => ["简介/特点", "费用", "申请截止日", "申请基本要求（这是最低要求，不是录取要求！）", "本科新生招生情况", "本科录取中位线（25% - 75%录取学生处于这个阶段）", "学生反馈", "总结"].some((title) => section.title === title || section.title.startsWith(title))).slice(0, 8);
  const facts = [
    ["资料快照", `${guide.sourceSnapshotYear} 年`],
    ["本科人数", formatGuideFact(structured.undergraduateStudents)],
    ["师生比例", formatGuideFact(structured.studentFacultyRatio)],
    ["录取率", formatGuideFact(structured.acceptanceRatePercent, "%")],
  ].filter(([, value]) => value !== "数据补充中");
  return <section className="border-t border-border-soft bg-surface-muted/35 px-5 py-5 sm:px-7">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><p className="text-label uppercase tracking-[0.12em] text-persimmon">SOURCE-PRESERVING GUIDE</p><h3 className="mt-2 text-lg font-semibold text-text-primary">来自 IECG 的学校解读</h3><p className="mt-1 text-xs leading-relaxed text-text-secondary">这是一份 {guide.sourceSnapshotYear} 年资料快照，用来帮助理解学校；费用、考试、截止日和录取政策需要再次核对官方页面。</p></div>{guide.sourceUrl && <a href={guide.sourceUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-xs font-semibold text-cobalt hover:underline">打开学校官网 <ArrowUpRight size={13} /></a>}
    </div>
    <div className="mt-4 grid gap-px bg-border-soft sm:grid-cols-4">{facts.map(([label, value]) => <div key={label} className="bg-surface-1 px-3 py-3"><p className="text-[10px] text-text-tertiary">{label}</p><p className="mt-1 text-sm font-semibold text-text-primary">{value}</p></div>)}</div>
    <div className="mt-5 grid gap-3 lg:grid-cols-2">{sections.map((section) => <section key={section.id} className="border border-border-soft bg-surface-1 px-4 py-4"><p className="text-sm font-semibold text-text-primary">{section.title}</p><p className="mt-2 whitespace-pre-line text-sm leading-7 text-text-secondary">{section.text}</p></section>)}</div>
    <p className="mt-4 text-[11px] leading-relaxed text-text-tertiary">来源文件：{guide.sourceFile} · 状态：历史来源，未视为当前政策</p>
  </section>;
}

function formatGuideFact(value: string | number | string[] | undefined, suffix = "") {
  if (value === undefined || value === "" || (Array.isArray(value) && value.length === 0)) return "数据补充中";
  if (Array.isArray(value)) return value.join("、");
  return `${value}${suffix}`;
}