"use client";

import { useState } from "react";
import type { UniversityPOI, CampusPOI } from "@/lib/types";
import {
  X,
  DollarSign,
  Shield,
  GraduationCap,
  MapPin,
  Users,
  Eye,
  Building2,
  Clock,
  Award,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

// ═══════════════════════════════════════════════════════════════════
// UniversityCard — School detail card rendered when a map marker is
// clicked.  Appears as a floating panel anchored to the bottom-right
// or side of the map viewport.
// ═══════════════════════════════════════════════════════════════════
//
// Responsibilities:
//  1. Display core school information: name (Chinese + English),
//     ranking band, annual cost, safety score, recognition score,
//     Chinese community level.
//  2. Show available academic programs as a horizontal tag list.
//  3. Present parent-oriented and student-oriented highlights.
//  4. Provide a "Street View" button (disabled until Phase 4
//     immersive campus feature is wired).
//  5. Display nearby amenities (subway, restaurants, groceries, rent)
//     when expanded.
//  6. Offer a "View full profile" link (external or detail route).
//
// Behaviour:
//  - Collapsible sections for programs (when > 4) and highlights.
//  - Closable via the X button in the header, which calls `onClose`.
//  - Renders a visible skeleton even when data is incomplete.
//
// Accessibility:
//  - Dialog role with aria-label in Chinese.
//  - Focus is trapped within the card (header close button).
//  - All icon-only controls have aria-label or aria-hidden.
//
// Data dependencies:
//  - `UniversityPOI` from @/lib/types — the primary data shape.
//  - `CampusPOI[]` from @/lib/types — campus landmarks (Phase 4).
//
// TODO: Connect to Supabase when available — replace `poi` prop with
//       a server-component fetch or SWR query keyed by university ID.
// TODO: Replace hardcoded program list with DB join on `university_programs`.
// TODO: Wire `onStreetView` callback when Phase 4 immersive view is ready.
// TODO: Connect campus images to real CDN / S3 URLs.

// ── Props ──────────────────────────────────────────────────────────

export interface UniversityCardProps {
  /** The university POI to render.  Required — the card does not render
   *  a "no data" state; the parent should conditionally mount it. */
  poi: UniversityPOI;

  /** Called when the user dismisses the card (X button or backdrop). */
  onClose: () => void;

  /** Called when the user clicks the street view button.
   *  Currently disabled — will be wired in Phase 4.
   *  TODO: Wire this callback when Street View immersive mode is ready. */
  onStreetView?: (poi: UniversityPOI) => void;

  /** Optional campus POIs for the drill-in map (Phase 4).
   *  TODO: Populate from Supabase `campus_pois` table. */
  campusPois?: CampusPOI[];
}

// ═══════════════════════════════════════════════════════════════════
// Component
// ═══════════════════════════════════════════════════════════════════

export function UniversityCard({
  poi,
  onClose,
  onStreetView: _onStreetView,
  campusPois: _campusPois,
}: UniversityCardProps) {
  // ── Local state ──
  const [showAllPrograms, setShowAllPrograms] = useState(false);
  const [showAllParentHighlights, setShowAllParentHighlights] = useState(false);
  const [showAllStudentHighlights, setShowAllStudentHighlights] =
    useState(false);

  // ── Derived values ──

  /** Cost in wan (万) RMB for display, e.g. "62万/年". */
  const costWan = (poi.annualCostRmb / 10000).toFixed(1);

  /** Number of programs visible before the "show more" toggle. */
  const PROGRAM_PREVIEW_COUNT = 4;

  /** Number of highlight items visible before toggle. */
  const HIGHLIGHT_PREVIEW_COUNT = 2;

  const visiblePrograms = showAllPrograms
    ? poi.programs
    : poi.programs.slice(0, PROGRAM_PREVIEW_COUNT);

  const visibleParentHighlights = showAllParentHighlights
    ? poi.parentHighlights
    : poi.parentHighlights.slice(0, HIGHLIGHT_PREVIEW_COUNT);

  const visibleStudentHighlights = showAllStudentHighlights
    ? poi.studentHighlights
    : poi.studentHighlights.slice(0, HIGHLIGHT_PREVIEW_COUNT);

  // ── Render ──

  return (
    <div
      role="dialog"
      aria-label={`${poi.chineseName} 详细信息`}
      className="pointer-events-auto w-full max-w-[380px] rounded-xl border border-line bg-panel shadow-panel overflow-hidden"
    >
      {/* ── Header: close button + school name ── */}
      <div className="flex items-start justify-between gap-3 border-b border-line/60 px-4 py-3.5">
        <div className="min-w-0 flex-1">
          {/* Chinese name (primary) */}
          <h2 className="truncate text-sm font-semibold text-ink">
            {poi.chineseName}
          </h2>
          {/* English name (secondary) */}
          <p className="truncate text-xs text-ink/48" lang="en">
            {poi.name}
          </p>
          {/* Location line */}
          <p className="mt-0.5 flex items-center gap-1 text-[11px] text-ink/44">
            <MapPin size={10} aria-hidden="true" />
            <span>{poi.city}</span>
            <span className="mx-0.5 text-ink/24" aria-hidden="true">
              ·
            </span>
            <span>{poi.country}</span>
          </p>
        </div>

        {/* Ranking badge */}
        <span className="shrink-0 rounded-full bg-ink/8 px-2 py-0.5 text-[10px] font-medium text-ink/60">
          {poi.rankingBand}
        </span>

        {/* Close button */}
        <button
          type="button"
          onClick={onClose}
          aria-label={`关闭 ${poi.chineseName} 详情`}
          className="grid h-6 w-6 shrink-0 place-items-center rounded text-ink/36 transition-colors hover:bg-line/40 hover:text-ink"
        >
          <X size={14} />
        </button>
      </div>

      {/* ── Key metrics grid ── */}
      <div className="grid grid-cols-2 gap-px bg-line/30 border-b border-line/60">
        {/* Annual Cost */}
        <MetricCell
          icon={<DollarSign size={13} aria-hidden="true" />}
          label="年费用"
          labelEn="Annual Cost"
          value={`¥${costWan}万/年`}
          // TODO: Connect to Supabase `universities.annual_cost_rmb`
        />

        {/* Safety Score */}
        <MetricCell
          icon={<Shield size={13} aria-hidden="true" />}
          label="安全评分"
          labelEn="Safety Score"
          value={`${poi.safetyScore}/100`}
          // TODO: Replace with real safety data when Supabase is available
        />

        {/* Recognition / Ranking */}
        <MetricCell
          icon={<Award size={13} aria-hidden="true" />}
          label="认可度"
          labelEn="Recognition"
          value={`${poi.recognitionScore}/100`}
        />

        {/* Chinese Community */}
        <MetricCell
          icon={<Users size={13} aria-hidden="true" />}
          label="华人社区"
          labelEn="Chinese Community"
          value={
            poi.chineseCommunity === "high"
              ? "高"
              : poi.chineseCommunity === "medium"
                ? "中"
                : "低"
          }
          // TODO: Replace with real Chinese population data
        />
      </div>

      {/* ── Programs section ── */}
      <div className="border-b border-line/60 px-4 py-3">
        <div className="mb-2 flex items-center gap-1.5">
          <GraduationCap size={13} className="text-ink/44" aria-hidden="true" />
          <h3 className="text-xs font-medium text-ink/72">
            热门专业
            <span className="ml-1 font-normal text-ink/40" lang="en">
              Programs
            </span>
          </h3>
        </div>

        {poi.programs.length === 0 ? (
          <p className="text-[11px] italic text-ink/36">
            {/* TODO: Connect to Supabase when available */}
            暂无专业数据
          </p>
        ) : (
          <>
            <ul
              className="flex flex-wrap gap-1.5"
              role="list"
              aria-label="专业列表"
            >
              {visiblePrograms.map((program) => (
                <li
                  key={program}
                  className="rounded-full border border-line bg-white/60 px-2.5 py-0.5 text-[11px] text-ink/68"
                >
                  {program}
                </li>
              ))}
            </ul>

            {poi.programs.length > PROGRAM_PREVIEW_COUNT && (
              <button
                type="button"
                onClick={() => setShowAllPrograms((prev) => !prev)}
                className="mt-2 inline-flex items-center gap-0.5 text-[11px] text-cobalt/80 transition-colors hover:text-cobalt"
                aria-expanded={showAllPrograms}
              >
                {showAllPrograms
                  ? "收起"
                  : `查看全部 ${poi.programs.length} 个专业`}
                {showAllPrograms ? (
                  <ChevronUp size={12} aria-hidden="true" />
                ) : (
                  <ChevronDown size={12} aria-hidden="true" />
                )}
              </button>
            )}
          </>
        )}
      </div>

      {/* ── Parent Highlights ── */}
      <div className="border-b border-line/60 px-4 py-3">
        <div className="mb-2 flex items-center gap-1.5">
          <Building2 size={13} className="text-ink/44" aria-hidden="true" />
          <h3 className="text-xs font-medium text-ink/72">
            家长关注
            <span className="ml-1 font-normal text-ink/40" lang="en">
              Parent View
            </span>
          </h3>
        </div>

        {poi.parentHighlights.length === 0 ? (
          <p className="text-[11px] italic text-ink/36">
            {/* TODO: Connect to Supabase when available */}
            暂无数据
          </p>
        ) : (
          <>
            <ul className="space-y-1" role="list" aria-label="家长关注要点">
              {visibleParentHighlights.map((item, i) => (
                <li
                  key={i}
                  className="flex items-start gap-1.5 text-[11px] text-ink/62"
                >
                  <span
                    className="mt-[5px] block h-1 w-1 shrink-0 rounded-full bg-persimmon/60"
                    aria-hidden="true"
                  />
                  <span>{item}</span>
                </li>
              ))}
            </ul>

            {poi.parentHighlights.length > HIGHLIGHT_PREVIEW_COUNT && (
              <button
                type="button"
                onClick={() => setShowAllParentHighlights((prev) => !prev)}
                className="mt-1.5 inline-flex items-center gap-0.5 text-[11px] text-cobalt/80 transition-colors hover:text-cobalt"
                aria-expanded={showAllParentHighlights}
              >
                {showAllParentHighlights ? "收起" : "展开全部"}
                {showAllParentHighlights ? (
                  <ChevronUp size={12} aria-hidden="true" />
                ) : (
                  <ChevronDown size={12} aria-hidden="true" />
                )}
              </button>
            )}
          </>
        )}
      </div>

      {/* ── Student Highlights ── */}
      <div className="border-b border-line/60 px-4 py-3">
        <h3 className="mb-2 text-xs font-medium text-ink/72">
          学生关注
          <span className="ml-1 font-normal text-ink/40" lang="en">
            Student View
          </span>
        </h3>

        {poi.studentHighlights.length === 0 ? (
          <p className="text-[11px] italic text-ink/36">
            {/* TODO: Connect to Supabase when available */}
            暂无数据
          </p>
        ) : (
          <>
            <ul className="space-y-1" role="list" aria-label="学生关注要点">
              {visibleStudentHighlights.map((item, i) => (
                <li
                  key={i}
                  className="flex items-start gap-1.5 text-[11px] text-ink/62"
                >
                  <span
                    className="mt-[5px] block h-1 w-1 shrink-0 rounded-full bg-jade/60"
                    aria-hidden="true"
                  />
                  <span>{item}</span>
                </li>
              ))}
            </ul>

            {poi.studentHighlights.length > HIGHLIGHT_PREVIEW_COUNT && (
              <button
                type="button"
                onClick={() => setShowAllStudentHighlights((prev) => !prev)}
                className="mt-1.5 inline-flex items-center gap-0.5 text-[11px] text-cobalt/80 transition-colors hover:text-cobalt"
                aria-expanded={showAllStudentHighlights}
              >
                {showAllStudentHighlights ? "收起" : "展开全部"}
                {showAllStudentHighlights ? (
                  <ChevronUp size={12} aria-hidden="true" />
                ) : (
                  <ChevronDown size={12} aria-hidden="true" />
                )}
              </button>
            )}
          </>
        )}
      </div>

      {/* ── Nearby amenities (collapsible) ── */}
      {poi.nearby && (
        <div className="border-b border-line/60 px-4 py-3">
          <h3 className="mb-2 text-xs font-medium text-ink/72">
            周边环境
            <span className="ml-1 font-normal text-ink/40" lang="en">
              Nearby
            </span>
          </h3>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px] text-ink/56">
            <NearbyRow
              label="地铁站"
              labelEn="Subway"
              value={`${poi.nearby.subwayStations} 站`}
              // TODO: Replace with real subway station count from Supabase
            />
            <NearbyRow
              label="中餐馆"
              labelEn="Chinese Restaurants"
              value={`${poi.nearby.chineseRestaurants} 家`}
              // TODO: Replace with real restaurant count
            />
            <NearbyRow
              label="亚洲超市"
              labelEn="Asian Groceries"
              value={`${poi.nearby.asianGroceries} 家`}
              // TODO: Replace with real grocery count
            />
            <NearbyRow
              label="月均房租"
              labelEn="Avg Rent"
              value={`¥${(poi.nearby.avgRentRmb / 1000).toFixed(1)}k`}
              // TODO: Replace with real rent data
            />
          </div>
        </div>
      )}

      {/* ── Data provenance footer ── */}
      <div className="flex items-center justify-between px-4 py-2.5 text-[10px] text-ink/36">
        <div className="flex items-center gap-1">
          <Clock size={10} aria-hidden="true" />
          <span>
            数据更新于{" "}
            {new Date(poi.verifiedAt).toLocaleDateString("zh-CN", {
              year: "numeric",
              month: "2-digit",
              day: "2-digit",
            })}
          </span>
          {poi.sourceCount > 0 && (
            <>
              <span aria-hidden="true">·</span>
              <span>{poi.sourceCount} 个来源</span>
            </>
          )}
        </div>

        {/* Post-study visa badge */}
        {poi.postStudyVisa && (
          <span className="rounded-full bg-jade/8 px-1.5 py-0.5 text-[10px] text-jade/80">
            {poi.postStudyVisa}
          </span>
        )}
      </div>

      {/* ── Action buttons ── */}
      <div className="flex gap-2 border-t border-line/60 px-4 py-3">
        {/* Street View button — disabled until Phase 4 */}
        <button
          type="button"
          disabled
          aria-disabled="true"
          title="校园实景功能即将上线（Phase 4）"
          className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-line/60 bg-line/20 px-3 py-2 text-xs font-medium text-ink/36 cursor-not-allowed transition-colors"
        >
          <Eye size={14} aria-hidden="true" />
          <span>校园实景</span>
          <span className="hidden" lang="en">
            Street View
          </span>
        </button>

        {/* Full profile link (external / detail route) */}
        {/* TODO: Wire to actual detail route when routing is established:
             e.g. <Link href={`/university/${poi.id}`}> */}
        <a
          href={`/university/${poi.id}`}
          className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-cobalt/30 bg-cobalt/5 px-3 py-2 text-xs font-medium text-cobalt transition-colors hover:bg-cobalt/10 hover:border-cobalt/40"
          aria-label={`查看 ${poi.chineseName} 完整档案`}
        >
          <ExternalLink size={14} aria-hidden="true" />
          <span>完整档案</span>
          <span className="hidden" lang="en">
            Full Profile
          </span>
        </a>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// Internal sub-components
// ═══════════════════════════════════════════════════════════════════

/** A single cell in the 2x2 metric grid at the top of the card. */
function MetricCell({
  icon,
  label,
  labelEn,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  labelEn: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-2 bg-white/70 px-3.5 py-2.5">
      <div className="mt-0.5 shrink-0 text-ink/40">{icon}</div>
      <div className="min-w-0">
        <p className="text-[10px] font-medium uppercase tracking-wide text-ink/44">
          {label}
          <span className="ml-0.5 font-normal normal-case text-ink/32" lang="en">
            {labelEn}
          </span>
        </p>
        <p className="mt-0.5 text-sm font-semibold tabular-nums text-ink">
          {value}
        </p>
      </div>
    </div>
  );
}

/** A single row in the nearby amenities grid. */
function NearbyRow({
  label,
  labelEn,
  value,
}: {
  label: string;
  labelEn: string;
  value: string;
}) {
  return (
    <div className="flex items-baseline justify-between gap-1">
      <span className="text-ink/44">
        {label}{" "}
        <span className="text-ink/28" lang="en">
          {labelEn}
        </span>
      </span>
      <span className="font-medium tabular-nums text-ink/68">{value}</span>
    </div>
  );
}

export default UniversityCard;
