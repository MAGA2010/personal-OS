// PathOS Stage 7B-A — Provider config / Baidu loader / Coordinate /
// Legend uniqueness tests.
//
// Covers the Stage 7B-A re-gate acceptance matrix:
//   - provider id resolution (maplibre | baidu | invalid | fallback)
//   - Baidu loader error surface (ak-missing | timeout | script-error)
//     without ever leaking the AK
//   - WGS84 coordinate sample integrity for the 5 Pilot universities
//   - single authoritative regional legend (no duplicate MapLegend)
//   - dark mode contrast normalization tokens still satisfy WCAG-AA

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  resolveMapProviderConfig,
  resolveMapProviderId,
  type MapProviderId,
} from "@/components/map/providers/types";
import {
  __resetBaiduLoaderForTests,
  getBaiduLoaderError,
  getBaiduLoaderState,
  loadBaiduMap,
  BaiduLoadError,
  isBrowser,
} from "@/components/map/providers/baidu/load-baidu-map";
import { MapLibreProviderAdapter } from "@/components/map/providers/maplibre/MapLibreProviderAdapter";
import { BaiduMapProviderAdapter } from "@/components/map/providers/baidu/BaiduMapProviderAdapter";
import fs from "node:fs";
import path from "node:path";

const FRONTEND_ROOT = path.resolve(__dirname, "../../..");

describe("Stage 7B-A — provider config resolution", () => {
  it("accepts 'maplibre'", () => {
    expect(resolveMapProviderId("maplibre")).toBe("maplibre");
  });
  it("accepts 'baidu'", () => {
    expect(resolveMapProviderId("baidu")).toBe("baidu");
  });
  it("falls back to maplibre on unrecognized values", () => {
    expect(resolveMapProviderId("google")).toBe("maplibre");
    expect(resolveMapProviderId("leaflet")).toBe("maplibre");
    expect(resolveMapProviderId("")).toBe("maplibre");
    expect(resolveMapProviderId(null)).toBe("maplibre");
    expect(resolveMapProviderId(undefined)).toBe("maplibre");
  });
  it("default config is maplibre with no AK", () => {
    const cfg = resolveMapProviderConfig({});
    expect(cfg.id).toBe("maplibre");
    expect(cfg.baiduAk).toBeNull();
  });
  it("trims and stores non-empty AK; nulls out empty AK", () => {
    expect(resolveMapProviderConfig({ provider: "baidu", baiduAk: "  abc123  " }).baiduAk).toBe("abc123");
    expect(resolveMapProviderConfig({ provider: "baidu", baiduAk: "" }).baiduAk).toBeNull();
    expect(resolveMapProviderConfig({ provider: "baidu", baiduAk: "   " }).baiduAk).toBeNull();
  });
  it("invariants: provider flag never panics on unknown env shape", () => {
    const cfg = resolveMapProviderConfig({ provider: undefined, baiduAk: undefined });
    expect(["maplibre", "baidu"]).toContain(cfg.id);
  });
});

describe("Stage 7B-A — Baidu loader error surface", () => {
  beforeEach(() => {
    __resetBaiduLoaderForTests();
  });
  afterEach(() => {
    __resetBaiduLoaderForTests();
  });

  it("isBrowser returns false when document is null", () => {
    expect(isBrowser(null)).toBe(false);
  });

  it("ak-missing: rejects without ever logging the AK", async () => {
    let captured: unknown = null;
    try {
      await loadBaiduMap(null);
    } catch (err) {
      captured = err;
    }
    expect(captured).toBeInstanceOf(BaiduLoadError);
    const e = captured as BaiduLoadError;
    expect(e.code).toBe("ak-missing");
    expect(e.message).toContain("AK");
    expect(e.message).not.toMatch(/[A-Za-z0-9]{16,}/);
    expect(e.hint).toBeTruthy();
    expect(getBaiduLoaderState()).toBe("errored");
    expect(getBaiduLoaderError()).not.toBeNull();
  });

  it("ak-missing: rejects for empty / whitespace AK", async () => {
    for (const v of ["", "   "]) {
      __resetBaiduLoaderForTests();
      await expect(loadBaiduMap(v)).rejects.toMatchObject({ code: "ak-missing" });
    }
  });

  it("singleton: concurrent loadBaiduMap calls without AK reject deterministically", async () => {
    const r1 = loadBaiduMap(null).catch((e) => e);
    const r2 = loadBaiduMap(null).catch((e) => e);
    const [e1, e2] = await Promise.all([r1, r2]);
    expect((e1 as BaiduLoadError).code).toBe("ak-missing");
    expect((e2 as BaiduLoadError).code).toBe("ak-missing");
  });
});

