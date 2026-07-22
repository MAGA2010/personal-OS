"use client";

import { useCallback, useRef, useEffect, useState } from "react";
import { MapPin, GraduationCap, DollarSign, Shield, Users, Star } from "lucide-react";
import type { UniversityPOI, ChineseCommunityLevel, RankingTier } from "@/lib/types";
import maplibregl from "maplibre-gl";
import { useMapContext } from "./MapCanvas";

// ═══════════════════════════════════════════════════════════════════
// UniversityMarkers — School POI marker layer for the interactive map
// ═══════════════════════════════════════════════════════════════════
//
// Responsibilities
// ────────────────
// 1. Render a list of UniversityPOI markers on the MapLibre canvas
//    using HTML overlays (positioned absolutely inside a shared
//    container).
// 2. Display a compact preview card on hover / focus.
// 3. Support selection via the `onSelect` callback.
// 4. Visually distinguish ranking tiers via icon size and colour.
//
// Non-responsibilities (delegated to parent / sibling components)
// ──────────────────────────────────────────────────────────────────
// • MapLibre marker clustering  →  future POIClusterLayer component
// • Full university detail       →  MapShell sidebar
// • Data fetching                →  parent / SWR hook
//
// Conventions
// ───────────
// • "use client" because this component manages DOM overlay
//   positioning relative to the MapLibre map instance.
// • Chinese labels primary, English secondary (fallback).
// • Tailwind colour tokens: ink, paper, panel, line, jade, persimmon,
//   cobalt — all defined in tailwind.config.ts.
// • TODO markers for data-dependent sections.
//
// TODO: Replace mock university data with live Supabase query
// TODO: Connect to Supabase `universities` table when available
// TODO: Replace absolute-position overlays with MapLibre GL markers
//       (using maplibregl.Marker API) when the MapCanvas context is
//       wired for marker lifecycle management — Phase 3.
// TODO: Add POI clustering via supercluster when zoom level drops
//       below county granularity — Phase 3.

// ── Types ──────────────────────────────────────────────────────────

export interface UniversityMarkersProps {
  /** Array of university POIs to render as markers on the map.
   *  When empty, the component renders a subtle "no results" state
   *  instead of markers.
   *
   *  TODO: Replace with real {UniversityPOI[]} data from Supabase
   */
  universities: UniversityPOI[];

  /** Called when a user clicks a marker or presses Enter/Space on it.
   *  The parent should update `selectedUniversityId` in the view state.
   *  Pass `null` when the user deselects. */
  onSelect: (id: string | null) => void;

  /** Currently selected university ID — the corresponding marker
   *  gets a highlighted ring and expanded state.  Pass `null` when
   *  nothing is selected. */
  selectedId?: string | null;
    compareOpen?: boolean; compareIds?: string[];/** Callback fired when the user hovers over a university marker.
   *  The parent can use this to highlight the corresponding list item
   *  in the sidebar. */
  onHover?: (id: string | null) => void;

  /** Whether the underlying university data is still loading.
   *  When true, a set of skeleton pill placeholders is shown. */
  isLoading?: boolean;

  /** Optional error message shown as a compact warning chip. */
  error?: string;

  /** Extra CSS classes appended to the outermost wrapper. */
  className?: string;
}

// ── Constants ──────────────────────────────────────────────────────

/** Default: keep the original map behaviour and show university pins at every zoom. */
const DEFAULT_pinMinZoom = 0;

/** Pixel sizes for ranking-tier marker icons. */
const TIER_ICON_SIZES: Record<RankingTier, number> = {
  top20: 36,
  top50: 30,
  top100: 26,
  other: 22,
};

/** Background colour classes for ranking-tier marker icons. */
const TIER_BG_CLASSES: Record<RankingTier, string> = {
  top20: "bg-persimmon text-white",
  top50: "bg-cobalt text-white",
  top100: "bg-jade text-white",
  other: "bg-ink/12 text-ink/72",
};

/** Chinese labels for ranking tiers. */
const TIER_LABELS: Record<RankingTier, string> = {
  top20: "全球前20",
  top50: "全球前50",
  top100: "全球前100",
  other: "其他",
};

/** Marker color for each ranking tier. */
const TIER_COLORS: Record<RankingTier, string> = {
  top20: '#c45f36',
  top50: '#315d9f',
  top100: '#23766b',
  other: '#152025',
};

/** Chinese labels for Chinese community density. */
const COMMUNITY_LABELS: Record<ChineseCommunityLevel, string> = {
  high: "华人社区密集",
  medium: "华人社区适中",
  low: "华人社区较少",
};

