"use client";

// PathOS Stage 7R — Regional Hover Tooltip
//
// Cursor-following tooltip. Receives the hovered region's record from
// the RegionalStateLayer. Uses `position: fixed` to escape ancestor
// overflow rules; `pointer-events: none` so it never blocks map drag.
// Stage 7B-A.3: edge-flips when near the right/bottom edge of the
// map container.

import { useEffect, useRef, useState } from "react";
import type { RegionalMetricRecord } from "@/regional/types";
import { useEdgeFlippedPosition } from "@/components/shared/useEdgeFlippedPosition";

interface Props {
  hoveredRecord: RegionalMetricRecord | null;
  pointer: { x: number; y: number } | null;
}

const TOOLTIP_MAX_WIDTH = 260;
const APPROX_HEIGHT = 110;

export function RegionalHoverTooltip({ hoveredRecord, pointer }: Props): JSX.Element | null {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [containerRect, setContainerRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    if (!hoveredRecord) return;
    const root = tooltipRef.current?.closest("[data-map-canvas-root='true']") as HTMLElement | null;
    if (!root) return;
    const update = () => setContainerRect(root.getBoundingClientRect());
    update();
    const ro = new ResizeObserver(update);
    ro.observe(root);
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      ro.disconnect();
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [hoveredRecord]);

  const pos = useEdgeFlippedPosition({
    anchorX: pointer?.x ?? 0,
    anchorY: pointer?.y ?? 0,
    tooltipWidth: TOOLTIP_MAX_WIDTH,
    tooltipHeight: APPROX_HEIGHT,
    containerRect,
    padding: 8,
    preferredOffset: 12,
  });

  if (!hoveredRecord || !pointer) return null;
  const r = hoveredRecord;
  const isMissing = r.rawValue === null || r.normalizedValue === null;
  return (
    <div
      ref={tooltipRef}
      role="tooltip"
      aria-live="polite"
      data-testid="regional-hover-tooltip"
      data-missing={isMissing ? "true" : "false"}
      data-placement-h={pos.horizontal}
      data-placement-v={pos.vertical}
      className="pointer-events-none fixed z-map-tooltip max-w-[260px] rounded-control border border-border-soft bg-surface-1 p-2 text-caption text-text-primary shadow-lg"
      style={{ left: pos.left, top: pos.top }}
    >
      <p className="text-[12px] font-semibold text-text-primary">
        {r.geoName}
        <span className="ml-1 text-[10px] font-normal text-text-secondary">
          {r.geoNameEn}
        </span>
      </p>
      {isMissing ? (
        <p className="mt-1 text-[11px] text-persimmon">该区域暂无该指标数据</p>
      ) : (
        <>
          <p className="mt-1 text-[11px]">
            <span className="text-text-secondary">原始值: </span>
            <span className="font-semibold text-text-primary">
              {r.displayValue ?? String(r.rawValue)}
            </span>
          </p>
          <p className="text-[11px]">
            <span className="text-text-secondary">标准化: </span>
            <span className="font-mono text-text-primary">{r.normalizedValue?.toFixed(3)}</span>
            <span className="ml-1 text-text-muted">/ 1.000</span>
          </p>
          <p className="mt-1 text-[9px] text-text-muted">
            单位: {r.metricId} · 年份: {r.referenceYear}
          </p>
        </>
      )}
      <p className="mt-1 text-[9px] text-text-muted">
        来源: {r.sourceId} · 工作簿行 {r.sourceRow}
      </p>
    </div>
  );
}