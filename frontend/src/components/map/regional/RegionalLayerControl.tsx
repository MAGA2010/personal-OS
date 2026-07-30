"use client";

// PathOS Stage 7R — Regional Layer Control
//
// Compact dropdown / segmented selector that lets the user pick which
// regional metric (if any) is rendered as a state choropleth. Exposes
// the current selection via a `value`/`onChange` pair, plus the URL
// sync is handled by the parent.

import { useMemo } from "react";
import { ChevronDown, Eye, EyeOff, Layers } from "lucide-react";
import { REGIONAL_METRIC_IDS, type RegionalMetricId } from "@/regional/types";
import { getRegionalMetricDefinition } from "@/regional/load";

interface Props {
  value: RegionalMetricId | null;
  onChange: (next: RegionalMetricId | null) => void;
}

const OPTIONS: Array<{ id: RegionalMetricId | null; labelZh: string; paletteId: string }> = [
  { id: null, labelZh: "不显示区域热力图", paletteId: "__off" },
  ...REGIONAL_METRIC_IDS.map((mid) => {
    const def = getRegionalMetricDefinition(mid);
    return {
      id: mid,
      labelZh: def?.displayNameZh ?? mid,
      paletteId: def?.paletteId ?? "__unknown",
    };
  }),
];

export function RegionalLayerControl({ value, onChange }: Props): JSX.Element {
  const current = useMemo(
    () => OPTIONS.find((o) => o.id === value) ?? OPTIONS[0],
    [value],
  );

  return (
    <div
      data-testid="regional-layer-control"
      className="flex items-center gap-1.5 rounded-control border border-border-soft bg-surface-1/95 px-2 py-1 shadow-sm backdrop-blur"
    >
      <Layers size={12} aria-hidden="true" className="shrink-0 text-cobalt" />
      <span className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
        区域图层
      </span>
      <div className="relative">
        <select
          data-testid="regional-layer-control-select"
          aria-label="选择区域图层"
          value={value ?? ""}
          onChange={(e) => {
            const v = e.target.value;
            if (v === "") {
              onChange(null);
            } else {
              onChange(v as RegionalMetricId);
            }
          }}
          className="appearance-none rounded-control border border-border-soft bg-surface-1 py-1 pl-2 pr-7 text-[11px] font-semibold text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
        >
          {OPTIONS.map((opt) => (
            <option key={opt.id ?? "off"} value={opt.id ?? ""}>
              {opt.id === null ? "不显示区域热力图" : opt.labelZh}
            </option>
          ))}
        </select>
        <ChevronDown
          size={11}
          aria-hidden="true"
          className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 text-text-secondary"
        />
      </div>
      {current.id === null ? (
        <EyeOff size={12} aria-hidden="true" className="text-text-muted" />
      ) : (
        <Eye size={12} aria-hidden="true" className="text-jade" />
      )}
    </div>
  );
}