// ── Mock Data ──────────────────────────────────────────────────────
//
// TODO: Replace with real {UniversityPOI[]} data from Supabase.
// TODO: Connect to Supabase when available.
//
// Expected Supabase query shape:
//
//   SELECT id, name, chinese_name, country, city, latitude, longitude,
//          ranking_band, ranking_tier, annual_cost_rmb, safety_score,
//          recognition_score, chinese_community, direct_flight,
//          post_study_visa, programs, parent_highlights,
//          student_highlights, verified_at, source_count,
//          streetview_pano_id, logo_url, campus_images, nearby
//     FROM universities
//    WHERE country = 'United States'
//    ORDER BY ranking_tier, name;
//
// Each university record maps to the `UniversityPOI` interface defined
// in `@/lib/types`.  The `nearby` field is a nested JSONB column with
// the shape of `UniversityNearby`.

// NOTE: MOCK_UNIVERSITIES removed. Real data sourced from frontend/src/data/universities.json (62 universities).

// ── Helpers ────────────────────────────────────────────────────────

/** Format annual cost in RMB to a compact Chinese string. */
function formatCost(rmb: number): string {
  const wan = rmb / 10000;
  // TODO: Replace with real {metric} formatting when i18n library is in place
  return `¥${wan.toFixed(0)}万/年`;
}

/** Format a safety score (0-100) for display. */
function formatSafetyScore(score: number): string {
  // TODO: Replace with real {metric} data from Supabase
  return `${score}分`;
}

// ── Component ──────────────────────────────────────────────────────

