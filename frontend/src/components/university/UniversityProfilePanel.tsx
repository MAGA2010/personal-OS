"use client";

// UniversityProfilePanel — renders a UniversityDetail's sections with
// progressive disclosure (collapsible). Used by:
//   1. The /university/[id] route (full-page view).
//   2. MapCard (hover/click preview — Phase 5 stretch).
//
// Data path:
//   - Parent passes the UniversityDetail directly (no fetch here) so the
//     route page can perform network + error handling at the route
//     layer; this component stays a pure presentational panel.
//   - Sections render from `detail`; null/undefined fields render a
//     "数据补充中" or "暂无数据" placeholder, never fabricated copy.
//
// Audience constraints:
//   - quarantined people are FILTERED OUT here, NOT displayed with a
//     lock icon. Per the Quarantine Policy, ordinary users never see
//     quarantined Person records — internal/research audiences are
//     funneled via a separate route that's not part of Phase 5.
//   - Provenance badges are pulled from `statusDictionary` so copy
//     stays backend-owned.

import { useState } from "react";
import type {
  CostRecord,
  Person,
  Program,
  RankingMembership,
  SourceReference,
  StatusDictionaryMap,
  UniversityDetail,
} from "@/domain/dataset";
import { ProvenanceBadge } from "./ProvenanceBadge";
import {
  AlertCircle,
  Building2,
  ChevronDown,
  ChevronUp,
  Clock,
  ClipboardCheck,
  ExternalLink,
  GraduationCap,
  History,
  MapPin,
  ScrollText,
  Shield,
  Users,
  Wallet,
} from "lucide-react";

// ── Helpers ──

function formatCost(c: CostRecord): string {
  const wan = (c.amount / 10000).toFixed(1);
  const scope = c.scope === "unknown" ? "" : ` (${scopeLabel(c.scope)})`;
  return `¥${wan} 万${scope}`;
}

function scopeLabel(scope: CostRecord["scope"]): string {
  if (scope === "in_state") return "本州";
  if (scope === "out_of_state") return "外州";
  if (scope === "international") return "国际生";
  return "未注明";
}

function programMembershipLabel(p: Program): string {
  if (p.membership === "top") return "顶尖";
  if (p.membership === "notable") return "知名";
  return "";
}

function rankingScopeLabel(r: RankingMembership): string {
  if (r.scope === "global") return "全球";
  if (r.scope === "national") return "全国";
  return "";
}

