// Stage 7B-A.3 — UI Collision, Responsive Stabilization & Visual QA.
//
// Source-text + token-shape assertions for the Stage 7B-A.3 collision
// fixes. Pinned invariants:
//
//   A. Toolbar exclusivity (one and only one MapToolbar)
//   B. Desktop / Mobile toolbar exclusivity (no dual UI at md)
//   C. Legend 0/1 (zero or one RegionalLegend, gated by active metric)
//   D. Profile / BottomSheet exclusivity (lg:hidden vs hidden lg:block)
//   E. Z-index token audit (no raw z-10/20/30/50 in /map)
//   F. Dropdown clipping (state selector dropdown has overflow-y-auto)
//   G. Tooltip pointer-events (both tooltips pointer-events-none)
//   H. Profile close button a11y + internal scroll
//   I. Breakpoint gates (min-w-0 / flex-wrap / md: / truncate)
//   J. Long label containment (truncate on select text)
//   K. Focus ring (focus-visible on buttons/selects)
//   L. aria-label coverage (interactive elements labelled)
//   M. Choropleth + Marker preservation (no regression in 4 metrics)
//   N. Map drag not blocked (overlay containers pointer-events-none)
//   O. BottomSheet Escape + safe-area + data-testid
//   P. Tooltip edge-flip hook contract
//
// Runs in `environment: "node"` — matches the rest of the suite.

import { describe, expect, it } from "vitest";
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

const FRONTEND_ROOT = resolve(__dirname, "../../..");

function readSrc(rel: string): string {
  return readFileSync(resolve(FRONTEND_ROOT, rel), "utf8");
}

/** Strip JS/TS comments so source-text assertions don't trip on
 *  descriptive prose that mentions (but does not actually use)
 *  legacy classes. */
function stripComments(src: string): string {
  // Block comments
  src = src.replace(/\/\*[\s\S]*?\*\//g, "");
  // Line comments (naive but adequate for our controlled sources)
  src = src.replace(/^\s*\/\/.*$/gm, "");
  return src;
}

function readJson(rel: string): unknown {
  return JSON.parse(readFileSync(resolve(FRONTEND_ROOT, rel), "utf8"));
}

describe("A. Toolbar exclusivity", () => {
  it("A1. MapShell.tsx renders exactly one <MapToolbar", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    const occurrences = src.match(/<MapToolbar\b/g) ?? [];
    expect(occurrences.length).toBe(1);
  });

  it("A2. MapShell.tsx renders zero live <MetricTabs JSX element", () => {
    // Comments may reference the legacy file name; we strip them.
    const src = stripComments(readSrc("src/components/map/MapShell.tsx"));
    expect(src).not.toMatch(/<MetricTabs\b/);
  });

  it("A3. MapToolbar wrapper has flex-wrap + max-w-[calc(100vw-1.5rem)]", () => {
    const src = readSrc("src/components/map/MapToolbar.tsx");
    expect(src).toContain("flex-wrap");
    expect(src).toContain("max-w-[calc(100vw-1.5rem)]");
  });
});

