// Stage 7A — Theme & Heatmap Closing Patch
//
// These tests cover the regression set required by the directive:
//   * ThemeToggle hydration safety (stable SSR markup)
//   * Theme snapshot / store behaviour
//   * Dark mode contrast matrix (WCAG AA)
//   * MapLibre light/dark basemaps are genuinely different
//   * Calculator synthetic missing-cost branch
//   * Assessment + match copy boundary on region metrics

import { describe, expect, it } from "vitest";

import {
  DARK_BASEMAP_STYLE,
  DEFAULT_DARK_STYLE,
  DEFAULT_LIGHT_STYLE,
  LIGHT_BASEMAP_STYLE,
} from "@/components/map/MapCanvas";

import { THEME_INIT_SCRIPT } from "@/lib/theme";
import { tuitionRmbFromSummary } from "@/lib/legacy-mappers";

// ---------------------------------------------------------------------------
// 1. Theme hydration safety
// ---------------------------------------------------------------------------

describe("theme bootstrap script (THEME_INIT_SCRIPT)", () => {
  it("is a non-empty string of source code", () => {
    expect(typeof THEME_INIT_SCRIPT).toBe("string");
    expect(THEME_INIT_SCRIPT.length).toBeGreaterThan(40);
  });

  it("reads from localStorage key pathos:theme", () => {
    expect(THEME_INIT_SCRIPT).toContain("pathos:theme");
  });

  it("queries prefers-color-scheme media feature", () => {
    expect(THEME_INIT_SCRIPT).toContain("prefers-color-scheme: dark");
  });

  it("toggles the .dark class on <html>", () => {
    expect(THEME_INIT_SCRIPT).toContain('classList.toggle("dark"');
  });

  it("sets data-theme attribute for downstream observers", () => {
    expect(THEME_INIT_SCRIPT).toContain("dataset.theme");
  });

  it("is wrapped in try/catch so storage failures don't crash SSR", () => {
    expect(THEME_INIT_SCRIPT).toMatch(/try\s*\{/);
    expect(THEME_INIT_SCRIPT).toMatch(/catch/);
  });

  it("does not call any non-deterministic browser API beyond matchMedia", () => {
    // The bootstrap script must remain byte-stable; only localStorage,
    // matchMedia, and documentElement are touched.
    const banned = ["XMLHttpRequest", "fetch", "navigator", "Date"];
    for (const api of banned) {
      expect(THEME_INIT_SCRIPT.includes(api), `THEME_INIT_SCRIPT should not call ${api}`).toBe(false);
    }
  });
});

// ---------------------------------------------------------------------------
// 2. WCAG AA contrast matrix
// ---------------------------------------------------------------------------

// Mirror the WCAG 2.x relative-luminance formula used in the audit script.
function lum(rgb: readonly [number, number, number]): number {
  const chan = (c: number) => {
    const v = c / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  };
  const [r, g, b] = rgb;
  return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b);
}

function contrast(fg: readonly [number, number, number], bg: readonly [number, number, number]): number {
  const L1 = lum(fg);
  const L2 = lum(bg);
  const [hi, lo] = L1 >= L2 ? [L1, L2] : [L2, L1];
  return (hi + 0.05) / (lo + 0.05);
}

const LIGHT_TOKENS: Palette = {
  "surface-base":  [246, 243, 237],
  "surface-1":     [255, 250, 241],
  "surface-2":     [255, 255, 255],
  "text-primary":  [21, 32, 37],
  "text-secondary":[86, 96, 102],
  "text-muted":    [98, 108, 114],
  "border-soft":   [140, 130, 114],
  "border-strong": [130, 120, 102],
  cobalt:          [49, 93, 159],
  jade:            [35, 118, 107],
  persimmon:       [170, 78, 36],
  danger:          [180, 52, 52],
  focus:           [49, 93, 159],
};

