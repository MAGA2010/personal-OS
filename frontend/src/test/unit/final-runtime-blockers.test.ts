import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

const FRONTEND_ROOT = resolve(__dirname, "../../..");

afterEach(() => {
  vi.useRealTimers();
});

function readSource(relativePath: string): string {
  return readFileSync(resolve(FRONTEND_ROOT, relativePath), "utf8");
}

describe("final runtime blocker regressions", () => {
  it("provides a stable /compare entry to the canonical map comparison experience", () => {
    const route = "src/app/compare/page.tsx";
    expect(existsSync(resolve(FRONTEND_ROOT, route))).toBe(true);
    const source = readSource(route);

    expect(source).toContain('redirect("/map")');
    expect(source).not.toMatch(/universities\.json|mock/i);
  });

  it("uses native layer minzoom instead of lossy feature-state for POI visibility", async () => {
    const poiModule = await import("@/components/map/UniversityPoiLayer");
    const normalizePoiMinZoom = (poiModule as Record<string, unknown>).normalizePoiMinZoom;
    expect(normalizePoiMinZoom).toBeTypeOf("function");

    const normalize = normalizePoiMinZoom as (value: number) => number;
    expect(normalize(0)).toBe(0);
    expect(normalize(5)).toBe(5);
    expect(normalize(-1)).toBe(0);
    expect(normalize(Number.NaN)).toBe(0);

    const source = readSource("src/components/map/UniversityPoiLayer.tsx");
    expect(source).not.toContain('["feature-state", "visible"]');
    expect(source.match(/minzoom:\s*layerMinZoom/g)).toHaveLength(4);
    expect(source).toContain('map.on("style.load", onStyleLoad)');
    expect(source).toContain('map.on("click", POINT_LAYER_ID, handleClick)');
  });

  it("installs POI layers after style readiness without waiting for a stale load event", async () => {
    vi.useFakeTimers();
    const poiModule = await import("@/components/map/UniversityPoiLayer");
    const deferInstall = (poiModule as Record<string, unknown>).deferPoiInstallUntilStyleReady;
    expect(deferInstall).toBeTypeOf("function");

    let styleReady = false;
    const install = vi.fn();
    const cancel = (deferInstall as (
      gate: { isStyleLoaded: () => boolean },
      apply: () => void,
    ) => () => void)({ isStyleLoaded: () => styleReady }, install);

    expect(install).not.toHaveBeenCalled();
    styleReady = true;
    await vi.advanceTimersByTimeAsync(20);
    expect(install).toHaveBeenCalledTimes(1);
    cancel();

    const source = readSource("src/components/map/UniversityPoiLayer.tsx");
    const lifecycle = source.slice(
      source.indexOf("// ── Mount source + layers"),
      source.indexOf("// ── Update data when the input list changes."),
    );
    expect(lifecycle).toContain("deferPoiInstallUntilStyleReady");
    expect(lifecycle).not.toContain('map.once("load", install)');
    expect(lifecycle).not.toContain("map.loaded()");
  });
});
