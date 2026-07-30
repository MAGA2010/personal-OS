"use client";

// Stage 7A — BottomSheet.
//
// Mobile-only bottom sheet with three snap points: collapsed (peek),
// half, expanded (full minus header). Drag handle + arrow buttons.
// Persists the active snap across navigations via localStorage.
//
// Designed for portrait phones; on wider viewports the parent should
// not render it (we don't add internal media queries here — the parent
// owns responsive layout).

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

export type Snap = "collapsed" | "half" | "expanded";

export interface BottomSheetProps {
  storageKey?: string;
  /** Initial snap on first render. Defaults to "collapsed". */
  defaultSnap?: Snap;
  /** Optional title rendered in the drag bar. */
  title?: ReactNode;
  className?: string;
  children?: ReactNode;
  /**
   * Escape-key handler. Fired when the user presses Escape while
   * the sheet is on top of the focus stack. Stage 7B-A.3: required so
   * keyboard users have a discoverable close affordance.
   */
  onEscape?: () => void;
  /**
   * Stable test id for collision-matrix regression tests.
   * Stage 7B-A.3: pinned so the "single BottomSheet" invariant is
   * testable from source-text assertions.
   */
  "data-testid"?: string;
}

const SNAP_TO_HEIGHT: Record<Snap, number> = {
  collapsed: 96,
  half: 0.5,
  expanded: 0.92,
};

const NEXT_SNAP: Record<Snap, Snap> = {
  collapsed: "half",
  half: "expanded",
  expanded: "collapsed",
};

export function BottomSheet({
  storageKey,
  defaultSnap = "collapsed",
  title,
  className = "",
  children,
  onEscape,
  "data-testid": dataTestId,
}: BottomSheetProps) {
  const [snap, setSnap] = useState<Snap>(defaultSnap);
  const [hydrated, setHydrated] = useState(false);
  const [dragOffset, setDragOffset] = useState(0);
  const startRef = useRef<{ startY: number; snap: Snap; vh: number } | null>(null);

  // Hydrate stored snap.
  useEffect(() => {
    if (!storageKey || typeof window === "undefined") {
      setHydrated(true);
      return;
    }
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (raw === "collapsed" || raw === "half" || raw === "expanded") setSnap(raw);
    } catch { /* ignore */ }
    setHydrated(true);
  }, [storageKey]);

  // Persist on snap change.
  useEffect(() => {
    if (!hydrated || !storageKey || typeof window === "undefined") return;
    try {
      window.localStorage.setItem(storageKey, snap);
    } catch { /* ignore */ }
  }, [snap, hydrated, storageKey]);

  // Stage 7B-A.3: Escape key dismisses the sheet. The handler is only
  // attached when `onEscape` is provided so the component remains a
  // generic primitive for callers that don't want escape dismissal.
  useEffect(() => {
    if (!onEscape || typeof window === "undefined") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onEscape();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onEscape]);

  const computeHeight = useCallback((s: Snap, vh: number) => {
    const v = SNAP_TO_HEIGHT[s];
    return typeof v === "number" && v < 1 ? Math.round(vh * v) : v;
  }, []);

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    startRef.current = { startY: event.clientY, snap, vh: window.innerHeight };
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!startRef.current) return;
    const delta = event.clientY - startRef.current.startY;
    setDragOffset(delta);
  };

  const onPointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!startRef.current) return;
    const { startY, snap: startSnap, vh } = startRef.current;
    const delta = event.clientY - startY;
    const startHeight = computeHeight(startSnap, vh);
    const finalHeight = startHeight - delta;
    // Snap to nearest preset.
    const candidates: Snap[] = ["collapsed", "half", "expanded"];
    let bestSnap: Snap = startSnap;
    let bestDiff = Infinity;
    for (const c of candidates) {
      const diff = Math.abs(computeHeight(c, vh) - finalHeight);
      if (diff < bestDiff) {
        bestDiff = diff;
        bestSnap = c;
      }
    }
    startRef.current = null;
    setDragOffset(0);
    setSnap(bestSnap);
    try { (event.currentTarget as HTMLElement).releasePointerCapture(event.pointerId); } catch { /* ignore */ }
  };

  const vh = typeof window !== "undefined" ? window.innerHeight : 800;
  const baseHeight = computeHeight(snap, vh);
  const height = Math.max(96, baseHeight - dragOffset);

  return (
    <div
      role="dialog"
      aria-modal="false"
      data-testid={dataTestId ?? "bottom-sheet"}
      data-snap={snap}
      className={"pointer-events-auto fixed inset-x-0 bottom-0 z-40 flex flex-col rounded-t-2xl border-t border-line bg-panel shadow-2xl transition-[height] duration-200 ease-out " + className}
      style={{ height: `${height}px` }}
    >
      <div
        className="flex shrink-0 cursor-grab touch-none items-center justify-between gap-3 border-b border-line/50 px-4 pb-[max(env(safe-area-inset-bottom),0.5rem)] pt-2 active:cursor-grabbing"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div className="flex items-center gap-2 text-ink/72">
          <span className="block h-1 w-10 rounded-full bg-line" aria-hidden="true" />
          <span className="text-[11px] font-semibold">{title ?? "详情"}</span>
        </div>
        <button
          type="button"
          onClick={() => setSnap(NEXT_SNAP[snap])}
          className="grid h-7 w-7 place-items-center rounded-full text-ink/60 hover:bg-line/40 hover:text-ink"
          aria-label={snap === "expanded" ? "收起" : snap === "collapsed" ? "展开" : "切换"}
        >
          {snap === "expanded" ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </button>
      </div>
      <div className="flex-1 overflow-hidden">{children}</div>
    </div>
  );
}

export default BottomSheet;