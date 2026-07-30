import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const FRONTEND_ROOT = resolve(__dirname, "../../..");

function readSource(relativePath: string): string {
  return readFileSync(resolve(FRONTEND_ROOT, relativePath), "utf8");
}

describe("public map state regressions", () => {
  it("preserves the live regional metric when selecting a state", () => {
    const source = readSource("src/regional/useSelectedRegionUrl.ts");
    const setter = source.slice(
      source.indexOf("const setSelectedRegionFips"),
      source.indexOf("// popstate:"),
    );

    expect(source).toMatch(/import\s*\{[^}]*updateSearchParam[^}]*\}\s*from\s*"@\/lib\/url-params"/);
    expect(setter).toContain("updateSearchParam(STATE_PARAM, normalized)");
    expect(setter).not.toContain("router.replace");
    expect(setter).not.toContain("searchParams?.toString()");
  });

  it("reinstalls university marker layers after a MapLibre style swap", () => {
    const source = readSource("src/components/map/UniversityPoiLayer.tsx");

    expect(source).toContain('map.on("style.load", onStyleLoad)');
    expect(source).toContain('map.off("style.load", onStyleLoad)');
    expect(source).toMatch(/const onStyleLoad\s*=\s*\(\)\s*=>\s*install\(\)/);
  });

  it("shows the selected regional metric in the state detail panel", () => {
    const panel = readSource("src/components/map/RegionDetailPanel.tsx");
    const shell = readSource("src/components/map/MapShell.tsx");

    expect(panel).toContain("activeRegionalMetric");
    expect(panel).toContain("getRegionalMetricDefinition(activeRegionalMetric)");
    expect(shell).toContain("activeRegionalMetric={activeRegionalMetric}");
  });

  it("updates an existing POI source without waiting for MapLibre load again", () => {
    const source = readSource("src/components/map/UniversityPoiLayer.tsx");
    const updateEffect = source.slice(
      source.indexOf("// ── Update data when the input list changes."),
      source.indexOf("// ── Apply selection / compare / saved highlight"),
    );

    expect(updateEffect).toContain("apply();");
    expect(updateEffect).not.toContain('map.once("load", apply)');
    expect(updateEffect).not.toContain("if (map.loaded()) apply()");
  });
});