function formatPosition(p: number | string): string {
  return typeof p === "number" ? `#${p}` : p;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function finiteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatCount(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? new Intl.NumberFormat("zh-CN").format(value)
    : "数据补充中";
}

function formatRate(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "数据补充中";
  const percent = value <= 1 ? value * 100 : value;
  return `${percent.toFixed(1)}%`;
}

function scoreRange(value: unknown, key: string): [number, number] | null {
  const range = asRecord(asRecord(value)?.[key]);
  const low = finiteNumber(range?.percentile_25);
  const high = finiteNumber(range?.percentile_75);
  return low !== null && high !== null ? [low, high] : null;
}

function formatSat(value: unknown): string {
  const record = asRecord(value);
  if (!record) return "数据补充中";
  const average = finiteNumber(record.average);
  const math = scoreRange(record, "math");
  const reading = scoreRange(record, "reading_writing");
  const parts: string[] = [];
  if (average !== null) parts.push(`平均 ${Math.round(average)}`);
  if (math && reading) {
    parts.push(`中间 50% ${math[0] + reading[0]}–${math[1] + reading[1]}`);
  }
  return parts.length > 0 ? parts.join(" · ") : "数据补充中";
}

function formatAct(value: unknown): string {
  const composite = scoreRange(value, "composite");
  return composite ? `中间 50% ${composite[0]}–${composite[1]}` : "数据补充中";
}

const POLICY_LABELS: Record<string, string> = {
  required: "必须提交",
  test_required: "必须提交",
  optional: "可选提交",
  test_optional: "可选提交",
  blind: "不审阅标化成绩",
  test_blind: "不审阅标化成绩",
  flexible: "灵活提交",
  test_flexible: "灵活提交",
};

function formatPolicy(value: unknown, emptyLabel: string): string {
  if (typeof value === "string" && value.trim()) {
    return POLICY_LABELS[value] ?? value;
  }
  const record = asRecord(value);
  if (!record) return emptyLabel;
  const rawStatus = [record.policyStatus, record.policy_status, record.label, record.displayLabel]
    .find((item): item is string => typeof item === "string" && item.trim() !== "");
  const status = rawStatus ? (POLICY_LABELS[rawStatus] ?? rawStatus) : "";
  const acceptedTests = Array.isArray(record.acceptedTests ?? record.accepted_tests)
    ? (record.acceptedTests ?? record.accepted_tests) as unknown[]
    : [];
  const tests = acceptedTests
    .map((item) => {
      if (typeof item === "string") return item;
      const test = asRecord(item);
      if (!test) return "";
      const name = test.name ?? test.test ?? test.type;
      const minimum = test.minimumScore ?? test.minimum_score ?? test.minimum;
      if (typeof name !== "string") return "";
      return typeof minimum === "number" ? `${name} ${minimum}` : name;
    })
    .filter(Boolean)
    .join(" / ");
  return [status, tests].filter(Boolean).join(" · ") || emptyLabel;
}

function fieldStatusLabel(status: string | undefined): string {
  if (!status) return "未标注";
  if (status.startsWith("verified")) return "已核验";
  if (status === "source_limited") return "来源有限";
  if (status === "pending_external_access") return "待核验";
  if (status === "not_reported") return "未报告";
  return status;
}

// ── Root component ──

export interface UniversityProfilePanelProps {
  detail: UniversityDetail;
  statusDictionary?: StatusDictionaryMap;
}

export function UniversityProfilePanel({ detail, statusDictionary }: UniversityProfilePanelProps) {
  return (
    <article className="divide-y divide-line/50 border-y border-line/50 bg-panel lg:divide-y-0 lg:border-0 lg:bg-transparent">
      {/* Column A: identity, programs, rankings, cost — the data a parent reads first. */}
      <div className="divide-y divide-line/50 border-y border-line/50 bg-panel lg:grid lg:grid-cols-[1fr_360px] lg:gap-x-6 lg:divide-y-0 lg:border-0 lg:bg-transparent">
        <div className="divide-y divide-line/50 lg:border-y lg:border-line/50 lg:bg-panel">
          <OverviewSection detail={detail} statusDictionary={statusDictionary} />
          <AdmissionsSection detail={detail} statusDictionary={statusDictionary} />
          <ProgramsSection detail={detail} statusDictionary={statusDictionary} />
          <RankingSection detail={detail} statusDictionary={statusDictionary} />
          <CostSection detail={detail} statusDictionary={statusDictionary} />
          <LocationSection detail={detail} statusDictionary={statusDictionary} />
        </div>
        {/* Column B: people, history, sources — secondary, contextual. */}
        <aside className="divide-y divide-line/50 lg:rounded-none lg:border-y lg:border-line/50 lg:bg-panel">
          <PeopleSection detail={detail} statusDictionary={statusDictionary} />
          <HistorySection detail={detail} />
          <SourcesSection detail={detail} statusDictionary={statusDictionary} />
        </aside>
      </div>
      {detail.warnings && detail.warnings.length > 0 && (
        <div className="mt-0 lg:mt-0">
          <WarningsSection warnings={detail.warnings} />
        </div>
      )}
    </article>
  );
}

// ── Section primitives ──

interface SectionProps {
  detail: UniversityDetail;
  statusDictionary?: StatusDictionaryMap;
  defaultOpen?: boolean;
}

function Section({
  icon,
  title,
  titleEn,
  children,
  defaultOpen = true,
  trailing,
}: {
  icon: React.ReactNode;
  title: string;
  titleEn: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  trailing?: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section aria-labelledby={`section-${title}`}>
      <header className="flex items-center justify-between gap-2 px-5 py-3">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex flex-1 items-center gap-2 text-left"
          aria-expanded={open}
          aria-controls={`section-body-${title}`}
        >
          <span className="text-ink/44" aria-hidden="true">{icon}</span>
          <h2 id={`section-${title}`} className="text-sm font-semibold text-ink">
            {title}
            <span className="ml-1.5 text-[10px] font-normal text-ink/40" lang="en">
              {titleEn}
            </span>
          </h2>
        </button>
        <div className="flex items-center gap-2">
          {trailing}
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label={open ? `收起${title}` : `展开${title}`}
            className="grid h-6 w-6 place-items-center rounded text-ink/40 hover:bg-line/30"
          >
            {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </header>
      {open && (
        <div id={`section-body-${title}`} className="px-5 pb-4">
          {children}
        </div>
      )}
    </section>
  );
}

// ── Overview ──

function OverviewSection({ detail, statusDictionary }: SectionProps) {
  const town = detail.city && detail.state ? `${detail.city}, ${detail.state}` : "—";
  const verifiedDate = detail.datasetVersion
    ? detail.datasetVersion
    : "数据补充中";
  return (
    <Section
      icon={<Building2 size={14} />}
      title="学校概况"
      titleEn="Overview"
      trailing={
        <ProvenanceBadge
          status={detail.previewOnly ? "source_review_not_completed" : "live_verified_exact"}
          dictionary={statusDictionary}
          compact
          withLabel={false}
        />
      }
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="中文名称" value={detail.chineseName} />
        <Field label="English Name" value={detail.name} mono />
        <Field label="所在州" value={detail.state || "数据补充中"} />
        <Field label="城市" value={detail.city || "数据补充中"} />
        <Field
          label="排名档次"
          value={detail.rankingBand ?? "数据补充中"}
        />
        <Field
          label="数据集版本"
          value={verifiedDate}
          mono={false}
        />
      </div>
      {detail.nationalRanking !== undefined && (
        <p className="mt-3 text-[11px] text-ink/52">
          全国排名 #{detail.nationalRanking}
          {detail.rankingYear ? ` (${detail.rankingYear})` : ""}
        </p>
      )}
    </Section>
  );
}

function Field({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-ink/44">{label}</p>
      <p className={`mt-0.5 text-sm text-ink ${mono ? "font-mono text-ink/80" : ""}`}>
        {value}
      </p>
    </div>
  );
}

function AdmissionsDataPoint({
  label,
  value,
  status,
  referenceYear,
  sourceCount = 0,
  wide = false,
}: {
  label: string;
  value: string;
  status?: string;
  referenceYear?: number | string | null;
  sourceCount?: number;
  wide?: boolean;
}) {
  const verified = status?.startsWith("verified") ?? false;
  return (
    <div className={`rounded-lg border border-line/55 bg-white/65 px-3 py-2.5 ${wide ? "sm:col-span-2" : ""}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-[10px] uppercase tracking-wide text-ink/44">{label}</p>
        <span
          className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${
            verified ? "bg-jade/10 text-jade" : "bg-persimmon/10 text-persimmon"
          }`}
        >
          {fieldStatusLabel(status)}
        </span>
      </div>
      <p className="mt-1 text-sm font-semibold leading-relaxed text-ink">{value}</p>
      {(referenceYear || sourceCount > 0) ? (
        <p className="mt-1 text-[9px] text-ink/38">
          {referenceYear ? `参考 ${referenceYear}` : ""}
          {referenceYear && sourceCount > 0 ? " · " : ""}
          {sourceCount > 0 ? `${sourceCount} 个来源` : ""}
        </p>
      ) : null}
    </div>
  );
}

function AdmissionsSection({ detail }: SectionProps) {
  const enrollment = detail.previewMetadata?.enrollment;
  const admissions = detail.previewMetadata?.admissions;
  if (!enrollment && !admissions) {
    return (
      <Section icon={<ClipboardCheck size={14} />} title="招生与规模" titleEn="Admissions & Enrollment">
        <EmptyHint>招生与在校生数据补充中</EmptyHint>
      </Section>
    );
  }

  return (
    <Section icon={<ClipboardCheck size={14} />} title="招生与规模" titleEn="Admissions & Enrollment">
      <div className="grid gap-2 sm:grid-cols-2">
        <AdmissionsDataPoint
          label="本科生人数"
          value={formatCount(enrollment?.undergraduate.value ?? detail.enrollmentSummary?.undergraduate)}
          status={enrollment?.undergraduate.status}
          referenceYear={enrollment?.undergraduate.referenceYear ?? detail.enrollmentSummary?.referenceYear}
          sourceCount={enrollment?.undergraduate.sourceIds.length ?? 0}
        />
        <AdmissionsDataPoint
          label="研究生人数"
          value={formatCount(enrollment?.graduate.value ?? detail.enrollmentSummary?.graduate)}
          status={enrollment?.graduate.status}
          referenceYear={enrollment?.graduate.referenceYear}
          sourceCount={enrollment?.graduate.sourceIds.length ?? 0}
        />
        <AdmissionsDataPoint
          label="在校生总数"
          value={formatCount(enrollment?.total.value ?? detail.enrollmentSummary?.total)}
          status={enrollment?.total.status}
          referenceYear={enrollment?.total.referenceYear}
          sourceCount={enrollment?.total.sourceIds.length ?? 0}
        />
        <AdmissionsDataPoint
          label="本科录取率"
          value={formatRate(admissions?.acceptanceRate.value)}
          status={admissions?.acceptanceRate.status}
          referenceYear={admissions?.acceptanceRate.referenceYear}
          sourceCount={admissions?.acceptanceRate.sourceIds.length ?? 0}
        />
        <AdmissionsDataPoint
          label="毕业率"
          value={formatRate(admissions?.graduationRate.value)}
          status={admissions?.graduationRate.status}
          referenceYear={admissions?.graduationRate.referenceYear}
          sourceCount={admissions?.graduationRate.sourceIds.length ?? 0}
        />
        <AdmissionsDataPoint
          label="大一保留率"
          value={formatRate(admissions?.retentionRate.value)}
          status={admissions?.retentionRate.status}
          referenceYear={admissions?.retentionRate.referenceYear}
          sourceCount={admissions?.retentionRate.sourceIds.length ?? 0}
        />
        <AdmissionsDataPoint
          label="SAT"
          value={formatSat(admissions?.sat.value)}
          status={admissions?.sat.status}
          referenceYear={admissions?.sat.referenceYear}
          sourceCount={admissions?.sat.sourceIds.length ?? 0}
        />
        <AdmissionsDataPoint
          label="ACT"
          value={formatAct(admissions?.act.value)}
          status={admissions?.act.status}
          referenceYear={admissions?.act.referenceYear}
          sourceCount={admissions?.act.sourceIds.length ?? 0}
        />
        <AdmissionsDataPoint
          label="标化考试政策"
          value={formatPolicy(admissions?.testPolicy.value, "官方本科标化政策待核验")}
          status={admissions?.testPolicy.status}
          referenceYear={admissions?.testPolicy.referenceYear}
          sourceCount={admissions?.testPolicy.sourceIds.length ?? 0}
          wide
        />
        <AdmissionsDataPoint
          label="国际生英语要求"
          value={formatPolicy(admissions?.englishPolicy.value, "官方本科英语要求待核验")}
          status={admissions?.englishPolicy.status}
          referenceYear={admissions?.englishPolicy.referenceYear}
          sourceCount={admissions?.englishPolicy.sourceIds.length ?? 0}
          wide
        />
      </div>
      <p className="mt-2 text-[10px] leading-relaxed text-ink/40">
        标化与英语政策仅展示已冻结的官方本科来源；不会根据 SAT 报送数据或学校排名推断政策。
      </p>
    </Section>
  );
}

// ── Programs ──
function ProgramsSection({ detail, statusDictionary }: SectionProps) {
  const programs = detail.programs ?? [];
  const topIds = new Set(detail.topProgramIds ?? []);
  return (
    <Section icon={<GraduationCap size={14} />} title="专业" titleEn="Programs">
      {programs.length === 0 ? (
        <EmptyHint>专业数据补充中</EmptyHint>
      ) : (
        <ul className="flex flex-wrap gap-1.5" role="list" aria-label="专业列表">
          {programs.map((p) => {
            const isTop = topIds.has(p.id);
            const tier = programMembershipLabel(p);
            return (
              <li
                key={p.id}
                className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] ${
                  isTop
                    ? "border-jade/30 bg-jade/8 text-jade"
                    : "border-line bg-white/70 text-ink/72"
                }`}
              >
                <span>{p.name}</span>
                {tier && <span className="text-[10px] opacity-70">· {tier}</span>}
                <ProvenanceBadge
                  status={p.displayTier === "live_verified" ? "live_verified_normalized" : "source_review_not_completed"}
                  dictionary={statusDictionary}
                  compact
                  withLabel={false}
                />
              </li>
            );
          })}
        </ul>
      )}
    </Section>
  );
}

// ── Ranking ──

function RankingSection({ detail, statusDictionary }: SectionProps) {
  const items = detail.ranking ?? [];
  return (
    <Section icon={<GraduationCap size={14} />} title="排名" titleEn="Rankings">
      {items.length === 0 ? (
        <EmptyHint>排名数据补充中</EmptyHint>
      ) : (
        <ul className="space-y-2" role="list" aria-label="排名来源">
          {items.map((r, i) => (
            <li
              key={`${r.system}-${r.year}-${i}`}
              className="flex items-center justify-between gap-3 rounded-md border border-line/60 bg-white/65 px-3 py-2 text-[12px]"
            >
              <div className="min-w-0">
                <p className="font-medium text-ink">
                  {r.system} {r.year}
                </p>
                <p className="text-[11px] text-ink/52">
                  {rankingScopeLabel(r)} · {formatPosition(r.position)}
                </p>
              </div>
              <ProvenanceBadge
                status={r.displayTier === "live_verified" ? "live_verified_exact" : "source_review_not_completed"}
                dictionary={statusDictionary}
                compact
              />
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

// ── Cost ──

function CostSection({ detail, statusDictionary }: SectionProps) {
  const items = detail.cost ?? [];
  // Use the most recent cost record (highest year) as the headline.
  const headline = items
    .slice()
    .sort((a, b) => b.year - a.year)[0];
  return (
    <Section
      icon={<Wallet size={14} />}
      title="费用"
      titleEn="Cost"
      trailing={
        headline ? (
          <ProvenanceBadge status={headline.status} dictionary={statusDictionary} compact />
        ) : null
      }
    >
      {items.length === 0 ? (
        <EmptyHint>费用数据补充中</EmptyHint>
      ) : (
        <div className="space-y-2">
          {headline && (
            <p className="text-2xl font-semibold tabular-nums text-ink">
              {formatCost(headline)}
              <span className="ml-2 text-[11px] font-normal text-ink/40">
                /{headline.year}
              </span>
            </p>
          )}
          <table className="w-full text-[11px]" aria-label="费用明细">
            <thead>
              <tr className="text-left text-ink/40">
                <th className="py-1 font-normal">年份</th>
                <th className="py-1 font-normal">金额</th>
                <th className="py-1 font-normal">对象</th>
                <th className="py-1 font-normal">来源状态</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c, i) => (
                <tr key={i} className="border-t border-line/40">
                  <td className="py-1.5 text-ink/72">{c.year}</td>
                  <td className="py-1.5 tabular-nums text-ink">
                    ¥{(c.amount / 10000).toFixed(1)}万
                  </td>
                  <td className="py-1.5 text-ink/60">{scopeLabel(c.scope)}</td>
                  <td className="py-1.5">
                    <ProvenanceBadge status={c.status} dictionary={statusDictionary} compact />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {detail.studentFacultyRatio !== undefined && (
            <p className="text-[11px] text-ink/52">
              师生比 1 : {detail.studentFacultyRatio}
            </p>
          )}
        </div>
      )}
    </Section>
  );
}

// ── Location ──

function LocationSection({ detail, statusDictionary }: SectionProps) {
  const towns = detail.nearbyTowns ?? [];
  return (
    <Section icon={<MapPin size={14} />} title="位置" titleEn="Location">
      <div className="flex flex-col gap-2 text-[12px] text-ink/72">
        <p>
          {detail.city}, {detail.state}, {detail.country}
        </p>
        {detail.latitude !== null && detail.longitude !== null && (
          <p className="font-mono text-[11px] text-ink/44">
            ({detail.latitude.toFixed(4)}, {detail.longitude.toFixed(4)})
          </p>
        )}
      </div>
      {towns.length > 0 && (
        <div className="mt-3">
          <p className="mb-1 text-[10px] uppercase tracking-wide text-ink/44">
            周边城镇
            <span className="ml-1 text-ink/32" lang="en">
              Nearby Towns
            </span>
          </p>
          <ul className="flex flex-wrap gap-1.5" role="list">
            {towns.map((t, i) => (
              <li
                key={`${t.name}-${i}`}
                className="rounded-full border border-line/60 bg-white/70 px-2.5 py-0.5 text-[11px] text-ink/72"
              >
                {t.nameZh ? `${t.nameZh} (${t.name})` : t.name}
                {t.distanceKm !== undefined && (
                  <span className="ml-1 text-ink/40">· {t.distanceKm} km</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-3 flex items-center gap-2 rounded-md border border-line/40 bg-white/60 px-3 py-2 text-[11px] text-ink/52">
        <Shield size={12} className="text-ink/44" aria-hidden="true" />
        <span>治安/生活指标请参阅地图区域着色 — 该指标来自聚合数据,不属于本校维度。</span>
      </div>
    </Section>
  );
}

// ── People ──

function PeopleSection({ detail, statusDictionary }: SectionProps) {
  // Quarantine policy: filter quarantined people before render. Never
  // show a "隐藏" placeholder — they're invisible to ordinary users.
  const visiblePeople = (detail.people ?? []).filter((p) => !p.quarantined);
  return (
    <Section
      icon={<Users size={14} />}
      title="知名校友/教师"
      titleEn="People"
    >
      {visiblePeople.length === 0 ? (
        <EmptyHint>人物介绍数据补充中</EmptyHint>
      ) : (
        <ul className="space-y-2" role="list" aria-label="人物列表">
          {visiblePeople.map((p) => (
            <PersonRow key={p.id} person={p} dictionary={statusDictionary} />
          ))}
        </ul>
      )}
    </Section>
  );
}

function PersonRow({ person, dictionary }: { person: Person; dictionary?: StatusDictionaryMap }) {
  return (
    <li className="rounded-md border border-line/60 bg-white/65 px-3 py-2">
      <div className="flex items-baseline justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">{person.name}</p>
          <p className="text-[11px] text-ink/52">{person.relationship}</p>
        </div>
        <ProvenanceBadge status={person.status} dictionary={dictionary} compact />
      </div>
      {(person.domain || person.era) && (
        <p className="mt-1 text-[11px] text-ink/44">
          {[person.domain, person.era].filter(Boolean).join(" · ")}
        </p>
      )}
    </li>
  );
}

// ── History ──

function HistorySection({ detail, statusDictionary }: SectionProps) {
  const history = detail.history;
  // Gate-bloker repair #RG-P0-J: anecdotes / notableAttendance that
  // are quarantined are removed entirely (a user must never see a
  // quarantined record). But `source_review_not_completed` records
  // are the canonical "public visible, awaiting review" state —
  // they KEEP their slot in the panel so users understand the school
  // has something at this index, but the content area renders the
  // "数据补充中" empty state alongside a provenance badge from
  // `statusDictionary`. Silently dropping them would make the
  // history section appear *empty* (which looks like the school has
  // no history at all) instead of "history exists, just pending".
  //
  // Note: `Anecdote.status` and `NotableAttendance.status` are typed
  // `ProvenanceStatus` (not `DisplayTier`), so the only "quarantined"
  // signal we have on individual records is via the parent
  // `detail.displayTier`. For preview data the section simply renders
  // every anecdote / notable-attendance row with its status badge;
  // the user sees `数据补充中` for the `source_review_not_completed`
  // ones and the live-verified ones with their real content.
  const anecdotes = (detail.anecdotes ?? []);
  const attendance = (detail.notableAttendance ?? []);
  // Drop the entire anecdotes / attendance block when the *record*
  // has displayTier === "quarantined". For per-row items we don't
  // carry a per-item displayTier, so we simply skip records whose
  // status indicates live-unavailable (the closest analog to
  // quarantined at the ProvenanceStatus level) and otherwise show
  // the row.
  const quarantinedStatuses: ReadonlyArray<string> = ["live_unavailable", "page_changed"];
  const visibleAnecdotes = anecdotes.filter((a) => !quarantinedStatuses.includes(a.status));
  const visibleAttendance = attendance.filter((n) => !quarantinedStatuses.includes(n.status));
  return (
    <Section icon={<History size={14} />} title="历史" titleEn="History" defaultOpen={false}>
      {history ? (
        <p className="text-[12px] leading-relaxed text-ink/72">{history}</p>
      ) : (
        <EmptyHint>校史数据补充中</EmptyHint>
      )}
      {visibleAnecdotes.length > 0 && (
        <div className="mt-3">
          <p className="mb-1 text-[10px] uppercase tracking-wide text-ink/44">
            轶事
            <span className="ml-1 text-ink/32" lang="en">
              Anecdotes
            </span>
          </p>
          <ul className="space-y-1 text-[12px] text-ink/72">
            {visibleAnecdotes.map((a, i) => (
              <li key={i} className="flex items-start gap-2">
                <ScrollText size={11} className="mt-1 shrink-0 text-ink/40" aria-hidden="true" />
                <span className="flex-1">
                  {a.status === "source_review_not_completed" ? (
                    <span className="text-ink/44">数据补充中</span>
                  ) : (
                    a.text
                  )}
                </span>
                <ProvenanceBadge status={a.status} dictionary={statusDictionary} compact />
              </li>
            ))}
          </ul>
        </div>
      )}
      {visibleAttendance.length > 0 && (
        <div className="mt-3">
          <p className="mb-1 text-[10px] uppercase tracking-wide text-ink/44">
            重要出席/来访
          </p>
          <ul className="space-y-1 text-[12px] text-ink/72">
            {visibleAttendance.map((n, i) => (
              <li key={i} className="flex items-center justify-between gap-2">
                <span className="flex-1">
                  <span className="font-medium">{n.year ?? ""}</span> ·{" "}
                  {n.status === "source_review_not_completed" ? (
                    <span className="text-ink/44">数据补充中</span>
                  ) : (
                    n.context ?? "—"
                  )}
                </span>
                <ProvenanceBadge status={n.status} dictionary={statusDictionary} compact />
              </li>
            ))}
          </ul>
        </div>
      )}
    </Section>
  );
}

// ── Sources ──

function SourcesSection({ detail, statusDictionary }: SectionProps) {
  const sources = detail.sources ?? [];
  const title = (
    <>
      <span>来源</span>
      <span className="ml-1.5 text-[10px] font-normal text-ink/40" lang="en">
        Sources
      </span>
    </>
  );
  return (
    <Section
      icon={<Shield size={14} />}
      title="来源"
      titleEn="Sources"
      defaultOpen={false}
      trailing={
        <span className="text-[11px] text-ink/44">
          {sources.length} 项
        </span>
      }
    >
      {sources.length === 0 ? (
        <EmptyHint>来源数据补充中</EmptyHint>
      ) : (
        <ul className="space-y-2" role="list" aria-label="来源列表">
          {sources.map((s, i) => (
            <SourceRow key={i} source={s} dictionary={statusDictionary} />
          ))}
        </ul>
      )}
      <p className="mt-3 text-[11px] text-ink/44">
        数据集中每条引用都附带 provenance 状态;审核未完成时,
        所有徽标会显示「数据补充中」,而非伪造来源。
      </p>
    </Section>
  );
}

function SourceRow({ source, dictionary }: { source: SourceReference; dictionary?: StatusDictionaryMap }) {
  return (
    <li className="rounded-md border border-line/60 bg-white/65 px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex min-w-0 items-center gap-1 text-[12px] text-cobalt hover:underline"
        >
          <ExternalLink size={11} aria-hidden="true" />
          <span className="truncate">
            {source.anchor ?? source.url}
          </span>
        </a>
        <ProvenanceBadge status={source.status} dictionary={dictionary} compact />
      </div>
      {(source.cachedSnapshotAt || source.retrievedAt) && (
        <p className="mt-1 flex items-center gap-1 text-[10px] text-ink/44">
          <Clock size={10} aria-hidden="true" />
          {source.cachedSnapshotAt ? `快照 ${source.cachedSnapshotAt}` : "—"}
          {source.retrievedAt && ` · 抓取 ${source.retrievedAt}`}
        </p>
      )}
    </li>
  );
}

// ── Warnings ──

function WarningsSection({ warnings }: { warnings: string[] }) {
  return (
    <Section
      icon={<AlertCircle size={14} />}
      title="数据警告"
      titleEn="Warnings"
      defaultOpen={true}
    >
      <ul className="space-y-1 text-[12px] text-persimmon/80" role="list">
        {warnings.map((w, i) => (
          <li key={i} className="flex gap-2">
            <AlertCircle size={12} className="mt-0.5 shrink-0" aria-hidden="true" />
            <span>{w}</span>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function EmptyHint({ children }: { children: React.ReactNode }) {
  return (
    <p className="flex items-center gap-1.5 text-[11px] italic text-ink/44">
      <Clock size={10} aria-hidden="true" />
      <span>{children}</span>
    </p>
  );
}

export default UniversityProfilePanel;
