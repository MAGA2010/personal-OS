"use client";

// Stage 7A — UniversityProfile panel.
//
// Replaces the legacy UniversityCard as the on-map detail panel. Renders
// from the canonical `UniversitySummary` shape (no `?? 0` fabrication)
// plus optional detail via `useUniversityDetail`. Missing fields show
// the "未报告" / "数据补充中" empty state — never 0/N/A.
//
// Designed to be rendered as an edge-docked popover (desktop right,
// mobile bottom sheet). Itself is non-modal: it never blocks map
// dragging or hover. Closes on Escape, on click-empty (handled by
// MapShell), and on explicit close button.

import { useEffect, useState } from "react";
import { X, GraduationCap, MapPin, DollarSign, Shield, Users, ExternalLink, Sparkles, Building2, BookOpen, AlertTriangle } from "lucide-react";
import { useDataSource } from "@/services/data-source-provider";
import { useUniversityDetail } from "@/hooks/use-data-source";
import { tuitionRmbFromSummary, type legacyPoiAnnualCostLabel } from "@/lib/legacy-mappers";
import type { UniversitySummary } from "@/domain/dataset";

export interface UniversityProfileProps {
  /** The selected university summary (canonical shape). */
  summary: UniversitySummary;
  /** Whether this university is currently in the user's compare set. */
  inCompare?: boolean;
  /** Add to compare (max 3 enforced by caller). */
  onAddToCompare?: () => void;
  /** Remove from compare. */
  onRemoveFromCompare?: () => void;
  /** Open the dedicated /university/[id] page. */
  onViewProfile?: () => void;
  /** Close the panel (escape / close button / click empty). */
  onClose: () => void;
}

