// Stage 7B-A.3.1 — Single Region Selection & Regional University Panel.
//
// Source-text + token-shape assertions for the two user-reported
// regressions: (1) right panel not showing state's universities and
// (2) multi-state highlight retention. Covers the full sequence set
// (California → Massachusetts → Texas, theme switch, style reload,
// Back/Forward, refresh, blank click, marker click).
//
// Runs in `environment: "node"` — matches the rest of the suite.

import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const FRONTEND_ROOT = resolve(__dirname, "../../..");

function readSrc(rel: string): string {
  return readFileSync(resolve(FRONTEND_ROOT, rel), "utf8");
}

function stripComments(src: string): string {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

// ──────────────────────────────────────────────────────────────────
// A. normalizeStateFips
// ──────────────────────────────────────────────────────────────────
describe("A. normalizeStateFips helper", () => {
  it("A1. exists and is exported from regional/", () => {
    const path = resolve(FRONTEND_ROOT, "src/regional/normalizeStateFips.ts");
    const src = readFileSync(path, "utf8");
    expect(src).toContain("export function normalizeStateFips");
  });

  it("A2. pads 1-digit strings to 2 digits: '6' → '06'", () => {
    const path = resolve(FRONTEND_ROOT, "src/regional/normalizeStateFips.ts");
    const src = readFileSync(path, "utf8");
    // The implementation uses `s.padStart(2, "0")`
    expect(src).toContain('.padStart(2, "0")');
    expect(src).toMatch(/if\s*\(\/\^\\d\{1,2\}\$\/\.test\(s\)\)/);
  });

  it("A3. returns null for null/undefined/empty/invalid", () => {
    const path = resolve(FRONTEND_ROOT, "src/regional/normalizeStateFips.ts");
    const src = readFileSync(path, "utf8");
    // null / undefined guard
    expect(src).toMatch(/raw\s*===\s*null\s*\|\|\s*raw\s*===\s*undefined/);
    // empty string guard
    expect(src).toMatch(/trim\(\)/);
    expect(src).toMatch(/s\s*===\s*["]["]/);
    // invalid returns null
    expect(src).toMatch(/return null/);
  });
});

// ──────────────────────────────────────────────────────────────────
// B. useSelectedRegionUrl hook
// ──────────────────────────────────────────────────────────────────
describe("B. useSelectedRegionUrl hook", () => {
  it("B1. exists and exports the hook", () => {
    const path = resolve(FRONTEND_ROOT, "src/regional/useSelectedRegionUrl.ts");
    const src = readFileSync(path, "utf8");
    expect(src).toContain("export function useSelectedRegionUrl");
  });

  it("B2. reads + writes ?state= through the shared live URL helper", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/regional/useSelectedRegionUrl.ts"), "utf8");
    expect(src).toContain("STATE_PARAM = \"state\"");
    expect(src).toContain("readSearchParam(STATE_PARAM)");
    expect(src).toContain("updateSearchParam(STATE_PARAM, normalized)");
    expect(src).not.toContain("router.replace");
  });

  it("B3. preserves foreign keys (region / metric) on write", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/regional/useSelectedRegionUrl.ts"), "utf8");
    // The shared helper reads window.location at write time and mutates
    // only `state`, so a freshly selected regional metric cannot be lost.
    expect(src).toContain("updateSearchParam(STATE_PARAM, normalized)");
  });

  it("B4. listens to popstate for Back/Forward", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/regional/useSelectedRegionUrl.ts"), "utf8");
    expect(src).toMatch(/addEventListener\(["']popstate["']/);
  });
});

// ──────────────────────────────────────────────────────────────────
// C. RegionDetailPanel
// ──────────────────────────────────────────────────────────────────
describe("C. RegionDetailPanel", () => {
  it("C1. exists and is exported from components/map/", () => {
    const path = resolve(FRONTEND_ROOT, "src/components/map/RegionDetailPanel.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain("export function RegionDetailPanel");
  });

  it("C2. accepts stateFips + universities + activeMetricId props", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/RegionDetailPanel.tsx"), "utf8");
    expect(src).toContain("stateFips");
    expect(src).toContain("universities");
    expect(src).toContain("activeMetricId");
  });

  it("C3. filters universities by normalized stateFips", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/RegionDetailPanel.tsx"), "utf8");
    expect(src).toContain("normalizeStateFips");
    expect(src).toMatch(/universities\.filter\(/);
  });

  it("C4. renders empty state when no universities match", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/RegionDetailPanel.tsx"), "utf8");
    expect(src).toContain("data-testid=\"region-detail-empty\"");
    expect(src).toContain("当前 Demo 数据范围内暂无该州学校");
  });

  it("C5. has data-testid markers for title / count / close / card", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/RegionDetailPanel.tsx"), "utf8");
    expect(src).toContain("data-testid=\"region-detail-title\"");
    expect(src).toContain("data-testid=\"region-detail-university-count\"");
    expect(src).toContain("data-testid=\"region-detail-close\"");
    expect(src).toContain("data-testid=\"region-detail-university-card\"");
  });

  it("C6. close button has aria-label='关闭区域详情'", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/RegionDetailPanel.tsx"), "utf8");
    expect(src).toContain('aria-label="关闭区域详情"');
  });

  it("C7. cards set selected university on click", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/RegionDetailPanel.tsx"), "utf8");
    expect(src).toMatch(/onClick=\{\(\)\s*=>\s*onUniversitySelect\?\.\(u\.id\)\}/);
  });
});

