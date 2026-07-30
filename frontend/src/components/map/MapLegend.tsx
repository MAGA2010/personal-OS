"use client";
import type { MetricDefinition, MetricId } from "@/lib/types";
import { METRIC_DEFINITIONS } from "@/config/metrics.config";

// ── Inline colour ramp (avoids external /shared/color-ramp dependency) ──

import {
  interpolateGreens,
  interpolateRdBu,
  interpolateOrRd,
  interpolateYlOrRd,
  interpolateYlGn,
  interpolateOranges,
} from "d3-scale-chromatic";

type ColorInterpolator = (t: number) => string;

const SCHEME_MAP: Record<MetricDefinition["colorScheme"], ColorInterpolator> = {
  greens: interpolateGreens,
  redblue: interpolateRdBu,
  tealgrn: interpolateYlGn,
  oranges: interpolateOranges,
  orangered: interpolateOrRd,
  ylorrd: interpolateYlOrRd,
};

const STEPS = 10;
const DOMAIN_CLIP: [number, number] = [0.08, 0.92];

function buildLegendStops(
  scheme: MetricDefinition["colorScheme"],
  invert: boolean,
): Array<{ offset: number; color: string }> {
  const base = SCHEME_MAP[scheme];
  const interpolate = (t: number) => {
    const raw = DOMAIN_CLIP[0] + t * (DOMAIN_CLIP[1] - DOMAIN_CLIP[0]);
    return base(invert ? 1 - raw : raw);
  };
  return Array.from({ length: STEPS + 1 }, (_, i) => ({
    offset: Math.round((i / STEPS) * 100),
    color: interpolate(i / STEPS),
  }));
}

// ═══════════════════════════════════════════════════════════════════
// MapLegend — Color gradient legend bar for the choropleth map
// ═══════════════════════════════════════════════════════════════════
//
// Renders a horizontal gradient bar with min / max labels for the
// currently active metric layer. The gradient is computed from the
// metric's d3 colour scheme via `buildLegendStops`.
//
// Gate-bloker repair #RG-P0-K:
//   The previous version hard-coded a `MOCK_RANGES` object with
//   invented min/max display strings (e.g. "$55k–$140k", "200–500")
//   for each metric, then used them as the default when the parent
//   didn't pass `minLabel` / `maxLabel`. That was a single source of
//   fake data masquerading as the real legend. We now consume the
//   canonical `MetricMetadata` shape from the backend (which itself
//   owns `minRawValue`/`maxRawValue` plus a `unit` string). When
//   the parent can't supply metadata, the legend renders the empty
//   state — it never invents numbers.

// ── Types ──────────────────────────────────────────────────────────

export interface MetricMetadata {
  /** Stable metric id matching one entry in `METRIC_DEFINITIONS`. */
  metricId: MetricId;
  /** Inclusive lower bound, in the metric's canonical raw unit. */
  minRawValue: number | null;
  /** Inclusive upper bound, in the metric's canonical raw unit. */
  maxRawValue: number | null;
  /** Display label for the lower bound (already formatted). */
  minLabel: string | null;
  /** Display label for the upper bound (already formatted). */
  maxLabel: string | null;
  /** Year + source provenance (e.g. "ACS 2024 5-Year"). */
  source?: string;
  year?: number;
  /** When true, the metadata is incomplete and the legend should
   *  fall back to a neutral "data pending" placeholder rather than
   *  guessing. */
  isPending?: boolean;
}

export interface MapLegendProps {
  /** The currently active metric definition.  Defaults to "income" when
   *  omitted, so the component always renders something visible. */
  metric?: MetricDefinition;

  /** Backend-supplied min/max metadata. The component renders
   *  `图例数据暂不可用` when omitted or when `metadata.isPending`
   *  is true. */
  metadata?: MetricMetadata | null;

  /** Optional explicit display labels. When both `minLabel` and
   *  `maxLabel` are present on `metadata`, they win; otherwise we
   *  fall back to these props (used by the parent when it wants to
   *  override formatting). */
  minLabel?: string;
  maxLabel?: string;

  /** Whether the underlying metric data is still loading.  When true the
   *  gradient bar is replaced with a subtle shimmer skeleton. */
  isLoading?: boolean;

  /** Optional error message — shown as a compact warning chip under the bar. */
  error?: string;
}

/** Default metric shown when none is provided — guarantees visible output. */
const DEFAULT_METRIC_ID = "income";

// ── Helpers ────────────────────────────────────────────────────────