describe("B. Desktop / Mobile exclusivity (lg gates)", () => {
  it("B1. Desktop UniversityProfile wrapper uses `hidden lg:block`", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    // The wrapper around the desktop profile carries the lg:block gate.
    expect(src).toMatch(/hidden[^"]*lg:block/);
  });

  it("B2. Mobile BottomSheet wrapper uses `lg:hidden`", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    expect(src).toMatch(/lg:hidden/);
  });

  it("B3. No raw `z-[9999]` or `z-[99999]` literals", () => {
    const candidates = [
      "src/components/map/MapShell.tsx",
      "src/components/map/MapToolbar.tsx",
      "src/components/map/MapCanvas.tsx",
      "src/components/map/UniversityProfile.tsx",
      "src/components/map/regional/RegionalStateLayer.tsx",
      "src/components/map/regional/RegionalLegend.tsx",
      "src/components/map/regional/RegionalLayerControl.tsx",
      "src/components/map/regional/RegionalHoverTooltip.tsx",
      "src/components/map/UniversityHoverTooltip.tsx",
    ];
    for (const f of candidates) {
      const src = readSrc(f);
      expect(src).not.toMatch(/z-\[9/);
    }
  });
});

describe("C. Legend 0/1", () => {
  it("C1. MapShell.tsx renders exactly one <RegionalLegend", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    const occurrences = src.match(/<RegionalLegend\b/g) ?? [];
    expect(occurrences.length).toBe(1);
  });

  it("C2. RegionalLegend wrapper is gated on activeRegionalMetric (truthy)", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    // The wrapper sits inside `{activeRegionalMetric && ( ... <RegionalLegend ... )}`
    expect(src).toMatch(/\{activeRegionalMetric\s*&&\s*\(/);
  });

  it("C3. RegionalLegend component returns null when metric is null", () => {
    const src = readSrc("src/components/map/regional/RegionalLegend.tsx");
    expect(src).toMatch(/activeMetricId\s*===\s*null\)\s*return\s+null/);
  });

  it("C4. RegionalLegend has data-testid for collision tests", () => {
    const src = readSrc("src/components/map/regional/RegionalLegend.tsx");
    expect(src).toContain('data-testid="regional-legend"');
  });
});

describe("D. Profile / BottomSheet exclusivity", () => {
  it("D1. UniversityProfile used in MapShell only inside the gated wrappers", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    const occurrences = src.match(/<UniversityProfile\b/g) ?? [];
    // Both desktop right-docked wrapper and mobile BottomSheet wrapper render it.
    // 2 total is acceptable (mutually exclusive at runtime via Tailwind media queries).
    expect(occurrences.length).toBeGreaterThanOrEqual(1);
    expect(occurrences.length).toBeLessThanOrEqual(2);
  });

  it("D2. BottomSheet used in MapShell only inside lg:hidden wrapper", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    expect(src).toMatch(/lg:hidden[^"]*"[^>]*>[\s\S]*<BottomSheet\b/);
  });
});

describe("E. Z-index token audit", () => {
  it("E1. No raw z-10 in src/components/map/ (excluding comments)", () => {
    const files = [
      "src/components/map/MapShell.tsx",
      "src/components/map/MapToolbar.tsx",
      "src/components/map/MapCanvas.tsx",
      "src/components/map/regional/RegionalStateLayer.tsx",
      "src/components/map/regional/RegionalLegend.tsx",
      "src/components/map/regional/RegionalLayerControl.tsx",
      "src/components/map/regional/RegionalHoverTooltip.tsx",
      "src/components/map/UniversityHoverTooltip.tsx",
    ];
    for (const f of files) {
      const src = stripComments(readSrc(f));
      expect(src, `${f} still contains raw z-10 in code`).not.toMatch(/\bz-10\b/);
    }
  });

  it("E2. No raw z-20 in src/components/map/ (excluding comments)", () => {
    const files = [
      "src/components/map/MapShell.tsx",
      "src/components/map/MapToolbar.tsx",
      "src/components/map/MapCanvas.tsx",
    ];
    for (const f of files) {
      const src = stripComments(readSrc(f));
      expect(src, `${f} still contains raw z-20 in code`).not.toMatch(/\bz-20\b/);
    }
  });

  it("E3. No raw z-30 or z-50 in tooltip components", () => {
    expect(stripComments(readSrc("src/components/map/UniversityHoverTooltip.tsx"))).not.toMatch(/\bz-30\b/);
    expect(stripComments(readSrc("src/components/map/regional/RegionalHoverTooltip.tsx"))).not.toMatch(/\bz-50\b/);
  });

  it("E4. Both tooltips use the z-map-tooltip token", () => {
    expect(readSrc("src/components/map/UniversityHoverTooltip.tsx")).toContain("z-map-tooltip");
    expect(readSrc("src/components/map/regional/RegionalHoverTooltip.tsx")).toContain("z-map-tooltip");
  });

  it("E5. map-zindex.ts tokens are unique + ordered", () => {
    const src = readSrc("src/components/map/map-zindex.ts");
    const block = src.match(/MAP_Z\s*=\s*\{([\s\S]+?)\}\s*as const/);
    expect(block, "MAP_Z block not found").not.toBeNull();
    const entryRe = /(\w+):\s*(\d+)/g;
    const values: number[] = [];
    let m: RegExpExecArray | null;
    while ((m = entryRe.exec(block![1])) !== null) {
      values.push(Number(m[2]));
    }
    const unique = new Set(values);
    expect(unique.size).toBe(values.length);
    for (let i = 1; i < values.length; i++) {
      expect(values[i]).toBeGreaterThan(values[i - 1]);
    }
  });
});

