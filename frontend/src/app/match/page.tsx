"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Bookmark, Brain, Check, DollarSign, GraduationCap, Map, Percent, Shield, Sparkles, Target, TrendingUp, Users } from "lucide-react";
import { useDataSource } from "@/services/data-source-provider";
import { useUniversitySummaries } from "@/hooks/use-data-source";

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
const clamp = (value: number) => Math.max(0, Math.min(100, Math.round(value)));
// Stage 7A — `formatRmb` now reads `costSummary.minimumUsd * 7.2`
// instead of the legacy `annualCostRmb` (which doesn't exist on the
// canonical summary). USD-minimum is the cheapest publicly listed
// tuition band; we surface that as the budget anchor so the slider
// has a real reference number to push against.
const formatRmb = (value: number | null | undefined) => {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return "学费数据补充中";
  return "¥" + Math.round(value / 10000) + "万";
};

function getMetricMap(metricId: string, records: readonly any[]) {
  return records.reduce<Record<string, number>>((acc, item) => {
    if (item.metricId === metricId && item.granularity === "state") {
      const fips = String(item.fipsCode ?? "").padStart(2, "0").slice(-2);
      acc[fips] = Math.round(Number(item.value ?? 0.5) * 100);
    }
    return acc;
  }, {});
}

// Gate-bloker repair #RG-P0-C: the previous version of this function
// fabricated missing facts: it forced every school with no
// `annualCostRmb` to look like ¥620000 (the average), every missing
// `safetyScore` to 60, every missing `recognitionScore` to 70, and
// every missing `admissionRate` to a derived fallback. That made
// every "data pending" school look identical to the average. The
// new version returns `null` for missing dimensions and excludes
// them from the weighted match — schools missing data show up
// with the "部分维度数据不足" badge instead of fake 0-100 scores.
// Stage 7A — `schoolPercentages` + `matchScore` rewrite.
//
// The previous version was written against the legacy summary shape
// (top-level `annualCostRmb`, `safetyScore`, `recognitionScore`,
// `chineseCommunity`, `numericRank`, `stateFips`). None of those
// fields exist on the canonical `UniversitySummary` produced by the
// Stage 5 Preview Bundle, so every school ended up flagged "部分维度
// 数据不足" and the match score collapsed to a single uniform value
// (because the math `(weighted/presentTotal)*100` overscaled by 100
// and everything clamped to 100%).
//
// What we DO have on the summary:
//   - costSummary.minimumUsd / maximumUsd  → budget dimension
//   - rankingSummary.nationalRank | rankingTier  → rank dimension
//   - acceptanceRate (lives in detail, not summary) → admission dim
//   - studentFacultyRatio  → optional safety-ish proxy (small)
//
// Region-scoped dimensions (safety, employment, chinese_community)
// are blocked at the source — the bundle's region-metrics.json has
// `records: []` and `status: "blocked"`. We render those three as
// "数据补充中" badges and exclude them from the weighted score
// instead of fabricating values.

const STAGE5_RMB_PER_USD = 7.2;
const STAGE5_TIER_SCORE: Record<string, number> = { top20: 96, top50: 82, top100: 66, other: 48 };
const STAGE5_RANK_DIM_BUDGET_USD = 30000; // USD baseline "comfortable"
const STAGE5_RANK_DIM_BUDGET_SPAN = 5000;  // USD above baseline that maps to 0%

function schoolPercentages(
  university: any,
  detail: { admissions?: { acceptanceRate?: { value: number | null; status?: string } } } | null,
): { school: StudentInputs; missing: DimensionKey[] } {
  const missing: DimensionKey[] = [];

  // Budget — read from `costSummary.minimumUsd` (the canonical
  // USD-based band). Higher USD = lower score.
  let budget: number | null = null;
  const minUsd = university?.costSummary?.minimumUsd;
  if (typeof minUsd === "number" && Number.isFinite(minUsd) && minUsd > 0) {
    const costRmb = minUsd * STAGE5_RMB_PER_USD;
    budget = clamp(100 - ((costRmb - STAGE5_RANK_DIM_BUDGET_USD * STAGE5_RMB_PER_USD) / (STAGE5_RANK_DIM_BUDGET_SPAN * STAGE5_RMB_PER_USD)));
  } else {
    missing.push("budget");
  }

  // Rank — read from `rankingSummary.nationalRank` first, then
  // fall back to the `rankingSummary.rankingTier` enum.
  let rank: number | null = null;
  const nationalRank = university?.rankingSummary?.nationalRank;
  const tier = university?.rankingSummary?.rankingTier ?? university?.rankingTier;
  if (typeof nationalRank === "number" && Number.isFinite(nationalRank) && nationalRank > 0) {
    rank = clamp(100 - (nationalRank - 1) * 1.35);
  } else if (typeof STAGE5_TIER_SCORE[tier] === "number") {
    rank = clamp(STAGE5_TIER_SCORE[tier]);
  } else {
    missing.push("rank");
  }

  // Region-scoped dimensions — currently blocked at the data source
  // (region-metrics returns `records: []`). Mark all three missing
  // and DO NOT fabricate a value from a stale metric cache.
  missing.push("safety");
  missing.push("employment");
  missing.push("community");

  // Admission — comes from preview detail. On the summary list, we
  // only get this if the caller passed detail (which the page does
  // not, for performance reasons). When absent, mark missing.
  let admission: number | null = null;
  const ar = detail?.admissions?.acceptanceRate?.value;
  if (typeof ar === "number" && Number.isFinite(ar) && ar > 0 && ar <= 1) {
    admission = clamp(Math.min(100, ar * 100 * 2.4));
  } else {
    missing.push("admission");
  }

  const school: StudentInputs = {
    budget: budget ?? 0,
    rank: rank ?? 0,
    safety: 0,
    employment: 0,
    community: 0,
    admission: admission ?? 0,
  };
  return { school, missing };
}