function isUsableMetadata(metadata: MetricMetadata | null | undefined): metadata is MetricMetadata {
  return (
    !!metadata &&
    !metadata.isPending &&
    typeof metadata.minLabel === "string" &&
    metadata.minLabel.length > 0 &&
    typeof metadata.maxLabel === "string" &&
    metadata.maxLabel.length > 0
  );
}

function placeholderLabels(_metricId: MetricId): { min: string; max: string } {
  // Gate-bloker repair #RG-P0-K: this is the *only* allowed fallback
  // when the backend hasn't returned metadata. It deliberately uses
  // a neutral "图例数据暂不可用" so users understand the numeric
  // range is not known; it never returns a fake "$55k" or "¥15万".
  return {
    min: "图例数据暂不可用",
    max: "图例数据暂不可用",
  };
}

// ── Component ──────────────────────────────────────────────────────

export function MapLegend({
  metric,
  metadata,
  minLabel: propMin,
  maxLabel: propMax,
  isLoading = false,
  error,
}: MapLegendProps) {
  // ── Resolve active metric ──
  const activeMetric: MetricDefinition =
    metric ?? METRIC_DEFINITIONS[DEFAULT_METRIC_ID];

  // ── Resolve display labels ──
  // Priority: backend metadata > explicit props > neutral placeholder.
  // The pre-ReGate version fell back to a hard-coded MOCK_RANGES
  // object here, which is the source of the "图例用了假数字" bug.
  const { min: minLabel, max: maxLabel } = (() => {
    if (isUsableMetadata(metadata)) {
      return { min: metadata.minLabel, max: metadata.maxLabel };
    }
    if (propMin && propMax) return { min: propMin, max: propMax };
    return placeholderLabels(activeMetric.id);
  })();

  const metadataAvailable = isUsableMetadata(metadata);

  // ── Build gradient stops ──
  const stops = buildLegendStops(activeMetric.colorScheme, activeMetric.invertScale);
  const gradientCss = `linear-gradient(to right, ${stops
    .map((s) => s.color)
    .join(", ")})`;

  // ── Loading skeleton ──
  if (isLoading) {
    return (
      <div
        role="status"
        aria-label={`${activeMetric.label} 图例加载中`}
        className="pointer-events-auto w-full max-w-[220px] rounded-lg border border-line/60 bg-white/94 px-3 py-2.5 shadow-panel backdrop-blur"
      >
        <div className="mb-1.5 h-3.5 w-24 animate-pulse rounded bg-line/50" />
        <div className="h-2.5 w-full animate-pulse rounded-sm bg-line/40" />
        <div className="mt-1 flex justify-between">
          <div className="h-3 w-10 animate-pulse rounded bg-line/40" />
          <div className="h-3 w-10 animate-pulse rounded bg-line/40" />
        </div>
        <span className="sr-only">加载中…</span>
      </div>
    );
  }

  // ── Rendered legend ──
  return (
    <div
      role="complementary"
      aria-label={`${activeMetric.label} 图例`}
      className="pointer-events-auto w-full max-w-[220px] rounded-lg border border-line bg-white/94 px-3 py-2.5 text-xs shadow-panel backdrop-blur"
    >
      {/* ── Title row: metric name + unit ── */}
      <div className="mb-1.5 flex items-baseline gap-1">
        <span className="font-medium text-ink/80">{activeMetric.label}</span>
        <span className="font-normal text-ink/48">{activeMetric.labelEn}</span>
        <span className="ml-auto font-normal tabular-nums text-ink/40">
          {activeMetric.unit}
        </span>
      </div>

      {/* ── Gradient bar ── */}
      <div
        className="h-2.5 w-full rounded-sm"
        style={{ background: gradientCss }}
        aria-hidden
      />

      {/* ── Min / Max labels ── */}
      <div className="mt-1 flex justify-between text-[11px] tabular-nums text-ink/52">
        <span>{minLabel}</span>
        <span>{maxLabel}</span>
      </div>

      {/* ── Metadata provenance chip ── */}
      {metadataAvailable && metadata ? (
        <div className="mt-1 text-[10px] text-ink/36">
          {metadata.year ? `${metadata.year}` : ""}
          {metadata.source ? ` · ${metadata.source}` : ""}
        </div>
      ) : (
        <div
          role="status"
          className="mt-1 rounded border border-line/60 bg-line/15 px-1.5 py-0.5 text-[10px] leading-tight text-ink/48"
        >
          图例数据暂不可用
        </div>
      )}

      {/* ── Error chip ── */}
      {error && (
        <div
          role="alert"
          className="mt-1.5 rounded border border-persimmon/30 bg-persimmon/5 px-1.5 py-0.5 text-[10px] leading-tight text-persimmon"
        >
          {error}
        </div>
      )}
    </div>
  );
}

export default MapLegend;