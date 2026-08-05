"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import Link from "next/link";

export default function UniversityError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  useEffect(() => {
    console.error("[university/[id]] segment crashed:", error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-[calc(100vh-3.5rem)] max-w-2xl flex-col items-center justify-center gap-4 px-6 py-16 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-persimmon/10 text-persimmon">
        <AlertTriangle size={22} aria-hidden="true" />
      </div>
      <div className="space-y-1">
        <h1 className="text-page text-text-primary">学校详情加载失败</h1>
        <p className="max-w-md text-caption text-text-secondary">
          该学校档案暂时无法读取。可能是数据库连接异常，请稍后再试或返回地图查看其他学校。
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
          <RefreshCw size={14} aria-hidden="true" /> 重试加载
        </button>
        <Link
          href="/map"
          className="inline-flex h-control items-center gap-1.5 rounded-control border border-border-soft bg-surface-1 px-4 text-caption font-semibold text-text-primary transition hover:border-cobalt/40 hover:text-cobalt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
        >
          返回地图
        </Link>
      </div>
    </main>
  );
}