export function UniversityMarkers({
  universities,
  onSelect,
  selectedId = null,
  onHover,
  isLoading = false,
  error,
  className,
  compareOpen = false,
  compareIds = [],
}: UniversityMarkersProps) {
  // ── State ──
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // ── Derived ──
  //
  // When no universities are passed, fall back to mock data so the
  // component always renders something visible.  The mock data is
  // replaced once the parent wires up a real Supabase query.
  //
  // TODO: Remove fallback once Supabase is connected — the parent
  //       should always provide real data or an empty array.
  const displayUniversities: UniversityPOI[] =
    universities;
  const mapContext = useMapContext();
  const markersRef = useRef<{ id: string; marker: maplibregl.Marker; el: HTMLElement }[]>([]);

  // Create/update MapLibre markers when map is ready
  useEffect(() => {
    const map = mapContext?.map;
    if (!map || !mapContext?.mapReady) return;

    // Clean up existing markers
    markersRef.current.forEach(({ marker }) => marker.remove());
    markersRef.current = [];

    displayUniversities.forEach((uni) => {
      const el = document.createElement('div');
      const isSel = selectedId === uni.id;
      el.style.cssText = [
        'width:28px;height:28px;border-radius:50%;',
        'border:2px solid white;cursor:pointer;',
        'display:flex;align-items:center;justify-content:center;',
        'font-size:12px;font-weight:700;color:white;',
        'background:' + TIER_COLORS[uni.rankingTier] + ';',
        'box-shadow:' + (isSel ? '0 0 0 3px rgba(49,93,159,0.5)' : '0 2px 6px rgba(0,0,0,0.2)') + ';',
        'transform:' + (isSel ? 'scale(1.15)' : 'scale(1)') + ';',
        'transition:transform 0.15s,box-shadow 0.15s;',
      ].join('');
      el.textContent = uni.chineseName.charAt(0);
      el.title = uni.chineseName + ' (' + uni.name + ')';

      el.addEventListener('click', function(e) {
        e.stopPropagation();
        onSelect(selectedId === uni.id ? null : uni.id);
      });

      el.addEventListener('mouseenter', function() {
        setHoveredId(uni.id);
        if (onHover) onHover(uni.id);
      });

      el.addEventListener('mouseleave', function() {
        setHoveredId(null);
        if (onHover) onHover(null);
      });

      var marker = new maplibregl.Marker({ element: el })
        .setLngLat([uni.longitude, uni.latitude])
        .addTo(map);

      markersRef.current.push({ id: uni.id, marker: marker, el: el });
    });

    return function() {
      markersRef.current.forEach(function(item) { item.marker.remove(); });
      markersRef.current = [];
    };
  }, [mapContext?.map, mapContext?.mapReady, displayUniversities, selectedId, onSelect, onHover]);

  // Update marker visual state when selection changes (without recreating DOM)
  useEffect(function() {
    markersRef.current.forEach(function(item) {
      if (item.id === selectedId) {
        item.el.style.transform = 'scale(1.15)';
        item.el.style.boxShadow = '0 0 0 3px rgba(49,93,159,0.5)';
      } else {
        item.el.style.transform = 'scale(1)';
        item.el.style.boxShadow = '0 2px 6px rgba(0,0,0,0.2)';
      }
    });
  }, [selectedId]);

  // ── Handlers ──

  const handleMarkerClick = useCallback(
    (id: string) => {
      const next = selectedId === id ? null : id;
      onSelect(next);
    },
    [onSelect, selectedId],
  );

  const handleMarkerEnter = useCallback(
    (id: string) => {
      setHoveredId(id);
      onHover?.(id);
    },
    [onHover],
  );

  const handleMarkerLeave = useCallback(() => {
    setHoveredId(null);
    onHover?.(null);
  }, [onHover]);

  // ── Loading skeleton ──
  if (isLoading) {
    return (
      <div
        role="status"
        aria-label="大学标记加载中"
        className={className}
      >
        <div className="flex flex-wrap gap-2 px-2 py-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="flex items-center gap-2 rounded-full border border-line/60 bg-white/88 px-3 py-1.5 animate-pulse"
            >
              <div className="h-5 w-5 rounded-full bg-line/40" />
              <div className="h-3 w-16 rounded bg-line/40" />
            </div>
          ))}
        </div>
        <span className="sr-only">大学标记加载中… / Loading university markers…</span>
      </div>
    );
  }

  // ── Error state ──
  if (error) {
    return (
      <div
        role="alert"
        className={className}
      >
        <div className="inline-flex items-center gap-1.5 rounded border border-persimmon/30 bg-persimmon/5 px-2.5 py-1.5 text-xs text-persimmon">
          <Shield aria-hidden="true" size={12} />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  // ── Empty state ──
  if (displayUniversities.length === 0) {
    return (
      <div
        role="status"
        aria-label="无大学数据"
        className={className}
      >
        <div className="inline-flex items-center gap-1.5 rounded border border-line bg-white/88 px-3 py-1.5 text-xs text-ink/44">
          <MapPin aria-hidden="true" size={12} />
          <span>暂无大学数据</span>
          <span className="text-ink/24" lang="en">
            No universities
          </span>
        </div>
      </div>
    );
  }

  // ── Marker grid ──
  //
  // Renders as a scrollable grid of university pill buttons.  In the
  // final Phase 3 implementation these will be replaced with actual
  // MapLibre GL markers positioned by lat/lng on the map canvas.
  //
  // TODO: Replace this grid with maplibregl.Marker instances anchored
  //       to the MapCanvas context (Phase 3).
  // Data sourced from frontend/src/data/universities.json (62 universities)
  //       fallback and rely entirely on parent-provided data.

  return (
    <div
      role="list"
      aria-label="大学POI标记列表"
      className={className}
    >
      <div className="flex flex-wrap gap-1.5">
        {displayUniversities.map((uni) => {
          const isSelected = selectedId === uni.id;
          const isHovered = hoveredId === uni.id;
          const tierSize = TIER_ICON_SIZES[uni.rankingTier];
          const tierBg = TIER_BG_CLASSES[uni.rankingTier];

          return (
            <div
              key={uni.id}
              role="listitem"
              className="relative"
              onMouseEnter={() => handleMarkerEnter(uni.id)}
              onMouseLeave={handleMarkerLeave}
            >
              {/* ── Marker pill button ── */}
              <button
                type="button"
                onClick={() => handleMarkerClick(uni.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleMarkerClick(uni.id);
                  }
                }}
                aria-label={`${uni.chineseName} (${uni.name}) — ${TIER_LABELS[uni.rankingTier]}`}
                aria-pressed={isSelected}
                aria-describedby={
                  isHovered || isSelected
                    ? `uni-preview-${uni.id}`
                    : undefined
                }
                className={[
                  // Base pill
                  "flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-xs font-medium",
compareOpen && compareIds?.includes(uni.id) ? "bg-cobalt/20 border-cobalt text-cobalt" : "",
                  // Transitions
                  "transition-all duration-150",
                  // Focus ring
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cobalt/50 focus-visible:ring-offset-1",
                  // Selection state
                  isSelected
                    ? "border-cobalt bg-cobalt/10 text-cobalt shadow-sm"
                    : isHovered
                      ? "border-ink/30 bg-white text-ink/82 shadow-sm"
                      : "border-line/60 bg-white/88 text-ink/72",
                ].join(" ")}
              >
                {/* Tier icon */}
                <span
                  className={[
                    "grid shrink-0 place-items-center rounded-full",
                    tierBg,
                  ].join(" ")}
                  style={{ width: tierSize * 0.55, height: tierSize * 0.55 }}
                  aria-hidden="true"
                >
                  <GraduationCap size={tierSize * 0.35} />
                </span>

                {/* Chinese name (primary) */}
                <span className="max-w-[120px] truncate">
                  {uni.chineseName}
                </span>

                {/* Ranking badge */}
                <span
                  className="hidden sm:inline-block rounded-full bg-ink/8 px-1.5 py-0.5 text-[10px] text-ink/48 shrink-0"
                  aria-hidden="true"
                >
                  {uni.rankingBand}
                </span>
              </button>

              {/* ── Preview tooltip card (shown on hover or selection) ── */}
              {isSelected && (
                <div
                  id={`uni-preview-${uni.id}`}
                  role="tooltip"
                  className="absolute left-0 top-full z-20 mt-1.5 w-48 rounded border border-line bg-white/90 px-2 py-1.5 text-[10px] leading-tight shadow-sm backdrop-blur"
                >
                  {/* Header */}
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-ink">
                        {uni.chineseName}
                      </p>
                      <p className="truncate text-ink/48" lang="en">
                        {uni.name}
                      </p>
                    </div>
                    <span
                      className={[
                        "shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium",
                        tierBg,
                      ].join(" ")}
                    >
                      {TIER_LABELS[uni.rankingTier]}
                    </span>
                  </div>

                  {/* Location */}
                  <p className="mb-2 flex items-center gap-1 text-ink/52">
                    <MapPin aria-hidden="true" size={11} />
                    <span>{uni.city}, {uni.country}</span>
                  </p>

                  {/* Key metrics row */}
                  <div className="mb-2.5 grid grid-cols-2 gap-x-3 gap-y-1.5">
                    {/* Annual cost */}
                    <div className="flex items-center gap-1 text-ink/56">
                      <DollarSign
                        aria-hidden="true"
                        size={11}
                        className="text-jade"
                      />
                      <span>{formatCost(uni.annualCostRmb)}</span>
                    </div>

                    {/* Safety score */}
                    <div className="flex items-center gap-1 text-ink/56">
                      <Shield
                        aria-hidden="true"
                        size={11}
                        className="text-cobalt"
                      />
                      <span>{formatSafetyScore(uni.safetyScore)}</span>
                    </div>

                    {/* Recognition score */}
                    <div className="flex items-center gap-1 text-ink/56">
                      <Star
                        aria-hidden="true"
                        size={11}
                        className="text-persimmon"
                      />
                      <span>认可度 {uni.recognitionScore}</span>
                    </div>

                    {/* Chinese community */}
                    <div className="flex items-center gap-1 text-ink/56">
                      <Users
                        aria-hidden="true"
                        size={11}
                        className="text-ink/40"
                      />
                      <span>
                        {COMMUNITY_LABELS[uni.chineseCommunity]}
                      </span>
                    </div>
                  </div>

                  {/* Divider */}
                  <div className="mb-2 h-px w-full bg-line/60" aria-hidden="true" />

                  {/* Programs (first 3) */}
                  {uni.programs.length > 0 && (
                    <div className="mb-1.5">
                      <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-ink/36">
                        热门专业
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {uni.programs.slice(0, 3).map((p) => (
                          <span
                            key={p}
                            className="rounded border border-line/50 bg-paper px-1.5 py-0.5 text-[10px] text-ink/56"
                          >
                            {p}
                          </span>
                        ))}
                        {uni.programs.length > 3 && (
                          <span className="text-[10px] text-ink/36 self-center">
                            +{uni.programs.length - 3}
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Parent highlights */}
                  {uni.parentHighlights.length > 0 && (
                    <div className="mb-1.5">
                      <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-ink/36">
                        家长关注
                      </p>
                      <ul className="list-inside list-disc space-y-0.5">
                        {uni.parentHighlights.slice(0, 2).map((h, i) => (
                          <li
                            key={i}
                            className="text-[10px] leading-relaxed text-ink/56"
                          >
                            {h}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Footer meta */}
                  <div className="mt-2 flex items-center gap-2 text-[10px] text-ink/36">
                    <span>数据验证: {uni.verifiedAt}</span>
                    <span aria-hidden="true">·</span>
                    <span>{uni.sourceCount} 个来源</span>
                    {uni.directFlight && (
                      <>
                        <span aria-hidden="true">·</span>
                        <span className="text-jade">直飞</span>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Exports ────────────────────────────────────────────────────────
// ── UniversityMapPins — MapLibre markers only (no pill strip) ─────

const DEFAULT_PIN_MIN_ZOOM = 0;

export function UniversityMapPins({
  universities,
  onSelect,
  selectedId = null,
  onHover,
  pinMinZoom = DEFAULT_PIN_MIN_ZOOM,
}: {
  universities: UniversityPOI[];
  onSelect: (id: string | null) => void;
  selectedId?: string | null;
  onHover?: (id: string | null) => void;
  /** Minimum zoom required to show map pins; pass 7.6 when city bubbles are enabled. */
  pinMinZoom?: number;
}) {
  const mapContext = useMapContext();
  const [, setHoveredId] = useState<string | null>(null);
  const markersRef = useRef<{ id: string; marker: maplibregl.Marker; el: HTMLElement }[]>([]);

  // Map pins must reflect the actual filtered result set. Do not fall back to mock data here,
  // otherwise empty filters/city drill-down still leave unrelated school pins on the map.
  const displayUniversities: UniversityPOI[] = universities;

  const updatePinVisibility = useCallback(() => {
    const map = mapContext?.map;
    if (!map) return;
    const visible = map.getZoom() >= pinMinZoom;
    markersRef.current.forEach(({ el }) => {
      el.style.display = visible ? 'flex' : 'none';
    });
  }, [mapContext?.map, pinMinZoom]);

  // Create/update MapLibre markers when map is ready.
  useEffect(() => {
    const map = mapContext?.map;
    if (!map || !mapContext?.mapReady) return;

    markersRef.current.forEach(({ marker }) => marker.remove());
    markersRef.current = [];

    displayUniversities.forEach((uni) => {
      const el = document.createElement('div');
      const isSel = selectedId === uni.id;
      el.style.cssText = [
        'width:28px;height:28px;border-radius:50%;',
        'border:2px solid white;cursor:pointer;',
        'display:flex;align-items:center;justify-content:center;',
        'font-size:12px;font-weight:700;color:white;',
        'background:' + TIER_COLORS[uni.rankingTier] + ';',
        'box-shadow:' + (isSel ? '0 0 0 3px rgba(49,93,159,0.5)' : '0 2px 6px rgba(0,0,0,0.2)') + ';',
        'transform:' + (isSel ? 'scale(1.15)' : 'scale(1)') + ';',
        'transition:transform 0.15s,box-shadow 0.15s;',
      ].join('');
      el.style.display = map.getZoom() >= pinMinZoom ? 'flex' : 'none';
      el.textContent = uni.chineseName.charAt(0);
      el.title = uni.chineseName + ' (' + uni.name + ')';

      el.addEventListener('click', function(e) {
        e.stopPropagation();
        onSelect(selectedId === uni.id ? null : uni.id);
      });

      el.addEventListener('mouseenter', function() {
        setHoveredId(uni.id);
        onHover?.(uni.id);
      });

      el.addEventListener('mouseleave', function() {
        setHoveredId(null);
        onHover?.(null);
      });

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([uni.longitude, uni.latitude])
        .addTo(map);

      markersRef.current.push({ id: uni.id, marker, el });
    });

    updatePinVisibility();

    return function() {
      markersRef.current.forEach(function(item) { item.marker.remove(); });
      markersRef.current = [];
    };
  }, [mapContext?.map, mapContext?.mapReady, displayUniversities, selectedId, onSelect, onHover, updatePinVisibility]);

  // Update marker visual state when selection changes.
  useEffect(function() {
    markersRef.current.forEach(function(item) {
      if (item.id === selectedId) {
        item.el.style.transform = 'scale(1.15)';
        item.el.style.boxShadow = '0 0 0 3px rgba(49,93,159,0.5)';
      } else {
        item.el.style.transform = 'scale(1)';
        item.el.style.boxShadow = '0 2px 6px rgba(0,0,0,0.2)';
      }
    });
  }, [selectedId]);

  // Avoid crowding when city bubbles are enabled; default pinMinZoom=0 preserves original behaviour.
  useEffect(() => {
    const map = mapContext?.map;
    if (!map || !mapContext?.mapReady) return;

    map.on('zoom', updatePinVisibility);
    map.on('zoomend', updatePinVisibility);
    updatePinVisibility();

    return () => {
      map.off('zoom', updatePinVisibility);
      map.off('zoomend', updatePinVisibility);
    };
  }, [mapContext?.map, mapContext?.mapReady, updatePinVisibility]);

  return null;
}


export default UniversityMarkers;







