import { Suspense } from "react";
import dynamic from "next/dynamic";

const MapShell = dynamic(
  () => import("@/components/map/MapShell").then((mod) => ({ default: mod.MapShell })),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center text-sm text-ink/40">
        加载地图中...
      </div>
    ),
  }
);

export default function MapPage() {
  return (
    <main className="flex flex-col bg-paper" style={{ height: "calc(100vh - 3.5rem)", overflow: "hidden" }} aria-label="留学地图">
      <div className="relative flex-1 min-h-0">
        <Suspense fallback={<div className="flex h-full items-center justify-center text-sm text-ink/40">加载地图中...</div>}>
          <MapShell className="h-full" />
        </Suspense>
      </div>
    </main>
  );
}
