import { MapShell } from "@/components/map/MapShell";
import Link from "next/link";

/**
 * Map Module / 留学地图
 * Interactive choropleth map for study-abroad regional analysis.
 *
 * Data layers (six metrics):
 *   income | safety | toefl | sat | admission_rate | chinese_population
 *
 * TODO: Connect to Supabase when available
 * TODO: Add UniversityPOI markers via supercluster
 * TODO: CampusPOI / streetview transitions on pin click
 */
export default function MapPage() {
  return (
    <main className="flex flex-1 flex-col bg-paper" aria-label="留学地图">
      <header className="flex shrink-0 items-center gap-3 border-b border-line bg-panel px-5 py-3">
        <div className="grid h-8 w-8 place-items-center rounded-md bg-ink text-panel">
          <svg aria-hidden="true" className="h-[18px] w-[18px]" fill="none" stroke="currentColor"
            strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} viewBox="0 0 24 24">
            <circle cx="12" cy="10" r="3" />
            <path d="M12 21.7C17.3 17 20 13 20 10a8 8 0 1 0-16 0c0 3 2.7 7 8 11.7z" />
          </svg>
        </div>
        <div>
          <h1 className="text-base font-semibold text-ink">留学地图</h1>
          <p className="text-xs text-ink/52">六大指标覆盖全美 / China-lens choropleth</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Link
            href="/map/rankings"
            className="flex items-center gap-1.5 rounded-md border border-line/60 bg-white/80 px-3 py-1.5 text-xs font-medium text-ink/60 hover:text-ink hover:border-ink/30 transition-colors"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeLinecap="round"
              strokeLinejoin="round" strokeWidth={2} viewBox="0 0 24 24">
              <path d="M6 20h12M6 10l4 4 4-6 4 4" />
            </svg>
            排名对比
          </Link>
        </div>
      </header>
      <div className="relative flex-1 p-3">
        <MapShell className="h-full" />
      </div>
    </main>
  );
}
