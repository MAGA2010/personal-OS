"use client";

// Stage 7B-A.3.1 — Region Detail Panel (right sidebar).
//
// Drives the right sidebar from `selectedRegionFips` directly, with the
// universities list computed via `stateFips` filter on the canonical
// `universities` array. This replaces the previous `RegionDetailSidebar`
// that depended on `regionMetricSet` (which is empty when the Preview
// Bundle marks `region-metrics:disabled`).
//
// Single-instance: mounted by MapShell inside `ResizablePanel`. The panel
// is mutually exclusive with `CityDetailPanel` and `UniversityProfile`
// (MapShell wires that gating).

import { useMemo } from "react";
import { ChevronRight, MapPin, GraduationCap } from "lucide-react";
import type { MetricId, UniversityPOI } from "@/lib/types";
import { METRIC_DEFINITIONS } from "@/config/metrics.config";
import { STATE_NAME_ZH, STATE_NAME_EN, fipsFromAbbr } from "@/config/states.config";
import { normalizeStateFips } from "@/regional/normalizeStateFips";
import { getRegionalMetricDefinition } from "@/regional/load";
import type { RegionalMetricId } from "@/regional/types";

interface Props {
  /** Two-digit zero-padded FIPS code (e.g. "06"). */
  stateFips: string;
  /** Active city-level metric (used for the indicator label). */
  activeMetricId: MetricId;
  /** Active state choropleth metric, when a regional layer is shown. */
  activeRegionalMetric: RegionalMetricId | null;
  /** All universities from the canonical data source. */
  universities: ReadonlyArray<UniversityPOI>;
  /** Close the panel (escape / close button). Clears `selectedRegionFips`. */
  onClose: () => void;
  /** Open a University Profile from a card click. */
  onUniversitySelect?: (id: string) => void;
  /** Currently selected university id (for highlight). */
  selectedUniversityId?: string | null;
}

export function RegionDetailPanel({
  stateFips,
  activeMetricId,
  activeRegionalMetric,
  universities,
  onClose,
  onUniversitySelect,
  selectedUniversityId,
}: Props): JSX.Element {
  const normalized = normalizeStateFips(stateFips) ?? stateFips;
  const nameZh = STATE_NAME_ZH[normalized] ?? normalized;
  const nameEn = STATE_NAME_EN[normalized] ?? normalized;
  const metricLabel = activeRegionalMetric
    ? getRegionalMetricDefinition(activeRegionalMetric)?.displayNameZh ?? activeRegionalMetric
    : METRIC_DEFINITIONS[activeMetricId]?.label ?? "当前指标";

  // Filter the universities list by normalized stateFips. UniversityPOI
  // exposes `stateFips` (already normalized in summaryToLegacyUniversityPOI).
  const universitiesInState = useMemo<UniversityPOI[]>(() => {
    return universities.filter((u: UniversityPOI) => {
      const fips = (u as unknown as { stateFips?: string }).stateFips;
      if (!fips) return false;
      return normalizeStateFips(fips) === normalized;
    });
  }, [universities, normalized]);

  return (
    <>
      {/* Sidebar header */}
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold text-ink" data-testid="region-detail-title">
            {nameZh}
          </h2>
          <p className="text-xs text-ink/48">{nameEn} · FIPS {normalized}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="关闭区域详情"
          data-testid="region-detail-close"
          className="grid h-7 w-7 shrink-0 place-items-center rounded text-ink/44 transition-colors hover:bg-line/40 hover:text-ink"
        >
          <ChevronRight size={16} />
        </button>
      </div>

      {/* Active metric chip */}
      <div className="border-b border-line px-4 py-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-ink/60">当前指标</span>
          <span className="rounded-full bg-cobalt/10 px-2 py-0.5 text-[10px] font-medium text-cobalt">
            {metricLabel}
          </span>
        </div>
      </div>

      {/* Universities list (本州大学) */}
      <div className="flex-1 overflow-y-auto px-4 py-3" data-testid="region-detail-universities">
        <h3 className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-ink/44">
          <GraduationCap size={11} aria-hidden="true" />
          本州大学
          <span
            className="ml-1.5 rounded bg-ink/8 px-1.5 py-0.5 text-[10px]"
            data-testid="region-detail-university-count"
          >
            {universitiesInState.length}
          </span>
        </h3>
        {universitiesInState.length === 0 ? (
          <p
            data-testid="region-detail-empty"
            className="rounded-md border border-dashed border-line/60 bg-paper/40 p-3 text-xs italic text-ink/55"
          >
            当前 Demo 数据范围内暂无该州学校。
          </p>
        ) : (
          <ul className="space-y-2" role="list">
            {universitiesInState.map((u: UniversityPOI) => {
              const isSelected = selectedUniversityId === u.id;
              return (
                <li key={u.id}>
                  <button
                    type="button"
                    onClick={() => onUniversitySelect?.(u.id)}
                    aria-pressed={isSelected}
                    data-testid="region-detail-university-card"
                    className={`flex w-full flex-col gap-1.5 rounded-lg border px-3 py-2.5 text-left text-xs transition-colors ${
                      isSelected
                        ? "border-cobalt/40 bg-cobalt/8"
                        : "border-line/70 bg-white hover:border-cobalt/30 hover:bg-cobalt/[0.03]"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate font-medium text-ink">
                          {u.chineseName || u.name || "未提供名称"}
                        </div>
                        {u.name && u.chineseName !== u.name && (
                          <div className="truncate text-ink/55" lang="en">
                            {u.name}
                          </div>
                        )}
                      </div>
                      {u.rankingBand && (
                        <span className="shrink-0 rounded-full border border-line/60 bg-paper px-1.5 py-0.5 text-[10px] font-medium text-ink/70">
                          {u.rankingBand}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1 text-ink/48">
                      <MapPin size={10} aria-hidden="true" />
                      <span className="truncate">
                        {u.city || "未提供位置"}
                      </span>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </>
  );
}

export default RegionDetailPanel;
