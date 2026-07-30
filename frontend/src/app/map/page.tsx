import { MapPageShell } from "@/components/map/shell/MapPageShell";

// Stage 7B-A.1 Closing Patch v3 (V3-A) — Server-side /map route.
//
// Previous (v2) version imported `next/dynamic` and gated MapShell
// behind `dynamic({ssr:false})` with a `loading:` fallback.  That
// fallback still produced a structural mismatch vs. MapShell's
// outermost DOM, so React 18 dev mode emitted a hydration warning.
//
// The v3 route delegates everything to a Server Component,
// `MapPageShell`, which statically renders the `<main>` chrome and
// embeds a single client component:
//   - `MapRuntimeClient`  — the mounted-gate wrapper around
//                          `<MapShell />`. Until `mounted === true`
//                          (one-shot `useEffect` flip) it renders
//                          the same SSR-stable placeholder; after
//                          mounted, it renders the real MapShell.
//
// Stage 7B-A.2 Phase 0.1 removed the orphan `MapToolbarClient`
// (floating ③ 留学地图 / 留学资讯 buttons), which were unused
// duplicates of widgets already rendered by MapShell + the news
// sidebar. MapShell itself owns the unified toolbar.
//
// Server pre-render and Client first render both emit the
// placeholder → hydration matches → no warning.  The "real"
// MapShell swaps in on the second render, after hydration completes.
export default function MapPage(): JSX.Element {
  return <MapPageShell />;
}