export function UniversityProfile({
  summary,
  inCompare = false,
  onAddToCompare,
  onRemoveFromCompare,
  onViewProfile,
  onClose,
}: UniversityProfileProps) {
  const dataSource = useDataSource();
  const detailState = useUniversityDetail(dataSource, summary.id);
  const detail = detailState.state.status === "ready" ? detailState.state.data : null;

  // Close on Escape.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const tuition = tuitionRmbFromSummary(summary);
  const costLabel = tuition !== null ? `¥${Math.round(tuition / 10000)}万/年` : "未报告";
  const rankingTier = summary.rankingSummary?.rankingTier ?? summary.rankingTier ?? null;
  const rankingLabel = summary.rankingSummary?.rankingLabel ?? "未在当前排名范围";
  const nationalRank = summary.rankingSummary?.nationalRank ?? null;
  const warnings = summary.qualitySummary?.warningCodes ?? [];

  // Detail-only fields (programs, cost records, nearby towns).
  // NOTE: the Preview Bundle currently returns the legacy
  // UniversityDetail shape (programs / cost / ranking / etc.) but
  // does NOT yet expose the PreviewMetadata's admissions/enrollment
  // blocks. We read both safely: when the blocks are present we
  // surface them; otherwise we render the empty-state label.
  // `detail` itself can be null while the detail hook is still
  // loading; treat null as the empty object so `.admissions?.…` and
  // similar chains don't throw before the optional chain can run.
  const detailAny = (detail ?? {}) as unknown as {
    programs?: Array<{ id: string; name: string; category?: string; rank?: number; membership?: "top" | "notable"; displayTier?: string }>;
    cost?: Array<{ amount: number; currency: string; year: number; components?: { tuition?: boolean; roomBoard?: boolean; mandatoryFees?: boolean } }>;
    nearbyTowns?: Array<{ name: string; nameZh?: string; distanceKm?: number }>;
    admissions?: { acceptanceRate?: { value: number | null; status?: string } };
    enrollment?: { undergraduate?: { value: number | null; status?: string } };
    allMajors?: Array<{ name: string; displayName: string }>;
  };
  const acceptanceRate = detailAny.admissions?.acceptanceRate?.value ?? null;
  const acceptanceStatus = detailAny.admissions?.acceptanceRate?.status ?? null;
  const undergradCount = detailAny.enrollment?.undergraduate?.value ?? null;
  const undergradStatus = detailAny.enrollment?.undergraduate?.status ?? null;
  const programs = detailAny.programs ?? [];
  const majors = detailAny.allMajors ?? [];

  function emptyReport(value: number | string | null | undefined, fallback: string): string {
    if (value === null || value === undefined) return fallback;
    if (typeof value === "number" && (!Number.isFinite(value) || value <= 0)) return fallback;
    if (typeof value === "string" && value.trim() === "") return fallback;
    return String(value);
  }

  return (
    <div
      role="dialog"
      aria-label={`${summary.chineseName || summary.name} 详细信息`}
      className="pointer-events-auto flex h-full w-full flex-col overflow-hidden rounded-xl border border-line/60 bg-panel text-ink shadow-panel"
    >
      {/* ── Header ── */}
      <header className="flex shrink-0 items-start gap-3 border-b border-line/50 px-4 py-3">
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-sm font-semibold text-ink">
            {summary.chineseName || summary.name || "未提供名称"}
          </h2>
          {summary.name && summary.chineseName !== summary.name && (
            <p className="truncate text-xs text-ink/55" lang="en">{summary.name}</p>
          )}
          <p className="mt-0.5 flex items-center gap-1 text-[11px] text-ink/48">
            <MapPin size={10} aria-hidden="true" />
            <span>{emptyReport(summary.city, "未报告")}</span>
            {summary.state ? (
              <>
                <span className="mx-0.5 text-ink/24" aria-hidden="true">·</span>
                <span>{emptyReport(summary.state, "未报告")}</span>
              </>
            ) : null}
          </p>
        </div>
        {rankingTier && (
          <span className="shrink-0 rounded-full border border-line/60 bg-paper px-2 py-0.5 text-[10px] font-medium text-ink/70">
            {rankingTier}
          </span>
        )}
        <button
          type="button"
          onClick={onClose}
          aria-label="关闭学校详情"
          className="grid h-6 w-6 shrink-0 place-items-center rounded text-ink/40 transition-colors hover:bg-line/30 hover:text-ink"
        >
          <X size={14} />
        </button>
      </header>

      {/* ── Scrollable content ── */}
      <div className="flex-1 overflow-y-auto overscroll-contain">
        {/* Key facts 2x2 grid */}
        <section className="grid grid-cols-2 gap-px border-b border-line/50 bg-line/20 text-[11px]">
          <Stat icon={<DollarSign size={12} aria-hidden="true" />} label="年费用" labelEn="Cost" value={costLabel} />
          <Stat icon={<GraduationCap size={12} aria-hidden="true" />} label="排名" labelEn="Rank" value={nationalRank !== null ? `No.${nationalRank}` : rankingLabel} />
          <Stat icon={<BookOpen size={12} aria-hidden="true" />} label="录取率" labelEn="Acceptance" value={
            acceptanceRate !== null && Number.isFinite(acceptanceRate)
              ? `${(acceptanceRate * 100).toFixed(1)}%`
              : emptyReport(acceptanceStatus, "未报告")
          } />
          <Stat icon={<Users size={12} aria-hidden="true" />} label="本科人数" labelEn="Undergrad" value={
            undergradCount !== null && Number.isFinite(undergradCount) && undergradCount > 0
              ? `${undergradCount.toLocaleString()}`
              : emptyReport(undergradStatus, "未报告")
          } />
        </section>

        {/* Detail area */}
        <section className="space-y-3 px-4 py-3 text-[12px]">
          {warnings.length > 0 && (
            <div className="rounded-lg border border-persimmon/30 bg-persimmon/10 p-2.5 text-[11px] leading-relaxed text-persimmon">
              <div className="flex items-center gap-1 font-semibold">
                <AlertTriangle size={11} aria-hidden="true" /> 数据警示
              </div>
              <p className="mt-1">
                当前已记录 {warnings.length} 项数据来源待补强。具体字段请以「未报告」标识为准。
              </p>
            </div>
          )}

          {/* Majors */}
          <div>
            <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold text-ink/72">
              <Building2 size={11} aria-hidden="true" />
              <span>热门专业 / Programs</span>
            </div>
            {majors.length === 0 && programs.length === 0 ? (
              <p className="text-[11px] italic text-ink/40">未报告</p>
            ) : (
              <ul className="flex flex-wrap gap-1.5">
                {(majors.length > 0 ? majors : programs.map((p) => ({ name: p.id, displayName: p.name }))).slice(0, 8).map((m) => (
                  <li key={m.name} className="rounded-full border border-line/60 bg-white/60 px-2 py-0.5 text-[10px] text-ink/72">
                    {m.displayName}
                  </li>
                ))}
                {(majors.length > 8 || programs.length > 8) && (
                  <li className="rounded-full bg-ink/5 px-2 py-0.5 text-[10px] text-ink/50">+{Math.max(0, (majors.length || programs.length) - 8)}</li>
                )}
              </ul>
            )}
          </div>

          {/* Prose block: ranking summary, plus a "what we report" footer. */}
          <div className="rounded-lg bg-paper/80 p-2.5 text-[11px] leading-relaxed text-ink/65">
            <p>{emptyReport(rankingLabel, "未在当前排名范围")}。地理坐标 {(summary.latitude ?? "未报告").toString()} / {(summary.longitude ?? "未报告").toString()}。</p>
            {detail?.warnings && detail.warnings.length > 0 && (
              <ul className="mt-1.5 list-disc space-y-0.5 pl-4 text-[10px] text-ink/50">
                {detail.warnings.slice(0, 3).map((w) => <li key={w}>{w}</li>)}
              </ul>
            )}
          </div>
        </section>
      </div>

      {/* ── Action footer ── */}
      <footer className="flex shrink-0 gap-2 border-t border-line/50 bg-paper/60 px-3 py-2.5">
        <button
          type="button"
          disabled={!onAddToCompare && !onRemoveFromCompare}
          onClick={() => (inCompare ? onRemoveFromCompare?.() : onAddToCompare?.())}
          className={
            "inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border px-3 py-1.5 text-[11px] font-semibold transition " +
            (inCompare
              ? "border-jade/40 bg-jade/8 text-jade hover:bg-jade/12"
              : "border-line/60 bg-white text-ink/72 hover:border-cobalt/30 hover:bg-cobalt/5 hover:text-cobalt")
          }
        >
          {inCompare ? (
            <>
              <CheckSmall /> 已加入对比
            </>
          ) : (
            <>
              <Sparkles size={12} aria-hidden="true" /> 加入对比
            </>
          )}
        </button>
        <button
          type="button"
          onClick={onViewProfile}
          className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-cobalt/30 bg-cobalt/5 px-3 py-1.5 text-[11px] font-semibold text-cobalt transition hover:border-cobalt/45 hover:bg-cobalt/10"
        >
          <ExternalLink size={12} aria-hidden="true" /> 完整档案
        </button>
      </footer>
    </div>
  );
}

function Stat({ icon, label, labelEn, value }: { icon: React.ReactNode; label: string; labelEn: string; value: string }) {
  return (
    <div className="flex items-start gap-2 bg-panel px-3 py-2">
      <div className="mt-0.5 text-ink/40">{icon}</div>
      <div className="min-w-0">
        <p className="text-[9px] font-medium uppercase tracking-wide text-ink/45">
          {label}<span className="ml-0.5 font-normal normal-case text-ink/30" lang="en">{labelEn}</span>
        </p>
        <p className="mt-0.5 truncate text-[12px] font-semibold text-ink" title={value}>{value}</p>
      </div>
    </div>
  );
}

function CheckSmall() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

export default UniversityProfile;

// Re-export the cost label helper for backwards compatibility with
// existing callers (Calculator, ComparePanel) that imported from
// legacy-mappers.
export type { legacyPoiAnnualCostLabel };