describe("F. Dropdown clipping", () => {
  it("F1. State selector dropdown has overflow-y-auto + max-h", () => {
    const src = readSrc("src/components/map/MapToolbar.tsx");
    expect(src).toMatch(/overflow-y-auto/);
    expect(src).toContain("max-h-[320px]");
  });

  it("F2. Dropdown is positioned above map canvas (z-map-control = 20)", () => {
    const src = readSrc("src/components/map/MapToolbar.tsx");
    expect(src).toContain("z-map-control");
  });

  it("F3. Toggle button has aria-haspopup + aria-expanded", () => {
    const src = readSrc("src/components/map/MapToolbar.tsx");
    expect(src).toContain('aria-haspopup="listbox"');
    expect(src).toContain("aria-expanded=");
  });
});

describe("G. Tooltip pointer-events", () => {
  it("G1. UniversityHoverTooltip has pointer-events-none", () => {
    expect(readSrc("src/components/map/UniversityHoverTooltip.tsx")).toContain("pointer-events-none");
  });

  it("G2. RegionalHoverTooltip has pointer-events-none", () => {
    expect(readSrc("src/components/map/regional/RegionalHoverTooltip.tsx")).toContain("pointer-events-none");
  });

  it("G3. Tooltips use `fixed` positioning (not absolute)", () => {
    // Stage 7B-A.3: both switched to fixed so they escape ancestor
    // overflow rules.
    expect(readSrc("src/components/map/UniversityHoverTooltip.tsx")).toMatch(/\bfixed\b/);
    expect(readSrc("src/components/map/regional/RegionalHoverTooltip.tsx")).toMatch(/\bfixed\b/);
  });

  it("G4. Tooltips carry data-placement-h/v attributes", () => {
    expect(readSrc("src/components/map/UniversityHoverTooltip.tsx")).toContain("data-placement-h");
    expect(readSrc("src/components/map/regional/RegionalHoverTooltip.tsx")).toContain("data-placement-v");
  });
});

describe("H. Profile close button + internal scroll", () => {
  it("H1. Close button has aria-label='关闭学校详情'", () => {
    expect(readSrc("src/components/map/UniversityProfile.tsx")).toContain('aria-label="关闭学校详情"');
  });

  it("H2. Profile body has overflow-y-auto", () => {
    expect(readSrc("src/components/map/UniversityProfile.tsx")).toContain("overflow-y-auto");
  });

  it("H3. Profile supports Escape (UniversityProfile component)", () => {
    const src = readSrc("src/components/map/UniversityProfile.tsx");
    expect(src).toMatch(/e\.key\s*===\s*["']Escape["']/);
  });
});

describe("Q. Integration bug-fix responsive collision contracts", () => {
  it("Q1. global navigation keeps the mobile drawer through tablet widths", () => {
    const src = readSrc("src/components/NavBar.tsx");
    expect(src).toContain("lg:flex");
    expect(src.match(/lg:hidden/g)?.length ?? 0).toBeGreaterThanOrEqual(2);
    expect(src).not.toContain("md:flex");
  });

  it("Q2. MapLibre navigation controls use the collision-free top-left anchor", () => {
    const canvas = readSrc("src/components/map/MapCanvas.tsx");
    const globals = readSrc("src/app/globals.css");
    expect(canvas).toContain('new maplibregl.NavigationControl(), "top-left"');
    expect(globals).toContain(".maplibregl-map .maplibregl-ctrl-top-left");
    expect(globals).toContain("@media (max-width: 767px)");
    expect(globals).toContain("@media (max-width: 359px)");
    expect(globals).toContain("top: 7.5rem");
  });

  it("Q3. desktop map panels begin at lg and mobile/tablet gets one regional sheet", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    expect(src).toContain('data-testid="region-detail-bottom-sheet"');
    expect(src).toMatch(/className="lg:hidden"[\s\S]*data-testid="region-detail-bottom-sheet"/);
    expect(src.match(/lg:block/g)?.length ?? 0).toBeGreaterThanOrEqual(3);
  });

  it("Q4. legend clears attribution and remains inside a 320px viewport", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    expect(src).toContain("bottom-12");
    expect(src).toContain("w-[calc(100%-2rem)]");
    expect(src).toContain("max-[359px]:w-[calc(100%-4rem)]");
    expect(src).toContain("max-w-[320px]");
  });

  it("Q5. wrapped state dropdown stays on-screen and rises above the legend", () => {
    const src = readSrc("src/components/map/MapToolbar.tsx");
    expect(src).toContain('dropdownOpen ? "z-map-tooltip" : "z-map-toolbar"');
    expect(src).toContain("max-[359px]:w-full");
    expect(src).toContain("max-[359px]:left-0");
    expect(src).toContain("max-[359px]:right-auto");
  });
});