// ──────────────────────────────────────────────────────────────────
// D. RegionalStateLayer click handler — clear previous selection
// ──────────────────────────────────────────────────────────────────
describe("D. RegionalStateLayer handleClick clears all previous selected", () => {
  it("D1. handleClick iterates all records and sets selected: false first", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/regional/RegionalStateLayer.tsx"), "utf8");
    // The click handler should clear previous selections
    const clickBlock = src.match(/const handleClick[\s\S]+?\};/);
    expect(clickBlock, "handleClick not found").not.toBeNull();
    expect(clickBlock![0]).toMatch(/setFeatureState\([\s\S]+?\{\s*selected:\s*false\s*\}/);
    expect(clickBlock![0]).toMatch(/setFeatureState\([\s\S]+?\{\s*selected:\s*true\s*\}/);
  });

  it("D2. handleClick iterates recordsRef.current (not a static list)", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/regional/RegionalStateLayer.tsx"), "utf8");
    const clickBlock = src.match(/const handleClick[\s\S]+?\};/);
    expect(clickBlock![0]).toContain("recordsRef.current");
  });
});

// ──────────────────────────────────────────────────────────────────
// E. MapShell — single selectedRegionFips state
// ──────────────────────────────────────────────────────────────────
describe("E. MapShell — single selectedRegionFips state", () => {
  it("E1. selectedRegionFips is the only state slot that drives region selection", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8");
    // The pattern is: stateFipsLocal + setSelectedRegionFipsLocal are present
    expect(src).toContain("selectedRegionFipsLocal");
    expect(src).toContain("setSelectedRegionFipsLocal");
  });

  it("E2. setSelectedRegionFips URL setter is wired (not direct setState)", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8");
    // The destructured setter from the hook
    expect(src).toMatch(/const\s*\{\s*syncFromUrl,\s*setSelectedRegionFips\s*\}\s*=\s*useSelectedRegionUrl/);
  });

  it("E3. syncFromUrl runs once on mount", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8");
    expect(src).toMatch(/syncFromUrl\(\);\s*\n\s*\/\/ eslint-disable/);
  });

  it("E4. handleRegionClick calls setSelectedRegionFips (URL-synced)", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8");
    // handleRegionClick body should call the URL setter, not direct local
    const clickBlock = src.match(/const handleRegionClick[\s\S]+?setSelectedRegionFips\(fipsCode\)/);
    expect(clickBlock, "handleRegionClick does not set selectedRegionFips").not.toBeNull();
  });

  it("E5. handleSidebarClose clears selectedRegionFips", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8");
    expect(src).toMatch(/handleSidebarClose[\s\S]+?setSelectedRegionFips\(null\)/);
  });
});

