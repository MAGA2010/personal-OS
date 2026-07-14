// ── Metric Metadata Registry ──
// All six map metric layers: definitions, display formatting, and mock data.
//
// TODO: Connect to Supabase when available — replace MOCK_STATE_METRICS
//       with `getMetricValue(fipsCode, metricId, granularity)` API call.

import type { MetricDefinition, MetricId, RegionMetric, Granularity } from "./types";

// ── Metric Definitions ──

/**
 * Registry of all six choropleth metric layers.
 * Keys match `MetricId` from @/lib/types.
 *
 * `invertScale` flips the color ramp so higher raw values produce the
 * "worse" color.  Used for metrics where a lower number is "better":
 *   - safety:  fewer crimes  → more blue
 *   - admission_rate:  harder to get in  → deeper red
 */
export const METRIC_DEFINITIONS: Record<MetricId, MetricDefinition> = {
  income: {
    id: "income",
    label: "收入水平",
    labelEn: "Median Income",
    unit: "$",
    colorScheme: "greens",
    invertScale: false,
    description:
      "区域家庭中位年收入，反映地区经济水平与生活成本",
  },

  safety: {
    id: "safety",
    label: "安全系数",
    labelEn: "Safety Index",
    unit: "/100k",
    colorScheme: "redblue",
    invertScale: true,
    description:
      "基于暴力犯罪率（每10万人暴力犯罪案件数）的倒数，数值越高越安全",
  },

  employment: {
    id: "employment",
    label: "就业指数",
    labelEn: "Employment Index",
    unit: "%",
    colorScheme: "tealgrn",
    invertScale: false,
    description:
      "基于BLS各州失业率数据计算：就业率 = 100% - 失业率，反映该地区的劳动力市场健康程度",
  },

  cost: {
    id: "cost",
    label: "留学成本",
    labelEn: "Study Cost Index",
    unit: "¥/年",
    colorScheme: "oranges",
    invertScale: false,
    description:
      "包含学费与生活费的年度综合留学成本评估，数值越高表示留学成本越高",
  },

  admission_rate: {
    id: "admission_rate",
    label: "录取率",
    labelEn: "Admission Rate",
    unit: "%",
    colorScheme: "orangered",
    invertScale: true,
    description:
      "该区域大学的平均录取率，数值越低表示竞争越激烈",
  },

  chinese_population: {
    id: "chinese_population",
    label: "华人水平",
    labelEn: "Chinese Population",
    unit: "%",
    colorScheme: "ylorrd",
    invertScale: false,
    description:
      "华裔人口占比，反映该区域华人社区规模和便利程度，范围约 0-15%",
  },
};

// ── Metric Display Order ──

/**
 * Tab order for the metric switcher (left-to-right in the UI).
 */
export const METRIC_ORDER: MetricId[] = [
  "income",
  "safety",
  "employment",
  "cost",
  "admission_rate",
  "chinese_population",
];

// ── Display Formatting ──

/**
 * Format a user-visible metric value for tooltips, legends, and infoboxes.
 *
 * @param metricId - The metric being displayed.
 * @param rawValue   - The real (non-normalized) metric value.
 * @returns A human-readable string with unit appended where appropriate.
 */
export function formatMetricValue(metricId: MetricId, rawValue: number): string {
  switch (metricId) {
    case "income":
      return `$${(rawValue / 1000).toFixed(0)}k`;
    case "safety":
      return `${rawValue.toFixed(0)}/100k`;
    case "employment":
      return `${rawValue.toFixed(1)}%`;
        case "cost":
      return `¥${(rawValue / 10000).toFixed(0)}万`;
    case "admission_rate":
    case "chinese_population":
      return `${rawValue.toFixed(1)}%`;
    default: {
      const _exhaustive: never = metricId;
      return `${rawValue}`;
    }
  }
}

/**
 * Derive a display value from a 0–1 normalised value for mock / local preview.
 *
 * TODO: Remove this function once real (non-normalised) data is in place;
 *       `formatMetricValue` will be used directly on raw values from Supabase.
 */
export function denormaliseDisplayValue(metricId: MetricId, normalised: number): string {
  let raw: number;
  switch (metricId) {
    case "income":
      raw = Math.round(normalised * 150_000);
      break;
    case "safety":
      raw = Math.round(normalised * 500 + 200);
      break;
    case "employment":
      raw = Math.round(normalised * 2.9 + 94.8);
      break;
    case "cost":
      raw = Math.round(normalised * 450000 + 150000);
      break;
    case "admission_rate":
      raw = (1 - normalised) * 80 + 10;
      break;
    case "chinese_population":
      raw = normalised * 15;
      break;
    default: {
      const _exhaustive: never = metricId;
      raw = normalised;
    }
  }
  return formatMetricValue(metricId, raw);
}

// ── Mock Data ──

/**
 * Mock state-level metric values, 0–1 normalised.
 *
 * Key:  FIPS state code (string, 2 digits).
 * Value: partial record mapping MetricId to a 0–1 float.
 *
 * TODO: Replace with real {metric name} regional data.
 * TODO: Connect to Supabase when available — expected shape:
 *
 *   SELECT fips_code, metric_id, raw_value, year
 *     FROM region_metrics
 *    WHERE granularity = $1;
 *
 *   The returned rows should be mapped to `RegionMetric[]`.
 */