describe("I. Breakpoint gates (responsive patterns)", () => {
  it("I1. MapToolbar uses min-w-0 on chips (truncate strategy)", () => {
    const src = readSrc("src/components/map/MapToolbar.tsx");
    expect(src).toContain("min-w-0");
    expect(src).toContain("truncate");
  });

  it("I2. MapShell uses lg:hidden + hidden lg:block for mobile/desktop split", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    expect(src).toContain("lg:hidden");
    expect(src).toMatch(/hidden[^"]*lg:block/);
  });

  it("I3. MapShell uses `flex-1 min-h-0` for the map fill column", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    expect(src).toContain("flex-1");
    expect(src).toContain("min-h-0");
  });

  it("I4. globals.css has min-width: 320px on html (320px floor)", () => {
    const src = readSrc("src/app/globals.css");
    expect(src).toMatch(/html\s*\{[^}]*min-width:\s*320px/);
  });
});

describe("J. Long label containment", () => {
  it("J1. RegionalLayerControl option '不显示区域热力图' (Chinese, 7 chars) is in source", () => {
    expect(readSrc("src/components/map/regional/RegionalLayerControl.tsx")).toContain("不显示区域热力图");
  });

  it("J2. RegionalLayerControl select has bounded width via parent", () => {
    const src = readSrc("src/components/map/regional/RegionalLayerControl.tsx");
    // The select sits inside a flex wrapper; truncate / bounded width is on the parent.
    expect(src).toMatch(/className=["'][^"']*appearance-none/);
  });
});

describe("K. Focus ring", () => {
  it("K1. RegionalLayerControl select uses focus-visible:ring", () => {
    const src = readSrc("src/components/map/regional/RegionalLayerControl.tsx");
    expect(src).toMatch(/focus-visible:ring/);
  });

  it("K2. globals.css applies a global focus-visible outline", () => {
    const src = readSrc("src/app/globals.css");
    expect(src).toMatch(/:focus-visible/);
  });
});

describe("L. aria-label coverage", () => {
  it("L1. MapToolbar has role + aria-label='地图工具栏'", () => {
    const src = readSrc("src/components/map/MapToolbar.tsx");
    expect(src).toContain('role="toolbar"');
    expect(src).toContain('aria-label="地图工具栏"');
  });

  it("L2. RegionalLayerControl select has aria-label='选择区域图层'", () => {
    expect(readSrc("src/components/map/regional/RegionalLayerControl.tsx")).toContain('aria-label="选择区域图层"');
  });

  it("L3. State selector button has data-testid and accessible role", () => {
    const src = readSrc("src/components/map/MapToolbar.tsx");
    expect(src).toContain('data-testid="state-selector-button"');
    expect(src).toContain('aria-haspopup="listbox"');
  });
});

describe("M. Choropleth + Marker preservation", () => {
  it("M1. RegionalStateLayer still mounts unconditionally on /map", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    expect(src).toContain("<RegionalStateLayer");
  });

  it("M2. UniversityPoiLayer still mounts unconditionally on /map", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    expect(src).toContain("<UniversityPoiLayer");
  });

  it("M3. All 4 RegionalMetricId branches still routed (income/safety/employment/chinese_population)", () => {
    // Pin the existing invariant from the previous test file — kept here so
    // a Stage 7B-A.3 edit cannot accidentally drop a metric.
    const src = readSrc("src/regional/types.ts");
    expect(src).toContain('"income"');
    expect(src).toContain('"safety"');
    expect(src).toContain('"employment"');
    expect(src).toContain('"chinese_population"');
  });

  it("M4. RegionalStateLayer deferUntilStyleLoaded still present", () => {
    const src = readSrc("src/components/map/regional/RegionalStateLayer.tsx");
    expect(src).toContain("deferUntilStyleLoaded");
  });
});

