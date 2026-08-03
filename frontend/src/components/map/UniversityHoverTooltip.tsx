"use client";

// Stage 7A — UniversityHoverTooltip.
// Small floating card rendered while the user hovers a POI. Anchored
// to the right of the cursor by default, but flips left/up when near
// the right/bottom edge of the map container. Disappears when the
// user moves the mouse off the marker. Never blocks map dragging
// (pointer-events:none).

import { useEffect, useRef, useState } from "react";
import type { UniversitySummary } from "@/domain/dataset";
import { tuitionRmbFromSummary } from "@/lib/legacy-mappers";
import { useEdgeFlippedPosition } from "@/components/shared/useEdgeFlippedPosition";

export interface UniversityHoverTooltipProps {
  /** The hovered summary. When null, the tooltip is hidden. */
  summary: UniversitySummary | null;
  /** Pixel coordinates of the cursor inside the map container. */
  x: number;
  y: number;
}

const TOOLTIP_MAX_WIDTH = 260;
const APPROX_HEIGHT = 80;

export function UniversityHoverTooltip({ summary, x, y }: UniversityHoverTooltipProps) {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [containerRect, setContainerRect] = useState<DOMRect | null>(null);

  // Track the nearest map container so we can flip within its bounds
  // rather than the full viewport. The container is the wrapper div
  // with `aria-label="MapLibre 地图视窗"`.
  useEffect(() => {
    if (!summary) return;
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
  }, [summary]);

  const pos = useEdgeFlippedPosition({
    anchorX: x,
    anchorY: y,
    tooltipWidth: TOOLTIP_MAX_WIDTH,
    tooltipHeight: APPROX_HEIGHT,
    containerRect,
    padding: 8,
    preferredOffset: 14,
  });

  if (!summary) return null;
  const tuition = tuitionRmbFromSummary(summary);
    const ugCount = summary.enrollmentSummary?.undergraduate ?? null;
const costLabel = tuition !== null ? `¥${Math.round(tuition / 10000)}万/年` : "未报告";
  const tier = summary.rankingSummary?.rankingTier ?? summary.rankingTier ?? null;
  return (
    <div
      ref={tooltipRef}
      role="tooltip"
      aria-live="polite"
      data-testid="university-hover-tooltip"
      data-placement-h={pos.horizontal}
      data-placement-v={pos.vertical}
      className="pointer-events-none fixed z-map-tooltip max-w-[260px] rounded-lg border border-line/70 bg-panel/95 px-3 py-2 text-[11px] shadow-lg backdrop-blur"
      style={{ left: pos.left, top: pos.top }}
    >
      <div className="font-semibold text-ink truncate">{summary.chineseName || summary.name}</div>
      {summary.name && summary.chineseName !== summary.name && (
        <div className="truncate text-ink/55" lang="en">{summary.name}</div>
      )}
      <div className="mt-1 flex items-center gap-2 text-ink/60">
        {tier && (
          <span className="rounded-full border border-line/60 bg-paper px-1.5 py-0.5 text-[9px] font-medium text-ink/72">{tier}</span>
        )}
        <span>{costLabel}</span>
       {ugCount !== null && ugCount > 0 && (
          <span className="text-ink/72">{ugCount >= 1000 ? (ugCount/1000).toFixed(1) + 'k' : ugCount}</span>
        )}
        </div>
      {(summary.city || summary.state) && (
        <div className="mt-0.5 text-ink/45">
          {[summary.city, summary.state].filter(Boolean).join(" · ")}
        </div>
      )}
    </div>
  );
}

export default UniversityHoverTooltip;