function matchScore(
  student: StudentInputs,
  weights: StudentInputs,
  school: StudentInputs,
  missing: DimensionKey[],
): number {
  // Re-normalize weights across the dimensions that DO have data.
  // A school missing "budget" can't be penalised for being over
  // budget; pretending it has a budget value of 0 would unfairly
  // inflate its score.
  //
  // Bug fix (Stage 7A): the previous formula was
  //   clamp((weighted / presentTotal) * 100)
  // which produced values vastly > 100 because each dim's
  // contribution is `(100 - gap) * weight` (range 0..100*weight).
  // Summing gives 0..100*presentTotal. Dividing by presentTotal
  // alone (not by presentTotal * 100) gives 0..100.
  const presentTotal = DIMENSIONS.reduce(
    (sum, dim) => (missing.includes(dim.key) ? sum : sum + weights[dim.key]),
    0,
  );
  if (presentTotal === 0) return 0;
  const weighted = DIMENSIONS.reduce((sum, dim) => {
    if (missing.includes(dim.key)) return sum;
    const gap = Math.abs(student[dim.key] - school[dim.key]);
    return sum + Math.max(0, 100 - gap) * weights[dim.key];
  }, 0);
  return clamp(weighted / presentTotal);
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
  const dataSource = useDataSource();
  const summariesState = useUniversitySummaries(dataSource);
  // Stage 7A — Region-scoped dimensions (safety / employment /
  // chinese_population) are blocked at the source (bundle returns
  // `records: []` + `status: "blocked"`). We no longer fetch them
  // and no longer fabricate values. The three dimensions render as
  // "数据补充中" badges and are excluded from the weighted score.
  const universities = useMemo(
    () => (summariesState.state.status === "ready" ? (summariesState.state.data as unknown as any[]) : []),
    [summariesState.state],
  );
  const [student, setStudent] = useState<StudentInputs>(DEFAULT_STUDENT);
  const [weights, setWeights] = useState<StudentInputs>(DEFAULT_WEIGHTS);
  const [addedId, setAddedId] = useState<string | null>(null);

  const matches = useMemo(() => universities.map((university) => {
    const { school, missing } = schoolPercentages(university, null);
    return {
      ...university,
      school,
      missing,
      match: matchScore(student, weights, school, missing),
    };
  }).sort((a, b) => b.match - a.match).slice(0, 18), [student, universities, weights]);

  const averageTarget = Math.round(DIMENSIONS.reduce((sum, dim) => sum + student[dim.key], 0) / DIMENSIONS.length);
  const totalWeight = DIMENSIONS.reduce((sum, dim) => sum + weights[dim.key], 0);

  return (
    <div className="min-h-screen bg-surface-base">
      <header className="border-b border-border-soft bg-surface-1/70 backdrop-blur">
        <div className="mx-auto flex max-w-page flex-wrap items-center gap-3 px-4 py-3 sm:gap-4 sm:px-6">
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-control bg-ink text-paper">
            <Sparkles size={18} aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-label uppercase tracking-[0.12em] text-cobalt/80">自主测验</p>
            <h1 className="text-page text-text-primary">拉取你的百分比与权重</h1>
            <p className="mt-0.5 text-caption text-text-secondary">
              学生先定义六维百分比，再与每所学校的数据百分比做匹配。
            </p>
          </div>
          <Link
            href="/assessment"
            className="ml-auto inline-flex h-control items-center gap-1.5 rounded-control border border-border-soft bg-surface-1 px-3 text-[12px] font-semibold text-text-primary transition hover:border-cobalt/40 hover:text-cobalt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
          >
            <Brain size={13} aria-hidden="true" /> 切到 AI 学校评估
          </Link>
        </div>
      </header>

      <main className="mx-auto grid max-w-page gap-6 px-4 py-5 lg:grid-cols-[360px_1fr] sm:px-6">
        <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <section className="rounded-card border border-border-soft bg-surface-1 p-4 shadow-pop">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <p className="text-label uppercase tracking-[0.12em] text-jade">学生百分比</p>
                <h2 className="mt-0.5 text-section text-text-primary">六维偏好</h2>
                <p className="mt-1 text-caption text-text-secondary">不是 AI 自动替你判断，而是由学生主动设定目标强度。</p>
              </div>
              <div className="rounded-control border border-jade/30 bg-jade/8 px-2.5 py-1 text-[11px] font-bold text-jade">均值 {averageTarget}%</div>
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
          <div className="rounded-card border border-border-soft bg-surface-1 p-4 shadow-pop">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-label uppercase tracking-[0.12em] text-persimmon">学校百分比</p>
                <h2 className="mt-0.5 text-page text-text-primary">匹配结果</h2>
                <p className="mt-1 text-caption text-text-secondary">
                  展示学校六维数据和学生目标之间的距离，不混入 AI 结论。
                </p>
              </div>
              <div className="inline-flex items-center gap-1.5 rounded-control border border-border-soft bg-surface-2 px-2.5 py-1 text-caption text-text-secondary">
                <Percent size={12} aria-hidden="true" /> Top {matches.length} / {universities.length}
              </div>
            </div>
            <div className="mt-3 flex items-start gap-2 rounded-control border border-persimmon/30 bg-persimmon/8 px-3 py-2 text-caption text-persimmon">
              <AlertTriangle size={13} aria-hidden="true" className="mt-0.5 shrink-0" />
              <p>区域指标（安全 / 就业 / 华人社区）当前仅在地图上作环境参考，未计入自主匹配分数；综合分仅基于「费用 + 排名」两个真实维度。</p>
            </div>
          </div>

          <div className="grid gap-3">
            {matches.map((university, index) => {
              const tone = university.match >= 86 ? "text-jade" : university.match >= 72 ? "text-cobalt" : "text-persimmon";
              // Stage 7A — read `costSummary.minimumUsd` instead of
              // the legacy `annualCostRmb` field that no longer exists.
              const minUsd = typeof university?.costSummary?.minimumUsd === "number" ? university.costSummary.minimumUsd : null;
              const costRmbForDisplay = minUsd !== null ? minUsd * STAGE5_RMB_PER_USD : null;
              const safetyLabel = "数据补充中"; // region metrics blocked at source
              const missingDims = (university.missing ?? []) as DimensionKey[];
              return (
                <article key={university.id} className="group overflow-hidden rounded-card border border-border-soft bg-surface-1 transition hover:-translate-y-0.5 hover:border-cobalt/40 hover:shadow-pop">
                  <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-start">
                    <div className="grid h-9 w-9 shrink-0 place-items-center rounded-control bg-ink text-[13px] font-bold text-paper">{index + 1}</div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-section text-text-primary">{university.chineseName}</h3>
                        <span className="text-caption text-text-muted">{university.name}</span>
                        <span className="rounded-control bg-cobalt/8 px-2 py-0.5 text-[11px] font-semibold text-cobalt">{university.rankingTier}</span>
                        {missingDims.length > 0 && <span className="rounded-control border border-border-soft bg-surface-2 px-2 py-0.5 text-[10px] font-medium text-text-secondary">部分维度数据不足</span>}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-caption text-text-secondary">
                        <span>{university.city}, {university.state}</span>
                        <span aria-hidden="true">·</span>
                        <span>{formatRmb(costRmbForDisplay)}/年</span>
                        <span aria-hidden="true">·</span>
                        <span>安全 {safetyLabel}</span>
                      </div>
                      <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                        {DIMENSIONS.map((dim) => {
                          const schoolValue = university.school[dim.key];
                          const studentValue = student[dim.key];
                          const isMissing = missingDims.includes(dim.key);
                          const gap = isMissing ? 0 : Math.abs(schoolValue - studentValue);
                          return (
                            <div key={dim.key} className="rounded-2xl bg-paper/80 p-2.5">
                              <div className="flex items-center justify-between text-[11px]"><span className="font-medium text-ink/60">{dim.label}</span><span className="font-semibold text-ink">{isMissing ? "数据补充中" : `校 ${schoolValue}% / 我 ${studentValue}%`}</span></div>
                              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-line/50">{!isMissing && <div className="h-full rounded-full bg-cobalt" style={{ width: schoolValue + "%" }} />}</div>
                              <div className="mt-1 text-[10px] text-ink/38">{isMissing ? "等待数据补充" : `差距 ${gap} · ${dim.helper}`}</div>
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