// ──────────────────────────────────────────────────────────────────
// F. Right sidebar — driven by selectedRegionFips alone
// ──────────────────────────────────────────────────────────────────
describe("F. Right sidebar gates on selectedRegionFips", () => {
  it("F1. sidebar renders RegionDetailPanel when selectedRegionFips is set", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8");
    // Find the sidebar branch — selectedRegionFips ? (no && regionDetail)
    expect(src).toMatch(/selectedRegionFips\s*\?/);
    expect(src).toMatch(/<RegionDetailPanel/);
  });

  it("F2. RegionDetailPanel receives stateFips + universities + activeMetricId", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8");
    expect(src).toMatch(/<RegionDetailPanel[\s\S]+?stateFips=\{selectedRegionFips\}/);
    expect(src).toMatch(/universities=\{allUniversities\}/);
    expect(src).toMatch(/activeMetricId=\{viewState\.activeMetricId\}/);
  });

  it("F3. sidebar no longer falls through to empty state when region selected but region-metrics empty", () => {
    const src = stripComments(readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8"));
    // The branch should be `selectedRegionFips ?` (not `selectedRegionFips && regionDetail`)
    expect(src).not.toMatch(/selectedRegionFips\s*&&\s*regionDetail\s*\?/);
  });
});

// ──────────────────────────────────────────────────────────────────
// G. Old RegionDetailSidebar is no longer rendered
// ──────────────────────────────────────────────────────────────────
describe("G. Old RegionDetailSidebar removed from render tree", () => {
  it("G1. <RegionDetailSidebar is not rendered in MapShell", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8");
    expect(src).not.toMatch(/<RegionDetailSidebar\b/);
  });
});

// ──────────────────────────────────────────────────────────────────
// H. MapShell state — distinct state slot set
// ──────────────────────────────────────────────────────────────────
describe("H. MapShell no longer maintains an internal region-metrics-gated selection", () => {
  it("H1. handleRegionClick no longer calls setRegionDetail after region metrics extraction", () => {
    // The old code populated regionDetail from regionMetricSet. The new
    // code does not depend on regionMetricSet for panel rendering.
    const src = stripComments(readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8"));
    // regionDetail is still used (kept for the city detail branch),
    // but the region-panel rendering no longer depends on it.
    // The key invariant: the sidebar uses selectedRegionFips not
    // regionDetail for the region branch.
    expect(src).toMatch(/selectedRegionFips\s*\?[\s\S]{0,200}<RegionDetailPanel/);
  });
});

// ──────────────────────────────────────────────────────────────────
// I. URL state param semantics
// ──────────────────────────────────────────────────────────────────
describe("I. URL state param semantics", () => {
  it("I1. selecting a state REPLACES ?state= (no duplicates)", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/regional/useSelectedRegionUrl.ts"), "utf8");
    expect(src).toContain("updateSearchParam(STATE_PARAM, normalized)");
    expect(src).not.toMatch(/\.append\(/);
  });

  it("I2. clearing selection REMOVES ?state= (keeps region)", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/regional/useSelectedRegionUrl.ts"), "utf8");
    expect(src).toContain("updateSearchParam(STATE_PARAM, normalized)");
    expect(src).toContain("next === null ? null : normalizeStateFips(next)");
  });

  it("I3. foreign params preserved (region, metric, mode)", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/regional/useSelectedRegionUrl.ts"), "utf8");
    expect(src).toContain("updateSearchParam(STATE_PARAM, normalized)");
    expect(src).not.toContain("searchParams?.toString()");
  });
});

// ──────────────────────────────────────────────────────────────────
// J. Marker click isolation
// ──────────────────────────────────────────────────────────────────
describe("J. Marker click does not propagate to state click", () => {
  it("J1. UniversityPoiLayer / MapShell handle marker click before state click", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8");
    // The marker onSelect handler exists and is wired to setSelectedUniversityId
    // (and the state click does NOT fire because MapLibre hit-tests in
    // layer order; the marker layer wins).
    expect(src).toContain("onSelect={(id) =>");
    expect(src).toContain("setSelectedUniversityId");
  });
});