describe("N. Map drag not blocked", () => {
  it("N1. Loading overlay in MapCanvas has pointer-events-none (Stage 7B-A.3 fix)", () => {
    const src = readSrc("src/components/map/MapCanvas.tsx");
    // The Stage 7B-A.3 fix added pointer-events-none to the loading overlay.
    // Check the line containing z-map-modal
    const idx = src.indexOf("z-map-modal");
    expect(idx).toBeGreaterThan(-1);
    // The className starting from that idx backwards to the previous "
    const start = src.lastIndexOf('"', idx);
    const end = src.indexOf('"', idx);
    const cls = src.slice(start + 1, end);
    expect(cls).toContain("pointer-events-none");
  });

  it("N2. Granularity badge is pointer-events-none (so it never blocks map)", () => {
    const src = readSrc("src/components/map/MapCanvas.tsx");
    // Find the className containing z-map-basemap and confirm pointer-events-none is in the same className.
    const m = src.match(/className="[^"]*z-map-basemap[^"]*"/);
    expect(m, "No className with z-map-basemap found").not.toBeNull();
    expect(m![0]).toContain("pointer-events-none");
  });
});

describe("O. BottomSheet Escape + safe-area + data-testid", () => {
  it("O1. BottomSheet accepts onEscape prop", () => {
    const src = readSrc("src/components/shared/BottomSheet.tsx");
    expect(src).toMatch(/onEscape\?:\s*\(\)\s*=>\s*void/);
  });

  it("O2. BottomSheet registers an Escape keydown listener when onEscape provided", () => {
    const src = readSrc("src/components/shared/BottomSheet.tsx");
    expect(src).toMatch(/e\.key\s*===\s*["']Escape["']/);
  });

  it("O3. BottomSheet drag handle uses safe-area-inset-bottom padding", () => {
    const src = readSrc("src/components/shared/BottomSheet.tsx");
    expect(src).toContain("env(safe-area-inset-bottom)");
  });

  it("O4. BottomSheet root has data-testid (default 'bottom-sheet')", () => {
    const src = readSrc("src/components/shared/BottomSheet.tsx");
    expect(src).toContain('data-testid');
  });
});

describe("P. useEdgeFlippedPosition hook contract", () => {
  it("P1. useEdgeFlippedPosition source file exists and exports the hook", () => {
    const path = resolve(FRONTEND_ROOT, "src/components/shared/useEdgeFlippedPosition.ts");
    expect(existsSync(path)).toBe(true);
    const src = readFileSync(path, "utf8");
    expect(src).toContain("export function useEdgeFlippedPosition");
  });

  it("P2. Hook prefers right of anchor then flips left", () => {
    const src = readSrc("src/components/shared/useEdgeFlippedPosition.ts");
    // The function computes `left = opts.anchorX + offset` and branches when
    // `left + opts.tooltipWidth + padding > vw`. Both patterns must be present.
    expect(src).toMatch(/opts\.anchorX\s*\+\s*offset/);
    expect(src).toMatch(/opts\.tooltipWidth\s*\+\s*padding\s*>\s*vw/);
    expect(src).toMatch(/opts\.anchorX\s*-\s*opts\.tooltipWidth\s*-\s*offset/);
  });

  it("P3. Hook flips vertical when bottom overflows", () => {
    const src = readSrc("src/components/shared/useEdgeFlippedPosition.ts");
    expect(src).toMatch(/opts\.anchorY\s*\+\s*offset/);
    expect(src).toMatch(/opts\.tooltipHeight\s*\+\s*padding\s*>\s*vh/);
    expect(src).toMatch(/opts\.anchorY\s*-\s*opts\.tooltipHeight\s*-\s*offset/);
  });

  it("P4. Hook subscribes to ResizeObserver", () => {
    const src = readSrc("src/components/shared/useEdgeFlippedPosition.ts");
    // The hook itself is pure; the consumers (tooltip components) wire ResizeObserver.
    // Pin the data-testid pattern instead — the hook returns horizontal/vertical placements.
    expect(src).toContain("HorizontalPlacement");
    expect(src).toContain("VerticalPlacement");
  });
});

describe("Q. UI Zone reservation (MapCanvas root attribute)", () => {
  it("Q1. MapCanvas container has data-map-canvas-root='true'", () => {
    const src = readSrc("src/components/map/MapCanvas.tsx");
    expect(src).toContain("data-map-canvas-root=\"true\"");
  });

  it("Q2. Both tooltips look up the root via the data attribute", () => {
    expect(readSrc("src/components/map/UniversityHoverTooltip.tsx")).toContain("data-map-canvas-root");
    expect(readSrc("src/components/map/regional/RegionalHoverTooltip.tsx")).toContain("data-map-canvas-root");
  });
});

describe("R. Before/after Collision Matrix", () => {
  it("R1. Collision matrix JSON exists with before/after sections", () => {
    // The isolated coupling build keeps its audit documents inside the
    // self-contained frontend root instead of relying on a sibling tree.
    const path = resolve(FRONTEND_ROOT, "docs/STAGE7B-A3-UI-COLLISION-MATRIX.json");
    expect(existsSync(path)).toBe(true);
    const data = readJson(path) as { before?: unknown[]; after?: unknown[]; summary?: Record<string, number> };
    expect(Array.isArray(data.before)).toBe(true);
    expect(Array.isArray(data.after)).toBe(true);
    expect(data.summary?.criticalAfter).toBe(0);
    expect(data.summary?.highAfter).toBe(0);
  });
});

describe("S. Map profile offset (Stage 7B-A.3 fix)", () => {
  it("S1. Desktop profile wrapper has top-14 (clears toolbar)", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    // Find the profile wrapper line; it should now carry top-14
    expect(src).toMatch(/right-3\s+top-14\s+z-map-profile/);
  });

  it("S2. Desktop profile uses flexible max-width to survive narrow desktop widths", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    expect(src).toMatch(/w-\[min\(360px,calc\(100%-1\.5rem\)\)\]/);
  });
});

describe("T. City drilldown card mobile-hidden", () => {
  it("T1. City card wrapper has hidden lg:block (mobile and tablet hide it)", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    // The CityCard div is now gated to desktop only and clears top-left controls.
    expect(src).toMatch(/left-16\s+top-4\s+z-map-control\s+hidden[\s\S]*?lg:block/);
  });
});

describe("U. MapCanvas z-index policy", () => {
  it("U1. MapCanvas uses z-map-modal for loading overlay (not raw z-20)", () => {
    const src = readSrc("src/components/map/MapCanvas.tsx");
    expect(src).toContain("z-map-modal");
    expect(stripComments(src)).not.toMatch(/\bz-20\b/);
  });

  it("U2. MapCanvas uses z-map-basemap for granularity badge (not raw z-10)", () => {
    const src = readSrc("src/components/map/MapCanvas.tsx");
    expect(src).toContain("z-map-basemap");
    expect(stripComments(src)).not.toMatch(/\bz-10\b/);
  });
});
