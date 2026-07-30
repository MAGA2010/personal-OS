// Stage 7B-A.1 — Regional heatmap control unification, rendering
// recovery, and map-toolbar collision fix. This suite pins the
// Stage 7B-A.1 invariants as pure-logic / source-text assertions so
// the regressions that produced the duplicate heatmap entry and
// the "select metric, map stays gray" bug cannot quietly come back.
//
// Coverage (≥27 cases as required by directive §十六):
//
//   A. URL param parsing & serialisation (5)
//   B. Allowed / forbidden regional metric set (5)
//   C. Z-index token system — uniqueness & ordering (4)
//   D. MapToolbar contract — data-testid / structure (3)
//   E. RegionalLayerControl options — cost is forbidden (4)
//   F. MapShell source invariants — legacy MetricTabs gone (3)
//   G. RegionalLegend visibility rule (3)
//
// The suite runs in `environment: "node"` — no DOM is required.
// All React component assertions are expressed as source-text
// scans and pure-function calls so they remain deterministic.

import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  REGIONAL_URL_PARAM,
  REGIONAL_VALID_VALUES,
  parseRegionParam,
  serialiseRegionParam,
} from "@/regional/useRegionalMetric";
import { REGIONAL_METRIC_IDS, type RegionalMetricId } from "@/regional/types";
import { MAP_Z, MAP_Z_CSS_VARS, buildMapZCssVars } from "@/components/map/map-zindex";
import { getRegionalMetricDefinition } from "@/regional/load";

const FRONTEND_ROOT = resolve(__dirname, "../../..");

function readSrc(rel: string): string {
  return readFileSync(resolve(FRONTEND_ROOT, rel), "utf8");
}

// ═══════════════════════════════════════════════════════════════════
// A. URL param parsing & serialisation
// ═══════════════════════════════════════════════════════════════════

describe("A. useRegionalMetric URL param parsing", () => {
  it("A1. null input → null metric (no heatmap)", () => {
    expect(parseRegionParam(null)).toBe(null);
  });

  it("A2. empty string → null metric", () => {
    expect(parseRegionParam("")).toBe(null);
  });

  it("A3. literal 'none' → null metric", () => {
    expect(parseRegionParam("none")).toBe(null);
  });

  it("A4. each valid RegionalMetricId round-trips", () => {
    for (const id of REGIONAL_METRIC_IDS) {
      expect(parseRegionParam(id)).toBe(id);
    }
  });

  it("A5. invalid string → null metric (no leakage)", () => {
    expect(parseRegionParam("not_a_metric")).toBe(null);
    expect(parseRegionParam("cost")).toBe(null); // cost is NOT regional
    expect(parseRegionParam("tuition")).toBe(null);
    expect(parseRegionParam("__proto__")).toBe(null);
  });

  it("A6. serialiseRegionParam mirrors the parser", () => {
    expect(serialiseRegionParam(null)).toBe("none");
    for (const id of REGIONAL_METRIC_IDS) {
      expect(serialiseRegionParam(id)).toBe(id);
      expect(parseRegionParam(serialiseRegionParam(id))).toBe(id);
    }
    expect(parseRegionParam(serialiseRegionParam(null))).toBe(null);
  });

  it("A7. URL_PARAM key is 'region'", () => {
    expect(REGIONAL_URL_PARAM).toBe("region");
  });
});

// ═══════════════════════════════════════════════════════════════════
// B. Allowed regional metric set
// ═══════════════════════════════════════════════════════════════════

describe("B. Regional metric allow-list", () => {
  it("B1. exactly 4 regional metrics", () => {
    expect(REGIONAL_METRIC_IDS).toHaveLength(4);
  });

  it("B2. the 4 metrics are the documented set", () => {
    expect([...REGIONAL_METRIC_IDS].sort()).toEqual(
      ["chinese_population", "employment", "income", "safety"].sort(),
    );
  });

  it("B3. 'cost' is NOT a regional metric", () => {
    expect(REGIONAL_METRIC_IDS).not.toContain("cost" as RegionalMetricId);
  });

  it("B4. REGIONAL_VALID_VALUES includes null + all metrics", () => {
    expect(REGIONAL_VALID_VALUES).toHaveLength(5);
    expect(REGIONAL_VALID_VALUES).toContain(null);
    for (const id of REGIONAL_METRIC_IDS) {
      expect(REGIONAL_VALID_VALUES).toContain(id);
    }
  });

  it("B5. each regional metric has a definition with a palette", () => {
    for (const id of REGIONAL_METRIC_IDS) {
      const def = getRegionalMetricDefinition(id);
      expect(def).toBeDefined();
      expect(def?.displayNameZh).toBeTruthy();
      expect(def?.paletteId).toBeTruthy();
    }
  });
});

