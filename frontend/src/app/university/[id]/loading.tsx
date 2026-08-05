// Loading skeleton for /university/[id].
//
// Server Component (no "use client") so the layout streams in via
// React Server Components while UniversityDetailView fetches.
// Matches the dimensions and tokens of the eventual panel so the
// swap is visually seamless.

import { GraduationCap } from "lucide-react";

export default function UniversityLoading(): JSX.Element {
  return (
    <main className="mx-auto max-w-4xl px-4 py-8" aria-busy="true" aria-label="加载学校档案">
      <div className="animate-pulse space-y-6">
        {/* Back link */}
        <div className="h-4 w-32 rounded bg-line/40" />

        {/* Title block */}
        <header className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-card bg-surface-2">
              <GraduationCap className="h-6 w-6 text-text-muted" aria-hidden="true" />
            </div>
            <div className="flex-1 space-y-2">
              <div className="h-6 w-2/3 rounded bg-line/60" />
              <div className="h-4 w-1/3 rounded bg-line/40" />
            </div>
          </div>
          <div className="h-3 w-1/2 rounded bg-line/40" />
        </header>

        {/* Hero stats */}
        <section className="grid gap-3 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="rounded-card border border-border-soft bg-surface-1 p-4">
              <div className="h-3 w-1/3 rounded bg-line/40" />
              <div className="mt-3 h-6 w-1/2 rounded bg-line/60" />
            </div>
          ))}
        </section>

        {/* Content blocks */}
        <section className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="rounded-card border border-border-soft bg-surface-1 p-4">
              <div className="h-4 w-1/4 rounded bg-line/60" />
              <div className="mt-3 h-3 w-full rounded bg-line/40" />
              <div className="mt-2 h-3 w-5/6 rounded bg-line/40" />
              <div className="mt-2 h-3 w-2/3 rounded bg-line/40" />
            </div>
          ))}
        </section>
      </div>
    </main>
  );
}
