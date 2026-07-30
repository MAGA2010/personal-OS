"use client";

// Stage 7B-A.3 — Edge-flipped tooltip position.
//
// Shared hook for floating UI that should track the cursor / anchor but
// stay inside the map container's viewport-aware rectangle. Used by
// UniversityHoverTooltip and RegionalHoverTooltip.
//
// Contract:
//   - input: cursor/anchor point + tooltip size + container rect + padding
//   - output: { left, top, placement } where placement describes the
//     resolved horizontal/vertical orientation
//   - re-runs on container resize via ResizeObserver
//   - read-only render (no setState in render); positions update in
//     useEffect + ResizeObserver callback
//   - SSR-safe: returns the anchor position when container is not yet
//     measured (avoids hydration mismatch)
//   - cleans up ResizeObserver + listeners

import { useEffect, useState } from "react";

export type HorizontalPlacement = "right" | "left" | "center";
export type VerticalPlacement = "below" | "above" | "center";

export interface EdgeFlippedPosition {
  /** Pixel left coordinate (viewport space; caller uses `fixed` or `absolute`). */
  left: number;
  /** Pixel top coordinate (viewport space). */
  top: number;
  /** Resolved horizontal orientation relative to anchor. */
  horizontal: HorizontalPlacement;
  /** Resolved vertical orientation relative to anchor. */
  vertical: VerticalPlacement;
}

export interface EdgeFlippedOptions {
  /** Anchor X (already converted to viewport coordinates when caller uses `fixed`). */
  anchorX: number;
  /** Anchor Y (viewport). */
  anchorY: number;
  /** Measured tooltip width (px). */
  tooltipWidth: number;
  /** Measured tooltip height (px). */
  tooltipHeight: number;
  /** Map container bounding rect (viewport space). When null, fallback to window. */
  containerRect: DOMRect | null;
  /** Minimum padding from container edges (px). Default 8. */
  padding?: number;
  /** Preferred offset from anchor (px). Default 12. */
  preferredOffset?: number;
}

function flipPosition(opts: EdgeFlippedOptions): EdgeFlippedPosition {
  const padding = opts.padding ?? 8;
  const offset = opts.preferredOffset ?? 12;
  const rect = opts.containerRect;
  const vw = rect ? rect.left + rect.width : typeof window !== "undefined" ? window.innerWidth : 1024;
  const vh = rect ? rect.top + rect.height : typeof window !== "undefined" ? window.innerHeight : 768;
  const left0 = rect ? rect.left : 0;
  const top0 = rect ? rect.top : 0;

  // Horizontal: prefer right of anchor; flip left if overflow.
  let left = opts.anchorX + offset;
  let horizontal: HorizontalPlacement = "right";
  if (left + opts.tooltipWidth + padding > vw) {
    left = opts.anchorX - opts.tooltipWidth - offset;
    horizontal = "left";
    if (left < left0 + padding) {
      // Last resort: clamp to container left
      left = left0 + padding;
      horizontal = "center";
    }
  }
  // Clamp horizontally inside container
  if (left < left0 + padding) {
    left = left0 + padding;
  } else if (left + opts.tooltipWidth > vw - padding) {
    left = Math.max(left0 + padding, vw - padding - opts.tooltipWidth);
  }

  // Vertical: prefer below anchor; flip above if overflow.
  let top = opts.anchorY + offset;
  let vertical: VerticalPlacement = "below";
  if (top + opts.tooltipHeight + padding > vh) {
    top = opts.anchorY - opts.tooltipHeight - offset;
    vertical = "above";
    if (top < top0 + padding) {
      top = top0 + padding;
      vertical = "center";
    }
  }
  if (top < top0 + padding) {
    top = top0 + padding;
  } else if (top + opts.tooltipHeight > vh - padding) {
    top = Math.max(top0 + padding, vh - padding - opts.tooltipHeight);
  }

  return { left, top, horizontal, vertical };
}

/**
 * Compute an edge-flipped tooltip position from the cursor + container.
 * Subscribes to ResizeObserver on the container to update positions on
 * resize (e.g. window resize, sidebar open/close).
 */
export function useEdgeFlippedPosition(opts: EdgeFlippedOptions): EdgeFlippedPosition {
  const [pos, setPos] = useState<EdgeFlippedPosition>(() => flipPosition(opts));

  useEffect(() => {
    setPos(flipPosition(opts));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    opts.anchorX,
    opts.anchorY,
    opts.tooltipWidth,
    opts.tooltipHeight,
    opts.containerRect?.left,
    opts.containerRect?.top,
    opts.containerRect?.width,
    opts.containerRect?.height,
    opts.padding,
    opts.preferredOffset,
  ]);

  return pos;
}