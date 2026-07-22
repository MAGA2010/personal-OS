import { MapShell } from "@/components/map/MapShell";
import Link from "next/link";
import { Newspaper } from "lucide-react";

export default function MapPage() {
  return (
    <main className="flex flex-col bg-paper" style={{ height: "calc(100vh - 3.5rem)", overflow: "hidden" }} aria-label="留学地图">
      {/* Mini floating news button */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
        <div className="flex items-center gap-1.5 rounded-lg bg-white/85 backdrop-blur border border-line/50 px-3 py-1.5 shadow-xs">
          <svg aria-hidden="true" className="h-4 w-4 text-ink/60" fill="none" stroke="currentColor"
            strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} viewBox="0 0 24 24">
            <circle cx="12" cy="10" r="3" />
            <path d="M12 21.7C17.3 17 20 13 20 10a8 8 0 1 0-16 0c0 3 2.7 7 8 11.7z" />
          </svg>
          <span className="text-xs font-medium text-ink/70">③ 留学地图</span>
        </div>
      </div>
      <div className="absolute top-3 right-3 z-10 flex items-center gap-2">
        <Link
          href="/news"
          className="flex items-center gap-1.5 rounded-lg bg-white/85 backdrop-blur border border-line/50 px-3 py-1.5 text-xs font-medium text-ink/60 hover:text-ink hover:border-ink/30 transition-colors shadow-xs"
        >
          <Newspaper size={14} />
          留学资讯
        </Link>
      </div>
      <div className="relative flex-1 min-h-0">
        <MapShell className="h-full" />
      </div>
    </main>
  );
}