// ═══════════════════════════════════════════════════════════════════
// C. Z-index token system
// ═══════════════════════════════════════════════════════════════════

describe("C. Map Z-Index Token System", () => {
  it("C1. every key in MAP_Z is also in MAP_Z_CSS_VARS", () => {
    for (const key of Object.keys(MAP_Z)) {
      expect(MAP_Z_CSS_VARS).toHaveProperty(key);
    }
    for (const key of Object.keys(MAP_Z_CSS_VARS)) {
      expect(MAP_Z).toHaveProperty(key);
    }
  });

  it("C2. CSS variable names use the --map-z- prefix", () => {
    for (const cssVar of Object.values(MAP_Z_CSS_VARS)) {
      expect(cssVar.startsWith("--map-z-")).toBe(true);
    }
  });

  it("C3. z-index values are strictly increasing and non-negative", () => {
    const entries = Object.entries(MAP_Z);
    for (let i = 1; i < entries.length; i++) {
      const prev = entries[i - 1][1];
      const cur = entries[i][1];
      expect(cur).toBeGreaterThan(prev);
      expect(prev).toBeGreaterThanOrEqual(0);
    }
  });

  it("C4. buildMapZCssVars emits one line per token, sorted by key", () => {
    const css = buildMapZCssVars();
    const lines = css.split("\n");
    expect(lines).toHaveLength(Object.keys(MAP_Z).length);
    expect(css).toContain("--map-z-toolbar: 22;");
    expect(css).toContain("--map-z-legend: 24;");
    expect(css).toContain("--map-z-modal: 50;");
  });
});

// ═══════════════════════════════════════════════════════════════════
// D. MapToolbar component contract
// ═══════════════════════════════════════════════════════════════════

describe("D. MapToolbar component contract", () => {
  it("D1. toolbar exposes a 'map-toolbar' data-testid", () => {
    const src = readSrc("src/components/map/MapToolbar.tsx");
    expect(src).toContain('data-testid="map-toolbar"');
  });

  it("D2. toolbar is a 'role=\"toolbar\"' with an aria-label", () => {
    const src = readSrc("src/components/map/MapToolbar.tsx");
    expect(src).toContain('role="toolbar"');
    expect(src).toContain('aria-label="地图工具栏"');
  });

  it("D3. toolbar uses z-map-toolbar utility, not a literal z- value", () => {
    const src = readSrc("src/components/map/MapToolbar.tsx");
    expect(src).toContain("z-map-toolbar");
    // No bare `z-NN` left in the toolbar file
    const literalZ = src.match(/\bz-\d{1,2}\b/);
    expect(literalZ).toBeNull();
  });

  it("D4. state selector uses z-map-control for its dropdown (≤ toolbar)", () => {
    const src = readSrc("src/components/map/MapToolbar.tsx");
    expect(src).toContain("z-map-control");
  });
});

// ═══════════════════════════════════════════════════════════════════
// E. RegionalLayerControl — option set is the documented 5 entries
// ═══════════════════════════════════════════════════════════════════

