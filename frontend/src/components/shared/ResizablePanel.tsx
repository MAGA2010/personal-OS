"use client";

// Stage 7A — ResizablePanel.
//
// Generic edge-docked panel with a draggable resize handle on its inner
// edge. Persists its width to localStorage under the given key so a
// returning user gets the same layout. Falls back to the supplied
// default width when storage is unavailable (private mode, quota).
//
// Usage:
//   <ResizablePanel edge="right" storageKey="pathos:map:detail" defaultWidth={360}>
//     {children}
//   </ResizablePanel>

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

export type PanelEdge = "left" | "right" | "top" | "bottom";

export interface ResizablePanelProps {
  edge: PanelEdge;
  storageKey?: string;
  /** Default width in px (when edge is left/right) or height (top/bottom). */
  defaultWidth: number;
  /** Minimum size in px. */
  minSize?: number;
  /** Maximum size in px. Defaults to a generous cap. */
  maxSize?: number;
  className?: string;
  /** When false, the panel collapses to zero width/height. */
  open?: boolean;
  children?: ReactNode;
}

const DEFAULT_MIN = 240;
const DEFAULT_MAX = 720;

export function ResizablePanel({
  edge,
  storageKey,
  defaultWidth,
  minSize = DEFAULT_MIN,
  maxSize = DEFAULT_MAX,
  className = "",
  open = true,
  children,
}: ResizablePanelProps) {
  const [size, setSize] = useState<number>(defaultWidth);
  const [hydrated, setHydrated] = useState(false);
  const dragRef = useRef<{ startPos: number; startSize: number } | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Hydrate from localStorage once.
  useEffect(() => {
    if (!storageKey || typeof window === "undefined") {
      setHydrated(true);
      return;
    }
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (raw !== null) {
        const v = Number(raw);
        if (Number.isFinite(v) && v >= minSize && v <= maxSize) setSize(v);
      }
    } catch {
      /* quota / private mode — ignore */
    }
    setHydrated(true);
  }, [storageKey, minSize, maxSize]);

  // Persist on size change (after hydration so we don't overwrite stored).
  useEffect(() => {
    if (!hydrated || !storageKey || typeof window === "undefined") return;
    try {
      window.localStorage.setItem(storageKey, String(size));
    } catch {
      /* ignore */
    }
  }, [size, hydrated, storageKey]);

  const onPointerDown = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (!open) return;
    event.preventDefault();
    const startPos = edge === "left" || edge === "right" ? event.clientX : event.clientY;
    dragRef.current = { startPos, startSize: size };
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    document.body.style.cursor = edge === "left" || edge === "right" ? "col-resize" : "row-resize";
  }, [edge, open, size]);

  const onPointerMove = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (!dragRef.current) return;
    const currentPos = edge === "left" || edge === "right" ? event.clientX : event.clientY;
    const delta = currentPos - dragRef.current.startPos;
    // For a right-edge panel, dragging left shrinks it; for a left-edge
    // panel, dragging right shrinks it. Mirror the sign accordingly.
    const next = edge === "right"
      ? dragRef.current.startSize - delta
      : edge === "left"
        ? dragRef.current.startSize + delta
        : edge === "top"
          ? dragRef.current.startSize + delta
          : dragRef.current.startSize - delta;
    const clamped = Math.max(minSize, Math.min(maxSize, next));
    setSize(clamped);
  }, [edge, minSize, maxSize]);

  const onPointerUp = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    dragRef.current = null;
    document.body.style.cursor = "";
    try { (event.currentTarget as HTMLElement).releasePointerCapture(event.pointerId); } catch { /* ignore */ }
  }, []);

  // Keyboard accessibility: arrow keys when handle is focused.
  const onKeyDown = useCallback((event: React.KeyboardEvent<HTMLDivElement>) => {
    const step = event.shiftKey ? 32 : 8;
    const dir = edge === "right" || edge === "bottom" ? -1 : 1;
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      setSize((s) => Math.max(minSize, Math.min(maxSize, s + dir * step)));
      event.preventDefault();
    } else if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      setSize((s) => Math.max(minSize, Math.min(maxSize, s - dir * step)));
      event.preventDefault();
    }
  }, [edge, minSize, maxSize]);

  const isVertical = edge === "left" || edge === "right";
  const sizeStyle: React.CSSProperties = isVertical
    ? { width: open ? size : 0 }
    : { height: open ? size : 0 };

  const handleOrientation = isVertical ? "vertical" : "horizontal";

  return (
    <div
      ref={containerRef}
      className={`relative shrink-0 overflow-hidden transition-[width,height] duration-200 ease-out ${className}`}
      style={sizeStyle}
      aria-hidden={!open}
    >
      <div className="h-full w-full">{children}</div>
      {open && (
        <div
          role="separator"
          aria-orientation={handleOrientation}
          aria-valuenow={size}
          aria-valuemin={minSize}
          aria-valuemax={maxSize}
          tabIndex={0}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onKeyDown={onKeyDown}
          className={
            (edge === "right"
              ? "absolute left-0 top-0 h-full w-1.5 cursor-col-resize border-l border-transparent hover:border-cobalt/40"
              : edge === "left"
                ? "absolute right-0 top-0 h-full w-1.5 cursor-col-resize border-r border-transparent hover:border-cobalt/40"
                : edge === "top"
                  ? "absolute bottom-0 left-0 w-full h-1.5 cursor-row-resize border-b border-transparent hover:border-cobalt/40"
                  : "absolute top-0 left-0 w-full h-1.5 cursor-row-resize border-t border-transparent hover:border-cobalt/40") +
            " bg-transparent focus:outline-none focus-visible:bg-cobalt/10"
          }
          title="拖拽调整大小"
        />
      )}
    </div>
  );
}

export default ResizablePanel;