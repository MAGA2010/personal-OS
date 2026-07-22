"use client";

import type { MetricDefinition, ColorSchemeId } from "@/lib/types";
import { METRIC_DEFINITIONS } from "@/lib/metrics";

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

const SCHEME_MAP: Record<ColorSchemeId, ColorInterpolator> = {
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
  scheme: ColorSchemeId,
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
// currently active metric layer.  The gradient is computed from the
// metric's d3 colour scheme via `buildLegendStops`.
//
// Data dependencies (all mocked until Supabase is wired):
//   • Active metric definition  →  METRIC_DEFINITIONS (static)
//   • Min / max raw values       →  hardcoded per metric (see MOCK_RANGES)
//   • Gradient colour stops      →  buildLegendStops() from color-ramp.ts
//
  // TODO: Use live min/max from region-metrics.json (currently MOCK_RANGES)
//       once `region_metrics` table is populated.  Expected shape:
//
//         SELECT MIN(raw_value), MAX(raw_value)
//           FROM region_metrics
//          WHERE metric_id = $1 AND granularity = $2;
//
// TODO: Connect to Supabase when available — the component should
//       accept `minRawValue` and `maxRawValue` as props from a parent
//       that fetches them server-side or via SWR.

// ── Types ──────────────────────────────────────────────────────────

export interface MapLegendProps {
  /** The currently active metric definition.  Defaults to "income" when
   *  omitted, so the component always renders something visible. */
  metric?: MetricDefinition;

  /** Minimum display label shown on the left side of the gradient bar.
   *  When absent the component falls back to a mock range for the metric. */
  minLabel?: string;

  /** Maximum display label shown on the right side of the gradient bar. */
  maxLabel?: string;

  /** Whether the underlying metric data is still loading.  When true the
   *  gradient bar is replaced with a subtle shimmer skeleton. */
  isLoading?: boolean;

  /** Optional error message — shown as a compact warning chip under the bar. */
  error?: string;
}

// ── Mock Data ──────────────────────────────────────────────────────

/**
 * Per-metric min/max display label ranges used until real data
 * is available from Supabase.
 *
 * Each entry mirrors what `formatMetricValue` would produce for the
 * expected data range of that metric.
 *
 * TODO: Replace with real {metric} regional data.
 * TODO: Connect to Supabase when available.
 */
const MOCK_RANGES: Record<string, { min: string; max: string }> = {
  income:             { min: "$55k",  max: "$140k"  },
  safety:             { min: "200",   max: "500"    },
  employment:         { min: "94.8%", max: "97.7%"  },
  cost:               { min: "¥15万", max: "¥60万"  },
  admission_rate:     { min: "15%",   max: "85%"    },
  chinese_population: { min: "0.5%",  max: "14%"    },
};

/** Default metric shown when none is provided — guarantees visible output. */
const DEFAULT_METRIC_ID = "income";

// ── Helpers ────────────────────────────────────────────────────────

/**
 * Resolve min / max labels with the following priority:
 *   1. Explicit `minLabel` / `maxLabel` props
 *   2. Mock range for the active metric
 *   3. Placeholder strings "低" / "高"
 */
function resolveLabels(
  metricId: string,
  propMin?: string,
  propMax?: string,
): { min: string; max: string } {
  if (propMin !== undefined && propMax !== undefined) {
    return { min: propMin, max: propMax };
  }
  const mock = MOCK_RANGES[metricId];
  if (mock) return mock;
  return { min: "低 / Low", max: "高 / High" };
}

// ── Component ──────────────────────────────────────────────────────

export function MapLegend({
  metric,
  minLabel: propMin,
  maxLabel: propMax,
  isLoading = false,
  error,
}: MapLegendProps) {
  // ── Resolve active metric ──
  const activeMetric: MetricDefinition =
    metric ?? METRIC_DEFINITIONS[DEFAULT_METRIC_ID];

  // ── Resolve display labels ──
  const { min: minLabel, max: maxLabel } = resolveLabels(
    activeMetric.id,
    propMin,
    propMax,
  );

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