describe("E. RegionalLayerControl options", () => {
  it("E1. exposes a 'regional-layer-control' data-testid", () => {
    const src = readSrc("src/components/map/regional/RegionalLayerControl.tsx");
    expect(src).toContain('data-testid="regional-layer-control"');
    expect(src).toContain('data-testid="regional-layer-control-select"');
  });

  it("E2. includes the OFF option ('不显示区域热力图')", () => {
    const src = readSrc("src/components/map/regional/RegionalLayerControl.tsx");
    expect(src).toContain("不显示区域热力图");
  });

  it("E3. does NOT include 'cost' or '留学成本' as an option label", () => {
    const src = readSrc("src/components/map/regional/RegionalLayerControl.tsx");
    // cost is city-level only — it must not appear in the regional selector
    expect(src).not.toContain("留学成本");
    expect(src).not.toContain('"cost"');
  });

  it("E4. iterates over REGIONAL_METRIC_IDS so adding a regional metric updates the UI", () => {
    const src = readSrc("src/components/map/regional/RegionalLayerControl.tsx");
    expect(src).toContain("REGIONAL_METRIC_IDS");
  });
});

// ═══════════════════════════════════════════════════════════════════
// F. MapShell source invariants
// ═══════════════════════════════════════════════════════════════════

describe("F. MapShell source invariants", () => {
  it("F1. <MetricTabs .../> is no longer rendered in MapShell", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    // Strip comment blocks so the "REMOVED" documentation note doesn't
    // count as a live JSX invocation.
    const stripped = src
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/^\s*\/\/.*$/gm, "");
    expect(stripped).not.toMatch(/<MetricTabs\b/);
  });

  it("F2. the regional metric state comes from the new hook, not a local useState", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    expect(src).toContain("useRegionalMetric");
    expect(src).not.toContain("useState<RegionalMetricId | null>(null)");
    // Legacy variable name `activeRegionalLayer` should be gone.
    expect(src).not.toContain("activeRegionalLayer");
    expect(src).not.toContain("setActiveRegionalLayer");
  });

  it("F3. MapShell uses MapToolbar (unified), not a legacy inline toolbar", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    // Strip comments so the "Replaces the legacy right-3 top-3 z-10"
    // documentation note doesn't count as a live class string.
    const stripped = src
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/^\s*\/\/.*$/gm, "");
    expect(src).toContain("<MapToolbar");
    const inlineToolbar = stripped.match(/right-3 top-3 z-(?:10|20|30)/);
    expect(inlineToolbar).toBeNull();
  });

  it("F4. regional legend uses z-map-legend, desktop profile uses z-map-profile", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    expect(src).toContain("z-map-legend");
    expect(src).toContain("z-map-profile");
  });

  it("F5. showStateDropdown local state is removed (MapToolbar owns it)", () => {
    const src = readSrc("src/components/map/MapShell.tsx");
    expect(src).not.toContain("showStateDropdown");
    expect(src).not.toContain("setShowStateDropdown");
  });
});

// ═══════════════════════════════════════════════════════════════════
// G. RegionalLegend visibility rule
// ═══════════════════════════════════════════════════════════════════

describe("G. RegionalLegend visibility contract", () => {
  it("G1. exposes a 'regional-legend' data-testid", () => {
    const src = readSrc("src/components/map/regional/RegionalLegend.tsx");
    expect(src).toContain('data-testid="regional-legend"');
  });

  it("G2. returns null when activeMetricId is null (legend hidden when no heatmap)", () => {
    const src = readSrc("src/components/map/regional/RegionalLegend.tsx");
    expect(src).toContain("if (!def || !palette || activeMetricId === null) return null;");
  });

  it("G3. only one regional legend wrapper exists in the source", () => {
    const src = readSrc("src/components/map/regional/RegionalLegend.tsx");
    const matches = src.match(/data-testid="regional-legend"/g) ?? [];
    expect(matches).toHaveLength(1);
  });
});

// ═══════════════════════════════════════════════════════════════════
// Tailwind config — Z-index tokens declared
// ═══════════════════════════════════════════════════════════════════

describe("H. Tailwind z-index tokens", () => {
  it("H1. tailwind.config.ts declares map-* z-index tokens", () => {
    const src = readSrc("tailwind.config.ts");
    for (const key of [
      '"map-basemap"',
      '"map-region"',
      '"map-city"',
      '"map-marker"',
      '"map-hover"',
      '"map-control"',
      '"map-toolbar"',
      '"map-legend"',
      '"map-tooltip"',
      '"map-profile"',
      '"map-modal"',
    ]) {
      expect(src).toContain(key);
    }
  });
});
// ═══════════════════════════════════════════════════════════════════
// I. style.load lifecycle preservation (Stage 7B-A Final Closure)
// ═══════════════════════════════════════════════════════════════════

