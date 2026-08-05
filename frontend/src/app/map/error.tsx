"use client";

// Route-level error boundary for /map.
//
// Catches any uncaught throw from the map subtree (e.g. a transient
// Supabase blip during client-side hydration) and renders a calm
// recovery surface instead of the Next.js red error overlay. The
// retry button calls `reset()` which re-renders the segment with
// the same initial props; on a fresh navigation it falls back to a
// hard reload so a stale client cache cannot loop on the same throw.

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function MapError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  useEffect(() => {
    console.error("[map] segment crashed:", error);
  }, [error]);

  return (
    <main
      className="mx-auto flex min-h-[calc(100vh-3.5rem)] max-w-page flex-col items-center justify-center gap-4 px-6 py-16 text-center"
      aria-live="polite"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-persimmon/10 text-persimmon">
        <AlertTriangle size={22} aria-hidden="true" />
      </div>
      <div className="space-y-1">
        <h1 className="text-page text-text-primary">地图加载失败</h1>
        <p className="max-w-md text-caption text-text-secondary">
          留学地图暂时无法渲染。可能是数据库正在升级或网络中断，请稍后再试。
        </p>
        {error.digest ? (
          <p className="font-mono text-[11px] text-text-muted">trace: {error.digest}</p>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center justify-center gap-2">
        <button
          type="button"
          onClick={() => reset()}
          className="inline-flex h-control items-center gap-1.5 rounded-control bg-cobalt px-4 text-caption font-semibold text-paper transition hover:bg-cobalt/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
        >
          <RefreshCw size={14} aria-hidden="true" /> 重试渲染
        </button>
        <button
          type="button"
          onClick={() => {
            if (typeof window !== "undefined") window.location.reload();
          }}
          className="inline-flex h-control items-center gap-1.5 rounded-control border border-border-soft bg-surface-1 px-4 text-caption font-semibold text-text-primary transition hover:border-cobalt/40 hover:text-cobalt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
        >
          刷新页面
        </button>
      </div>
    </main>
  );
}