const DARK_TOKENS: Palette = {
  "surface-base":  [24, 30, 36],
  "surface-1":     [36, 44, 52],
  "surface-2":     [48, 56, 64],
  "text-primary":  [244, 240, 232],
  "text-secondary":[190, 196, 202],
  "text-muted":    [162, 168, 174],
  "border-soft":   [110, 120, 128],
  "border-strong": [140, 150, 158],
  cobalt:          [132, 172, 224],
  jade:            [96, 196, 178],
  persimmon:       [240, 154, 110],
  danger:          [244, 130, 130],
  focus:           [132, 172, 224],
};

type Triple = readonly [number, number, number];
type Palette = Record<string, Triple>;
function runMatrix(name: string, palette: Palette) {
  describe(`contrast matrix (${name})`, () => {
    const textTargets = [
      ["surface-base", 4.5],
      ["surface-1", 4.5],
      ["surface-2", 4.5],
    ] as const;
    const borderTargets = [
      ["surface-base", 3.0],
      ["surface-1", 3.0],
    ] as const;

    const textFgs = ["text-primary", "text-secondary", "text-muted", "cobalt", "jade", "persimmon", "danger"] as const;
    for (const fg of textFgs) {
      for (const [bg, target] of textTargets) {
        it(`${fg} on ${bg} >= ${target}:1`, () => {
          const ratio = contrast(palette[fg], palette[bg]);
          if (ratio < target) {
            throw new Error(
              `FAIL ${name}: ${fg} ${JSON.stringify(palette[fg])} on ${bg} ${JSON.stringify(palette[bg])} = ${ratio.toFixed(2)} (need ${target})`,
            );
          }
          expect(ratio).toBeGreaterThanOrEqual(target);
        });
      }
    }

    const borderFgs = ["border-soft", "border-strong", "focus"] as const;
    for (const fg of borderFgs) {
      for (const [bg, target] of borderTargets) {
        it(`${fg} on ${bg} >= ${target}:1`, () => {
          const ratio = contrast(palette[fg], palette[bg]);
          if (ratio < target) {
            throw new Error(
              `FAIL ${name}: ${fg} ${JSON.stringify(palette[fg])} on ${bg} ${JSON.stringify(palette[bg])} = ${ratio.toFixed(2)} (need ${target})`,
            );
          }
          expect(ratio).toBeGreaterThanOrEqual(target);
        });
      }
    }
  });
}

runMatrix("light", LIGHT_TOKENS);
runMatrix("dark", DARK_TOKENS);

// ---------------------------------------------------------------------------
// 3. MapLibre light/dark basemaps are genuinely different
// ---------------------------------------------------------------------------

describe("MapLibre light/dark basemaps", () => {
  it("exported DEFAULT_LIGHT_STYLE and DEFAULT_DARK_STYLE are distinct objects", () => {
    expect(DEFAULT_LIGHT_STYLE).toBeDefined();
    expect(DEFAULT_DARK_STYLE).toBeDefined();
    expect(DEFAULT_LIGHT_STYLE).not.toBe(DEFAULT_DARK_STYLE);
  });

  it("light style references CARTO Voyager tiles", () => {
    const sources = JSON.stringify(LIGHT_BASEMAP_STYLE.sources);
    expect(sources).toContain("carto");
    expect(sources).toContain("voyager");
    expect(sources).not.toContain("dark_all");
  });

  it("dark style references CARTO Dark Matter tiles", () => {
    const sources = JSON.stringify(DARK_BASEMAP_STYLE.sources);
    expect(sources).toContain("carto");
    expect(sources).toContain("dark_all");
    expect(sources).not.toContain("voyager");
  });

  it("both styles have non-empty tile URL arrays (≥ 4 hosts)", () => {
    for (const style of [LIGHT_BASEMAP_STYLE, DARK_BASEMAP_STYLE]) {
      const src = Object.values(style.sources)[0] as { tiles: string[] };
      expect(src.tiles.length).toBeGreaterThanOrEqual(4);
    }
  });

  it("both styles carry OpenStreetMap + CARTO attribution", () => {
    for (const style of [LIGHT_BASEMAP_STYLE, DARK_BASEMAP_STYLE]) {
      const src = Object.values(style.sources)[0] as { attribution: string };
      expect(src.attribution).toContain("OpenStreetMap");
      expect(src.attribution).toContain("CARTO");
    }
  });

  it("both styles are valid MapLibre StyleSpecification shape", () => {
    for (const style of [LIGHT_BASEMAP_STYLE, DARK_BASEMAP_STYLE]) {
      expect(style.version).toBe(8);
      expect(Object.keys(style.sources).length).toBeGreaterThanOrEqual(1);
      expect(style.layers.length).toBeGreaterThanOrEqual(2);
    }
  });
});