describe("I. style.load lifecycle preserved by Stage 7B-A.1", () => {
  it("I1. RegionalStateLayer still wraps addSource/addLayer in deferUntilStyleLoaded", () => {
    const src = readSrc("src/components/map/regional/RegionalStateLayer.tsx");
    expect(src).toContain("deferUntilStyleLoaded");
    const installDefers = src.match(/deferUntilStyleLoaded\(/g) ?? [];
    expect(installDefers.length).toBeGreaterThanOrEqual(2);
  });

  it("I2. RegionalStateLayer catches removeLayer on a missing layer (theme swap safety)", () => {
    const src = readSrc("src/components/map/regional/RegionalStateLayer.tsx");
    expect(src).toMatch(/removeLayer\([^)]+\);\s*\}\s*catch/);
  });

  it("I3. the MapToolbar refactor did not introduce maplibre / setStyle calls", () => {
    const src = readSrc("src/components/map/MapToolbar.tsx");
    expect(src).not.toContain("maplibre-gl");
    expect(src).not.toContain("setStyle(");
    expect(src).not.toContain("addSource(");
  });
});

// ═══════════════════════════════════════════════════════════════════
// J. Stage 7B-A checkpoint & data invariants
// ═══════════════════════════════════════════════════════════════════

describe("J. Stage 7B-A frozen data invariants", () => {
  it("J1. the repository-local Preview manifest exists", () => {
    const path = require("node:path");
    const manifest = path.resolve(FRONTEND_ROOT, "data/preview/manifest.json");
    const fs = require("node:fs");
    expect(fs.existsSync(manifest)).toBe(true);
  });

  it("J2. the regional validation totals match the data invariant contract", () => {
    const fs = require("node:fs");
    const path = require("node:path");
    const v = JSON.parse(
      fs.readFileSync(
        path.resolve(FRONTEND_ROOT, "generated/regional-data/regional-data-validation.json"),
        "utf8",
      ),
    );
    expect(v.summary.recordsTotal).toBe(204);
    expect(v.summary.recordsVerified).toBe(204);
    expect(v.summary.readyMetricCount).toBe(4);
    expect(v.summary.duplicateGeoIds).toBe(0);
    expect(v.summary.missingCount).toBe(0);
    // 51 jurisdictions (states + DC) per metric
    for (const d of v.distribution) {
      expect(d.count).toBe(51);
      expect(d.missingCount).toBe(0);
    }
  });

  it("J3. cost is recorded as out-of-scope (not a regional metric)", () => {
    const fs = require("node:fs");
    const path = require("node:path");
    const v = JSON.parse(
      fs.readFileSync(
        path.resolve(FRONTEND_ROOT, "generated/regional-data/regional-data-validation.json"),
        "utf8",
      ),
    );
    expect(v.outOfScopeMetrics).toContain("cost");
  });

  it("J4. Baidu runtime is still BLOCKED — default Provider is MapLibre", () => {
    // The Stage 7B-A Map Provider abstraction (in
    // src/components/map/providers/baidu/*) is preserved by the
    // external freeze checkpoint — touching those files is outside
    // Stage 7B-A.1's scope. The invariant for this patch is narrower:
    // the files Stage 7B-A.1 created or modified must NOT pull in
    // Baidu runtime code.
    const stage7ba1Files = [
      "src/components/map/MapToolbar.tsx",
      "src/components/map/map-zindex.ts",
      "src/regional/useRegionalMetric.ts",
      "tailwind.config.ts",
    ];
    const banned = ["BMapGL", "@baidu", "bmaps"];
    for (const rel of stage7ba1Files) {
      const src = readSrc(rel);
      for (const bannedName of banned) {
        expect(src, `${rel} contains ${bannedName}`).not.toContain(bannedName);
      }
    }
  });

  it("J5. MapCanvas still imports from maplibre-gl, not baidu", () => {
    const src = readSrc("src/components/map/MapCanvas.tsx");
    expect(src).toContain("import maplibregl from \"maplibre-gl\";");
    expect(src).not.toContain("BMapGL");
    expect(src).not.toContain("@baidu");
  });
});
