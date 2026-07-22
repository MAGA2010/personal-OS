import { MapShell } from "@/components/map/MapShell";

export default function MapPage() {
  return (
<main className="flex flex-col bg-paper" style={{ height: 'calc(100vh - 3.5rem)', overflow: 'hidden' }} aria-label="留学地图">
      <div className="relative flex-1 min-h-0">
        <MapShell className="h-full" />
      </div>
    </main>
  );
}
