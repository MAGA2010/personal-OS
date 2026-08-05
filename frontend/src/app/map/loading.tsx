// Loading skeleton for /map.
//
// Server Component (no "use client") so it streams in via React
// Server Components as soon as the route begins to resolve. Renders
// the same outer DOM as `MapPageShell` so hydration is visually
// seamless when MapShell swaps in.

export default function MapLoading(): JSX.Element {
  return (
    <main
      className="flex flex-col bg-paper"
      style={{ height: "calc(100vh - 3.5rem)", overflow: "hidden" }}
      aria-label="加载留学地图"
      aria-busy="true"
    >
      <div className="relative flex-1 min-h-0 animate-pulse">
        {/* Map canvas placeholder */}
        <div className="absolute inset-0 bg-surface-2" />
        {/* Fake toolbar */}
        <div className="absolute left-4 top-4 flex flex-col gap-2">
          <div className="h-9 w-40 rounded-control bg-surface-1/80 shadow-pop" />
          <div className="h-9 w-32 rounded-control bg-surface-1/80 shadow-pop" />
        </div>
        {/* Fake legend */}
        <div className="absolute right-4 bottom-4 h-24 w-44 rounded-card bg-surface-1/80 p-3 shadow-pop">
          <div className="h-3 w-1/2 rounded bg-line/60" />
          <div className="mt-3 space-y-2">
            <div className="h-2 w-3/4 rounded bg-line/40" />
            <div className="h-2 w-2/3 rounded bg-line/40" />
            <div className="h-2 w-1/2 rounded bg-line/40" />
          </div>
        </div>
        {/* Fake markers */}
        <div className="absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-cobalt/40" />
        <div className="absolute left-[35%] top-[40%] h-3 w-3 rounded-full bg-cobalt/30" />
        <div className="absolute left-[60%] top-[55%] h-3 w-3 rounded-full bg-cobalt/30" />
        <div className="absolute left-[20%] top-[60%] h-3 w-3 rounded-full bg-cobalt/30" />
        <div className="absolute left-[70%] top-[30%] h-3 w-3 rounded-full bg-cobalt/30" />
      </div>
    </main>
  );
}