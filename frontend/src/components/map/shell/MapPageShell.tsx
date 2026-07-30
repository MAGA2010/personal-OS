import { MapRuntimeClient } from "./MapRuntimeClient";

/**
 * Stage 7B-A.1 Closing Patch v3 (V3-A) — SSR-stable page shell
 * ----------------------------------------------------------------
 * Server Component. Renders the `<main>` element + the host div
 * where `MapShell` will mount.
 */
export function MapPageShell(): JSX.Element {
  return (
    <main
      className="flex flex-col bg-paper"
      style={{ height: "calc(100vh - 3.5rem)", overflow: "hidden" }}
      aria-label="留学地图"
    >
      <div className="relative flex-1 min-h-0">
        <MapRuntimeClient />
      </div>
    </main>
  );
}