// ---------------------------------------------------------------------------
// 4. Calculator synthetic missing-cost branch
// ---------------------------------------------------------------------------

describe("calculator: synthetic minimumUsd = null", () => {
  const baseSummary = {
    id: "test",
    name: "Test",
    chineseName: "测试",
    city: "Nowhere",
    state: "NA",
    stateFips: "00",
    rankingTier: "top50" as const,
    costSummary: { minimumUsd: null as number | null, maximumUsd: null as number | null },
  };

  it("tuitionRmbFromSummary returns null when minimumUsd is null", () => {
    expect(tuitionRmbFromSummary(baseSummary)).toBeNull();
  });

  it("tuitionRmbFromSummary returns null when minimumUsd is 0 (no fake ¥0)", () => {
    expect(
      tuitionRmbFromSummary({ ...baseSummary, costSummary: { minimumUsd: 0, maximumUsd: null } }),
    ).toBeNull();
  });

  it("tuitionRmbFromSummary returns null when minimumUsd is negative", () => {
    expect(
      tuitionRmbFromSummary({ ...baseSummary, costSummary: { minimumUsd: -1, maximumUsd: null } }),
    ).toBeNull();
  });

  it("tuitionRmbFromSummary returns null when minimumUsd is NaN/Infinity", () => {
    expect(
      tuitionRmbFromSummary({ ...baseSummary, costSummary: { minimumUsd: Number.NaN, maximumUsd: null } }),
    ).toBeNull();
    expect(
      tuitionRmbFromSummary({ ...baseSummary, costSummary: { minimumUsd: Number.POSITIVE_INFINITY, maximumUsd: null } }),
    ).toBeNull();
  });

  it("tuitionRmbFromSummary returns integer RMB when minimumUsd is a positive finite number", () => {
    const result = tuitionRmbFromSummary({ ...baseSummary, costSummary: { minimumUsd: 50000, maximumUsd: 60000 } });
    expect(typeof result).toBe("number");
    expect(result).toBe(360000); // 50000 * 7.2
  });
});

// ---------------------------------------------------------------------------
// 5. Assessment + match copy boundary
// ---------------------------------------------------------------------------
//
// Both /match and /assessment must surface the "region metrics are not
// part of the match score" notice. The match page has had the callout
// since Stage 7A v1; the assessment page must now match.
//
// We assert against the rendered React tree source to make sure the
// boundary statement lives in the page modules.

import * as fs from "node:fs";
import * as path from "node:path";

describe("region-metric boundary copy", () => {
  const root = path.resolve(process.cwd(), "src/app");

  it("/match includes the region-blocked callout", () => {
    const src = fs.readFileSync(path.join(root, "match/page.tsx"), "utf8");
    expect(src).toContain("区域指标");
    expect(src).toMatch(/安全.*就业.*华人社区/);
    expect(src).toMatch(/未.*(?:计入|进入).*分数/);
  });

  it("/assessment surfaces an explicit notice that region metrics do not affect scoring", () => {
    const src = fs.readFileSync(path.join(root, "assessment/page.tsx"), "utf8");
    expect(src).toContain("区域指标");
    expect(src).toMatch(/未.*(?:进入|计入).*(?:AI 评估|分数|评分)/);
  });

  it("/portfolio surfaces reach/target/safety structure (AI list analysis)", () => {
    const src = fs.readFileSync(path.join(root, "portfolio/page.tsx"), "utf8");
    expect(src).toMatch(/冲刺|匹配|保底/);
  });
});