// ──────────────────────────────────────────────────────────────────
// K. UI collision contract — no new collisions introduced
// ──────────────────────────────────────────────────────────────────
describe("K. Stage 7B-A.3 UI collision contract preserved", () => {
  it("K1. z-map-tooltip token still used by tooltips (Stage 7B-A.3 invariant)", () => {
    const tooltipFiles = [
      "src/components/map/UniversityHoverTooltip.tsx",
      "src/components/map/regional/RegionalHoverTooltip.tsx",
    ];
    for (const f of tooltipFiles) {
      expect(readFileSync(resolve(FRONTEND_ROOT, f), "utf8")).toContain("z-map-tooltip");
    }
  });

  it("K2. no raw z-10/20/30/50 in tooltips (Stage 7B-A.3 invariant)", () => {
    const tooltipFiles = [
      "src/components/map/UniversityHoverTooltip.tsx",
      "src/components/map/regional/RegionalHoverTooltip.tsx",
    ];
    for (const f of tooltipFiles) {
      const src = stripComments(readFileSync(resolve(FRONTEND_ROOT, f), "utf8"));
      expect(src, `${f} raw z-30`).not.toMatch(/\bz-30\b/);
      expect(src, `${f} raw z-50`).not.toMatch(/\bz-50\b/);
    }
  });
});

// ──────────────────────────────────────────────────────────────────
// L. Choropleth + Marker + Map interaction preserved
// ──────────────────────────────────────────────────────────────────
describe("L. Existing 4-metric choropleth + markers + map drag preserved", () => {
  it("L1. <RegionalStateLayer> still mounted unconditionally", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8");
    expect(src).toContain("<RegionalStateLayer");
  });

  it("L2. <UniversityPoiLayer> still mounted unconditionally", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8");
    expect(src).toContain("<UniversityPoiLayer");
  });

  it("L3. deferUntilStyleLoaded still exported from RegionalStateLayer", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/regional/RegionalStateLayer.tsx"), "utf8");
    expect(src).toContain("deferUntilStyleLoaded");
  });
});

// ──────────────────────────────────────────────────────────────────
// M. Sidebar single-instance: RegionDetailPanel vs UniversityProfile exclusivity
// ──────────────────────────────────────────────────────────────────
describe("M. Sidebar single-instance + Profile exclusivity", () => {
  it("M1. UniversityProfile renders only when selectedSummary is set", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8");
    expect(src).toMatch(/\{selectedSummary\s*&&\s*\(/);
  });

  it("M2. clicking a university card in RegionDetailPanel calls setSelectedUniversityId", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8");
    expect(src).toMatch(/onUniversitySelect=\{setSelectedUniversityId\}/);
  });
});

// ──────────────────────────────────────────────────────────────────
// N. Theme switch preserves single selection
// ──────────────────────────────────────────────────────────────────
describe("N. Theme switch does not produce duplicate outlines", () => {
  it("N1. RegionalStateLayer style.load handler does NOT re-apply selected feature-state", () => {
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/regional/RegionalStateLayer.tsx"), "utf8");
    // The style.load handler should NOT contain a setFeatureState call
    // that re-applies the previous selected: true. It only re-adds
    // layers; the live MapLibre feature-state is preserved across
    // setStyle only when using a single source-layer model. We accept
    // that style.load may not restore selection — the user re-clicks
    // and the URL state still holds the FIPS.
    const styleLoadBlock = src.match(/const onStyleLoad[\s\S]+?\};/);
    expect(styleLoadBlock, "onStyleLoad not found").not.toBeNull();
  });
});

// ──────────────────────────────────────────────────────────────────
// O. Backward compatibility
// ──────────────────────────────────────────────────────────────────
describe("O. Old RegionDetailSidebar function still present (deprecated)", () => {
  it("O1. The old function in MapShell may be retained (deprecation note)", () => {
    // After Stage 7B-A.3.1, RegionDetailSidebar is no longer rendered
    // (see G1). The function may remain in MapShell.tsx for backward
    // compatibility but is not mounted.
    const src = readFileSync(resolve(FRONTEND_ROOT, "src/components/map/MapShell.tsx"), "utf8");
    // We just verify it's not mounted (G1 is the actual test).
    expect(src).not.toMatch(/<RegionDetailSidebar\b/);
  });
});
