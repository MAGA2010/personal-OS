// ── PathOS Metric Configuration (frontend-only) ──
// UI metadata for the choropleth / marker metric layers.
// Hold no business data; data values come from the backend data source.

import type { MetricDefinition, MetricId } from "@/lib/types";

/**
 * Registry of metric layers (UI metadata only).
 * Data values live in the `useRegionMetrics` / `useUniversityDetail` hooks.
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

/** Tab order for the metric switcher (left-to-right in the UI). */
export const METRIC_ORDER: MetricId[] = [
  "income",
  "safety",
  "employment",
  "cost",
  "chinese_population",
];

/** Format a user-visible metric value for tooltips, legends, and infoboxes. */
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
    case "chinese_population":
      return `${rawValue.toFixed(1)}%`;
    default: {
      const _exhaustive: never = metricId;
      return `${rawValue}`;
    }
  }
}

/** Per-metric supported render mode (UI hint, not data). */
export const METRIC_RENDER_MODE: Record<MetricId, "region_choropleth" | "university_marker"> = {
  income: "region_choropleth",
  safety: "region_choropleth",
  employment: "region_choropleth",
  cost: "region_choropleth",
  chinese_population: "region_choropleth",
};