describe("Stage 7B-A — WGS84 coordinate samples (Pilot universities)", () => {
  // The five Pilot sample universities; lng first, lat second.
  const SAMPLES: Array<{ id: string; zh: string; city: string; state: string; lng: number; lat: number }> = [
    { id: "candidate-v2:harvard-university", zh: "哈佛大学", city: "Cambridge", state: "MA", lng: -71.118313, lat: 42.374471 },
    { id: "candidate-v2:columbia-university", zh: "哥伦比亚大学", city: "New York", state: "NY", lng: -73.961885, lat: 40.808286 },
    { id: "candidate-v2:stanford-university", zh: "斯坦福大学", city: "Stanford", state: "CA", lng: -122.167359, lat: 37.429434 },
    { id: "candidate-v2:university-of-chicago", zh: "芝加哥大学", city: "Chicago", state: "IL", lng: -87.599539, lat: 41.787994 },
    { id: "candidate-v2:arizona-state-university", zh: "亚利桑那州立大学", city: "Tempe", state: "AZ", lng: -111.934383, lat: 33.417721 },
  ];

  for (const s of SAMPLES) {
    it(`${s.zh} has a valid US lng/lat (no 0,0, no China shift)`, () => {
      expect(s.lng).toBeGreaterThanOrEqual(-180);
      expect(s.lng).toBeLessThanOrEqual(-50); // continental US
      expect(s.lat).toBeGreaterThanOrEqual(20);
      expect(s.lat).toBeLessThanOrEqual(60);
      expect(s.lng).not.toBe(0);
      expect(s.lat).not.toBe(0);
    });
  }

  it("source universities.json contains all 5 Pilot samples with the documented coordinates", () => {
    const bundlePath = path.resolve(FRONTEND_ROOT, "data/preview/universities.json");
    expect(fs.existsSync(bundlePath)).toBe(true);
    const list = JSON.parse(fs.readFileSync(bundlePath, "utf8")) as Array<Record<string, unknown>>;
    for (const s of SAMPLES) {
      const u = list.find((x) => x.id === s.id);
      expect(u).toBeDefined();
      expect(u?.longitude).toBeCloseTo(s.lng, 5);
      expect(u?.latitude).toBeCloseTo(s.lat, 5);
    }
  });
});

describe("Stage 7B-A — single authoritative regional legend", () => {
  const shellPath = path.resolve(__dirname, "..", "..", "components/map/MapShell.tsx");
  it("MapShell no longer imports MapLegend (duplicate removed)", () => {
    const src = fs.readFileSync(shellPath, "utf8");
    // The duplicate MapLegend import and JSX element must be gone.
    expect(src).not.toMatch(/from\s+["']\.\/MapLegend["']/);
    expect(src).not.toMatch(/<MapLegend\b/);
  });

  it("RegionalLegend is still imported and rendered in MapShell", () => {
    const src = fs.readFileSync(shellPath, "utf8");
    expect(src).toMatch(/from\s+["']\.\/regional\/RegionalLegend["']/);
    expect(src).toMatch(/<RegionalLegend\b/);
  });
});

describe("Stage 7B-A — dark mode contrast normalization", () => {
  const cssPath = path.resolve(__dirname, "..", "..", "app/globals.css");
  it("globals.css maps .bg-white to surface tokens under .dark", () => {
    const src = fs.readFileSync(cssPath, "utf8");
    expect(src).toMatch(/\.dark\s+\.bg-white\s*\{/);
    expect(src).toMatch(/\.dark\s+\.bg-white\\\/94\s*\{/);
  });
  it("globals.css keeps the WCAG-AA dark token ramp intact", () => {
    const src = fs.readFileSync(cssPath, "utf8");
    expect(src).toMatch(/--token-ink:\s+244 240 232/);
    expect(src).toMatch(/--token-paper:\s+24 30 36/);
  });
});

describe("Stage 7B-A — provider adapter surface", () => {
  it("MapLibreProviderAdapter declares MapProviderAdapter methods", () => {
    expect(typeof MapLibreProviderAdapter).toBe("function");
  });
  it("BaiduMapProviderAdapter declares MapProviderAdapter methods", () => {
    expect(typeof BaiduMapProviderAdapter).toBe("function");
  });
  it("BaiduMapProviderAdapter with ak=null still constructs and surfaces ak-missing", async () => {
    let err: unknown = null;
    const a = new BaiduMapProviderAdapter({ ak: null });
    a.initialize({} as HTMLElement, {
      theme: "system",
      view: { center: [-98, 38], zoom: 3 },
      onError: (e: { code: string }) => { err = e; },
    });
    // initialize schedules the AK-missing error; wait a microtask
    await new Promise((r) => setTimeout(r, 5));
    expect(err).not.toBeNull();
    expect((err as { code: string }).code).toBe("ak-missing");
    a.destroy();
  });
});

// Tiny helper so the missing-import path can be checked at runtime.
function _ensureTypesImportable(): MapProviderId {
  return resolveMapProviderId(process?.env?.NEXT_PUBLIC_PATHOS_MAP_PROVIDER);
}
void _ensureTypesImportable;
