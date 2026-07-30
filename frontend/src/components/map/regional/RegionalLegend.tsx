"use client";

// PathOS Stage 7R — Regional Heatmap Legend
//
// Shows the active metric's name, year, unit, direction, color stops,
// coverage, and source. Designed to read on both light and dark themes.

import { useMemo } from "react";
import { Info } from "lucide-react";
import type { RegionalMetricId } from "@/regional/types";
import { getRegionalMetricDefinition } from "@/regional/load";
import { getPalette } from "@/regional/palettes";

interface Props {
  activeMetricId: RegionalMetricId | null;
  themeMode: "light" | "dark";
  verifiedCount: number;
  totalCount: number;
  sourceWorkbookSha256: string;
}

export function RegionalLegend({
  activeMetricId,
  themeMode,
  verifiedCount,
  totalCount,
  sourceWorkbookSha256,
}: Props): JSX.Element | null {
  const def = useMemo(
    () => (activeMetricId ? getRegionalMetricDefinition(activeMetricId) : undefined),
    [activeMetricId],
  );
  const palette = useMemo(
    () => (def ? getPalette(def.paletteId, themeMode) : null),
    [def, themeMode],
  );

  if (!def || !palette || activeMetricId === null) return null;

  // Bucket labels — five equal buckets across [0,1] normalized space
  const bucketLabels = ["低", "偏低", "中", "偏高", "高"];
  const directionZh = def.higherIsBetter
    ? "数值越高越好"
    : def.rawDirection === "inverse"
    ? "原始值越低越好（标准化值越高越好）"
    : "数值越低越好";

  return (
    <div
      data-testid="regional-legend"
      role="region"
      aria-label={`${def.displayNameZh} 图例`}
      className="rounded-control border border-border-soft bg-surface-1/95 p-3 text-caption shadow-md backdrop-blur"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-[12px] font-semibold text-text-primary">
          {def.displayNameZh}
          <span className="ml-1 text-[10px] font-normal text-text-secondary">
            {def.displayNameEn}
          </span>
        </p>
        <span
          aria-label="仅用于地图探索"
          title="仅用于地图探索"
          className="rounded-full border border-border-soft bg-surface-2 px-2 py-0.5 text-[10px] text-text-muted"
        >
          仅地图探索
        </span>
      </div>
      <p className="mt-1 text-[10px] text-text-secondary">
        {def.referenceYear} · {def.rawUnit} · {directionZh}
      </p>
      <div
        role="img"
        aria-label={`${def.displayNameZh} 色阶：低、偏低、中、偏高、高`}
        className="mt-2 flex h-3 overflow-hidden rounded-control border border-border-soft"
      >
        {palette.stops.map((color, idx) => (
          <span
            key={`${color}-${idx}`}
            className="flex-1"
            style={{ backgroundColor: color }}
            aria-hidden="true"
          />
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[9px] text-text-muted">
        {bucketLabels.map((l, i) => (
          <span key={`${l}-${i}`}>{l}</span>
        ))}
      </div>
      <div className="mt-2 flex items-center justify-between text-[10px] text-text-secondary">
        <span>
          覆盖 <span className="font-semibold text-text-primary">{verifiedCount}</span>/
          {totalCount} 州 (含 DC)
        </span>
        <span
          aria-label="缺失值显示为中性灰"
          title="缺失值显示为中性灰"
          className="flex items-center gap-1"
        >
          <span
            aria-hidden="true"
            className="inline-block h-2.5 w-3 rounded-sm border border-border-soft"
            style={{ backgroundColor: palette.missing }}
          />
          缺失
        </span>
      </div>
      <p className="mt-2 flex items-start gap-1 text-[10px] text-text-secondary">
        <Info size={10} aria-hidden="true" className="mt-0.5 shrink-0" />
        <span>
          来源: {def.sourceName}
          {def.sourceUrl ? (
            <>
              {" · "}
              <a
                href={def.sourceUrl}
                target="_blank"
                rel="noreferrer"
                className="text-cobalt underline-offset-2 hover:underline"
              >
                链接
              </a>
            </>
          ) : null}
        </span>
      </p>
      <p className="mt-1 text-[9px] text-text-muted">
        数据原始工作簿 SHA: <span className="font-mono">{sourceWorkbookSha256.slice(0, 12)}…</span>
      </p>
    </div>
  );
}