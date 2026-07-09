"use client";

import type { MetricId } from "@/lib/types";
import { METRIC_DEFINITIONS, METRIC_ORDER } from "@/lib/metrics";

// ── MetricTabs Props ──

interface MetricTabsProps {
  /** The currently selected metric layer. */
  active: MetricId;
  /** Called when the user picks a different metric tab. */
  onSelect: (id: MetricId) => void;
}

// ── Metric Tab Label Mapping ──
//
// Each entry pairs a Chinese label (shown at all breakpoints) with a
// compact form (2-character abbreviation shown on narrow viewports).
// The `METRIC_DEFINITIONS` registry supplies the canonical label/text;
// this map only supplies the abbreviation override.
//
// TODO: Connect to Supabase when available — if metric labels need to
//       be regionalised or A/B tested, pull them from a `metric_labels`
//       table keyed by (metricId, locale).

const METRIC_ABBREVIATIONS: Record<MetricId, string> = {
  income: "收入",
  safety: "安全",
  toefl: "托福",
  sat: "SAT",
  admission_rate: "录取",
  chinese_population: "华人",
};

// ── Component ──

/**
 * MetricTabs — Horizontal pill-style tab bar for selecting the active
 * choropleth metric layer.
 *
 * ## Behaviour
 * - Renders six pill buttons in a fixed left-to-right order (defined by
 *   `METRIC_ORDER`).
 * - The active pill gets a filled `ink` background; inactive pills are
 *   outlined with a transparent hover state.
 * - On narrow viewports (< 640px) each pill shows a 2-character Chinese
 *   abbreviation.  At `sm` and above the full Chinese label is used.
 *
 * ## Accessibility
 * - The wrapping `<nav>` carries an `aria-label` in Chinese.
 * - Each `<button>` sets `aria-pressed` to reflect selection state.
 * - Focus ring (`focus-visible:ring-2`) is included for keyboard nav.
 *
 * ## Data dependencies
 * - `METRIC_ORDER`  — `MetricId[]` tab display order.
 * - `METRIC_DEFINITIONS` — `Record<MetricId, MetricDefinition>` for labels.
 *
 * TODO: Replace with real {metric name} label metadata when i18n is in place.
 * TODO: Connect to Supabase when available — user preference persistence
 *       (last selected metric) via `user_prefs` table.
 */
export function MetricTabs({ active, onSelect }: MetricTabsProps) {
  return (
    <nav
      aria-label="指标图层切换"
      className="flex flex-wrap gap-1.5"
    >
      {METRIC_ORDER.map((id) => {
        const def = METRIC_DEFINITIONS[id];
        const isActive = id === active;
        const abbr = METRIC_ABBREVIATIONS[id];

        return (
          <button
            key={id}
            type="button"
            aria-pressed={isActive}
            aria-label={`${def.label} (${def.labelEn})`}
            onClick={() => onSelect(id)}
            className={[
              // ── Base pill shape ──
              "rounded-full px-3.5 py-1.5 text-xs font-medium",
              // ── Focus ring ──
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cobalt/50 focus-visible:ring-offset-1",
              // ── Transition ──
              "transition-all duration-150",
              // ── Active state ──
              isActive
                ? "bg-ink text-paper shadow-sm"
                : [
                    "border border-line/60",
                    "bg-white/88 text-ink/64",
                    "hover:bg-white hover:text-ink/82",
                    "active:bg-paper active:text-ink/72",
                  ].join(" "),
            ].join(" ")}
          >
            {/* Compact label: visible below sm */}
            <span className="block sm:hidden" aria-hidden={false}>
              {abbr}
            </span>

            {/* Full Chinese label: visible at sm and above */}
            <span className="hidden sm:block">{def.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