const MOCK_NORMALIZED: Record<string, Partial<Record<MetricId, number>>> = {
  // ── Northeast ──
  "25": { income: 0.85, safety: 0.72, employment: 0.80, cost: 0.78, admission_rate: 0.35, chinese_population: 0.62 }, // MA
  "36": { income: 0.80, safety: 0.60, employment: 0.82, cost: 0.80, admission_rate: 0.28, chinese_population: 0.88 }, // NY
  "34": { income: 0.82, safety: 0.68, employment: 0.75, cost: 0.74, admission_rate: 0.32, chinese_population: 0.52 }, // NJ
  "42": { income: 0.72, safety: 0.65, employment: 0.78, cost: 0.76, admission_rate: 0.40, chinese_population: 0.45 }, // PA
  "09": { income: 0.78, safety: 0.70, employment: 0.79, cost: 0.77, admission_rate: 0.30, chinese_population: 0.50 }, // CT

  // ── Midwest ──
  "17": { income: 0.70, safety: 0.55, employment: 0.72, cost: 0.70, admission_rate: 0.45, chinese_population: 0.48 }, // IL
  "39": { income: 0.65, safety: 0.62, employment: 0.68, cost: 0.68, admission_rate: 0.52, chinese_population: 0.25 }, // OH
  "26": { income: 0.62, safety: 0.58, employment: 0.70, cost: 0.69, admission_rate: 0.50, chinese_population: 0.30 }, // MI
  "55": { income: 0.66, safety: 0.64, employment: 0.66, cost: 0.65, admission_rate: 0.55, chinese_population: 0.20 }, // WI
  "27": { income: 0.68, safety: 0.60, employment: 0.67, cost: 0.66, admission_rate: 0.48, chinese_population: 0.22 }, // MN

  // ── South ──
  "48": { income: 0.68, safety: 0.50, employment: 0.74, cost: 0.73, admission_rate: 0.42, chinese_population: 0.38 }, // TX
  "12": { income: 0.64, safety: 0.52, employment: 0.73, cost: 0.72, admission_rate: 0.44, chinese_population: 0.32 }, // FL
  "13": { income: 0.66, safety: 0.54, employment: 0.71, cost: 0.71, admission_rate: 0.46, chinese_population: 0.28 }, // GA
  "37": { income: 0.63, safety: 0.56, employment: 0.69, cost: 0.67, admission_rate: 0.50, chinese_population: 0.22 }, // NC
  "51": { income: 0.70, safety: 0.62, employment: 0.70, cost: 0.70, admission_rate: 0.48, chinese_population: 0.25 }, // VA

  // ── West ──
  "06": { income: 0.90, safety: 0.55, employment: 0.85, cost: 0.85, admission_rate: 0.20, chinese_population: 0.95 }, // CA
  "53": { income: 0.76, safety: 0.65, employment: 0.72, cost: 0.70, admission_rate: 0.42, chinese_population: 0.42 }, // WA
  "41": { income: 0.72, safety: 0.68, employment: 0.70, cost: 0.68, admission_rate: 0.50, chinese_population: 0.28 }, // OR
  "04": { income: 0.58, safety: 0.55, employment: 0.65, cost: 0.64, admission_rate: 0.58, chinese_population: 0.18 }, // AZ
  "32": { income: 0.60, safety: 0.52, employment: 0.64, cost: 0.62, admission_rate: 0.55, chinese_population: 0.15 }, // NV
  "08": { income: 0.74, safety: 0.62, employment: 0.68, cost: 0.66, admission_rate: 0.48, chinese_population: 0.20 }, // CO
};

/**
 * Build RegionMetric objects from the static mock dictionary.
 *
 * Each returned entry mirrors the shape that the Supabase backend will
 * supply once live data is connected.
 */
export function getMockRegionMetrics(
  metricId: MetricId,
  granularity: Granularity = "state",
  year = 2025,
): RegionMetric[] {
  const entries: RegionMetric[] = [];

  for (const [fipsCode, metricValues] of Object.entries(MOCK_NORMALIZED)) {
    const normalised = metricValues[metricId];
    if (normalised === undefined) continue;

    entries.push({
      fipsCode,
      granularity,
      metricId,
      value: normalised,
      rawValue: normalised,
      displayValue: denormaliseDisplayValue(metricId, normalised),
      year,
    });
  }

  return entries;
}

/**
 * Synchronous single-state lookup from mock data.
 *
 * TODO: Replace with a server-side fetch (or SWR/React Query) when
 *       Supabase is integrated.  The return shape should remain
 *       `RegionMetric | null`.
 */
export function getMockMetricForFips(
  fipsCode: string,
  metricId: MetricId,
  granularity: Granularity = "state",
  year = 2025,
): RegionMetric | null {
  const normalised = MOCK_NORMALIZED[fipsCode]?.[metricId];
  if (normalised === undefined) return null;

  return {
    fipsCode,
    granularity,
    metricId,
    value: normalised,
    rawValue: normalised,
    displayValue: denormaliseDisplayValue(metricId, normalised),
    year,
  };
}
