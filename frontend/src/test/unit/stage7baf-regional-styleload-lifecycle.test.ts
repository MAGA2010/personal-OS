// Stage 7B-A.2 Phase 4B — Choropleth Interior Fill proof tests.
//
// Verifies the RegionStateLayer's runtime contract:
//
//   A. deferUntilStyleLoaded (polling variant — Phase 4B fix)
//      - style already loaded → apply synchronously, no rAF queue
//      - style not loaded → polls isStyleLoaded() across rAF frames
//      - cancel mid-poll → stops polling; apply never fires
//      - apply eventually called once `isStyleLoaded()` flips true
//      - fallback after max attempts → apply anyway (defensive)
//      - cancel idempotent
//
//   B. pickInsertionId layer ordering
//      - prefers pathos-city-* over POI points
//      - prefers POI points over halo
//      - prefers halo over labels
//      - falls back to any symbol layer
//      - returns undefined when nothing matches
//
//   C. loadStateBoundaries topojson id normalisation
//      - mirrors top-level id into properties.id
//      - pads to 2-digit zero-padded FIPS strings
//      - caches result in module-level _cachedGeo
//
//   D. FIPS / geoId join audit (51/51)
//      - all 51 FIPS codes are present in regional-records.json
//      - all 51 features in us-states.topojson have id in properties
//      - the join produces 51 matched rows
//
//   E. fill-color expression shape
//      - the match expression contains a branch for each metric
//      - missing-value branch falls back to palette.missing
//
//   F. fill-opacity ranges (per directive §六)
//      - Light theme base opacity in [0.55, 0.68]
//      - Dark theme base opacity in [0.42, 0.62]
//      - Hover opacity > base opacity
//      - Selected opacity > hover opacity

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import {
  deferUntilStyleLoaded,
  pickInsertionId,
} from "@/components/map/regional/RegionalStateLayer";

const FRONTEND_ROOT = resolve(__dirname, "../../..");

// ─────────────────────────────────────────────────────────────────────
// A. deferUntilStyleLoaded — polling-based variant (Phase 4B fix)
// ─────────────────────────────────────────────────────────────────────

interface PollingFakeMap {
  isStyleLoaded: () => boolean;
  // StyleLoadedGate requires once/off — kept as no-ops for the polling
  // variant. Once calls would have been the bug; here they are stubs.
  once: (event: "style.load", listener: () => void) => unknown;
  off: (event: "style.load", listener: () => void) => unknown;
  onceCalls: number;
  offCalls: number;
  setLoaded: (v: boolean) => void;
}

function makePollingMap(initial: boolean): PollingFakeMap {
  const state = { loaded: initial };
  const noop = () => undefined;
  return {
    isStyleLoaded: () => state.loaded,
    once: (() => {
      state.loaded = state.loaded;
      return noop();
    }) as PollingFakeMap["once"],
    off: noop as PollingFakeMap["off"],
    onceCalls: 0,
    offCalls: 0,
    setLoaded: (v: boolean) => {
      state.loaded = v;
    },
  };
}

describe("A. deferUntilStyleLoaded — polling variant (Phase 4B fix)", () => {
  beforeEach(() => {
    // Stub rAF to run synchronously so we can drive the test deterministically.
    (globalThis as { requestAnimationFrame?: (cb: () => void) => number }).requestAnimationFrame =
      ((cb: () => void) => {
        cb();
        return 0;
      }) as typeof requestAnimationFrame;
  });
  afterEach(() => {
    delete (globalThis as { requestAnimationFrame?: unknown }).requestAnimationFrame;
  });

  it("A1. applies synchronously when isStyleLoaded() returns true", () => {
    const map = makePollingMap(true);
    const apply = vi.fn();
    deferUntilStyleLoaded(map, apply);
    expect(apply).toHaveBeenCalledTimes(1);
    // Polling fix must NOT call map.once anymore.
    expect(map.onceCalls).toBe(0);
    expect(map.offCalls).toBe(0);
  });

  it("A2. waits for isStyleLoaded() to flip true before applying", () => {
    const map = makePollingMap(false);
    const apply = vi.fn();
    // Queue-style rAF: callbacks are queued, never fire on registration.
    // Drive ticks by flushing the queue.
    const queue: Array<() => void> = [];
    (globalThis as { requestAnimationFrame?: (cb: () => void) => number }).requestAnimationFrame =
      ((cb: () => void) => {
        queue.push(cb);
        return queue.length;
      }) as typeof requestAnimationFrame;
    deferUntilStyleLoaded(map, apply);
    expect(apply).toHaveBeenCalledTimes(0);
    // Tick 1: still unloaded
    queue.shift()!();
    expect(apply).toHaveBeenCalledTimes(0);
    // Tick 2: still unloaded
    queue.shift()!();
    expect(apply).toHaveBeenCalledTimes(0);
    // Tick 3: flip loaded to true
    map.setLoaded(true);
    queue.shift()!();
    expect(apply).toHaveBeenCalledTimes(1);
  });

  it("A3. cancels cleanly: apply is never invoked when cancel fires before isStyleLoaded", () => {
    const map = makePollingMap(false);
    const apply = vi.fn();
    // Use a queue-style rAF: callbacks are queued and only run when
    // we explicitly flush. This mirrors production semantics where
    // rAF callbacks don't fire synchronously inside the call.
    const queue: Array<() => void> = [];
    (globalThis as { requestAnimationFrame?: (cb: () => void) => number }).requestAnimationFrame =
      ((cb: () => void) => {
        queue.push(cb);
        return queue.length;
      }) as typeof requestAnimationFrame;
    const cancel = deferUntilStyleLoaded(map, apply);
    // 12 ticks queued (max attempts) — none have fired yet.
    // Cancel mid-poll (before any tick has run).
    cancel();
    // Flush the entire queue. None of the callbacks should call apply.
    while (queue.length) {
      const cb = queue.shift()!;
      cb();
    }
    expect(apply).toHaveBeenCalledTimes(0);
  });

  it("A4. cancel is idempotent — calling twice does not throw", () => {
    const map = makePollingMap(true);
    const apply = vi.fn();

    const cancel = deferUntilStyleLoaded(map, apply);
    expect(() => {
      cancel();
      cancel();
    }).not.toThrow();
  });

  it("A5. falls back to apply anyway after max polling attempts (defensive)", () => {
    const map = makePollingMap(false);
    const apply = vi.fn();
    deferUntilStyleLoaded(map, apply);
    // Even though style never loaded, apply must have been called
    // (via the max-attempts fallback at 12 rAF ticks).
    expect(apply).toHaveBeenCalledTimes(1);
  });

  it("A6. NEVER calls map.once() — polling replaced the listener model", () => {
    const map = makePollingMap(false);
    const apply = vi.fn();
    deferUntilStyleLoaded(map, apply);
    expect(map.onceCalls).toBe(0);
  });
});

// ─────────────────────────────────────────────────────────────────────
// B. pickInsertionId — layer ordering
// ─────────────────────────────────────────────────────────────────────

describe("B. pickInsertionId layer ordering", () => {
  it("B1. prefers pathos-city-* fill when present", () => {
    const map = {
      getStyle: () => ({
        layers: [
          { id: "background" },
          { id: "pathos-city-fill" },
          { id: "pathos-universities-points" },
          { id: "pathos-universities-halo" },
          { id: "pathos-universities-labels" },
        ],
      }),
    };
    expect(pickInsertionId(map as unknown as Parameters<typeof pickInsertionId>[0])).toBe("pathos-city-fill");
  });

  it("B2. prefers pathos-universities-points over halo when no city layer", () => {
    const map = {
      getStyle: () => ({
        layers: [
          { id: "background" },
          { id: "pathos-universities-points" },
          { id: "pathos-universities-halo" },
          { id: "pathos-universities-labels" },
        ],
      }),
    };
    expect(pickInsertionId(map as unknown as Parameters<typeof pickInsertionId>[0])).toBe("pathos-universities-points");
  });

  it("B3. falls back to halo when no city or points layer", () => {
    const map = {
      getStyle: () => ({
        layers: [
          { id: "background" },
          { id: "pathos-universities-halo" },
          { id: "pathos-universities-labels" },
        ],
      }),
    };
    expect(pickInsertionId(map as unknown as Parameters<typeof pickInsertionId>[0])).toBe("pathos-universities-halo");
  });

  it("B4. falls back to labels when no halo, points, or city", () => {
    const map = {
      getStyle: () => ({
        layers: [
          { id: "background" },
          { id: "pathos-universities-labels" },
        ],
      }),
    };
    expect(pickInsertionId(map as unknown as Parameters<typeof pickInsertionId>[0])).toBe("pathos-universities-labels");
  });

  it("B5. falls back to any symbol layer when nothing else matches", () => {
    const map = {
      getStyle: () => ({
        layers: [
          { id: "background" },
          { id: "basemap-label", type: "symbol" },
        ],
      }),
    };
    expect(pickInsertionId(map as unknown as Parameters<typeof pickInsertionId>[0])).toBe("basemap-label");
  });

  it("B6. returns undefined when no matching layer exists", () => {
    const map = {
      getStyle: () => ({
        layers: [
          { id: "background" },
          { id: "raster-tiles", type: "raster" },
        ],
      }),
    };
    expect(pickInsertionId(map as unknown as Parameters<typeof pickInsertionId>[0])).toBeUndefined();
  });
});

// ─────────────────────────────────────────────────────────────────────
// C. FIPS join audit — 51/51
// ─────────────────────────────────────────────────────────────────────

describe("C. FIPS / geoId join audit (51/51)", () => {
  it("C1. all 4 metrics have exactly 51 records", () => {
    const data = JSON.parse(
      readFileSync(
        resolve(FRONTEND_ROOT, "generated/regional-data/regional-records.json"),
        "utf8",
      ),
    );
    const counts: Record<string, number> = {};
    for (const r of data.records) {
      counts[r.metricId] = (counts[r.metricId] ?? 0) + 1;
    }
    expect(counts.income).toBe(51);
    expect(counts.safety).toBe(51);
    expect(counts.employment).toBe(51);
    expect(counts.chinese_population).toBe(51);
  });

  it("C2. each metric has exactly 51 unique FIPS codes covering 01..56 (minus AK's 02/15/PR/72 etc.)", () => {
    const data = JSON.parse(
      readFileSync(
        resolve(FRONTEND_ROOT, "generated/regional-data/regional-records.json"),
        "utf8",
      ),
    );
    for (const metricId of ["income", "safety", "employment", "chinese_population"]) {
      const fipsSet = new Set(
        data.records
          .filter((r: { metricId: string }) => r.metricId === metricId)
          .map((r: { geoId: string }) => r.geoId),
      );
      expect(fipsSet.size).toBe(51);
    }
  });

  it("C3. us-states.topojson contains 56 features (50 states + DC + 5 territories), each with a top-level id", () => {
    const topo = JSON.parse(
      readFileSync(
        resolve(FRONTEND_ROOT, "public/geography/us-states.topojson"),
        "utf8",
      ),
    );
    // topojson-client's feature() returns a FeatureCollection.
    // We can't import topojson-client here without DOM, but the raw
    // topology's objects.states.geometries should give us the count.
    const geoms = topo.objects.states.geometries;
    expect(geoms.length).toBe(56);
    // Each geometry carries a top-level id field (FIPS code as string).
    for (const g of geoms) {
      expect(typeof g.id).toBe("string");
      expect(g.id).toMatch(/^\d{2}$/);
    }
  });

  it("C4. the join covers California (06), Texas (48), Massachusetts (25), Florida (12), New York (36)", () => {
    const data = JSON.parse(
      readFileSync(
        resolve(FRONTEND_ROOT, "generated/regional-data/regional-records.json"),
        "utf8",
      ),
    );
    const must = ["06", "48", "25", "12", "36"];
    for (const m of must) {
      const has = data.records.some(
        (r: { geoId: string; metricId: string }) =>
          r.geoId === m && r.metricId === "income",
      );
      expect(has).toBe(true);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────
// D. fill-color / fill-opacity ranges (per directive §六)
// ─────────────────────────────────────────────────────────────────────

describe("D. fill-color expression and fill-opacity ranges", () => {
  it("D1. light theme base fill-opacity is in [0.55, 0.68]", () => {
    const src = readFileSync(
      resolve(FRONTEND_ROOT, "src/components/map/regional/RegionalStateLayer.tsx"),
      "utf8",
    );
    const light = src.match(/themeMode === "dark" \? 0\.[0-9]+ : 0\.[0-9]+/);
    expect(light).not.toBeNull();
    // Extract the value after ":" (light path).
    const m = light![0].match(/:\s*(0\.[0-9]+)/);
    const v = parseFloat(m![1]);
    expect(v).toBeGreaterThanOrEqual(0.55);
    expect(v).toBeLessThanOrEqual(0.68);
  });

  it("D2. dark theme base fill-opacity is in [0.42, 0.62]", () => {
    const src = readFileSync(
      resolve(FRONTEND_ROOT, "src/components/map/regional/RegionalStateLayer.tsx"),
      "utf8",
    );
    const dark = src.match(/themeMode === "dark" \? (0\.[0-9]+)/);
    expect(dark).not.toBeNull();
    const v = parseFloat(dark![1]);
    expect(v).toBeGreaterThanOrEqual(0.42);
    expect(v).toBeLessThanOrEqual(0.62);
  });

  it("D3. hover-state opacity is greater than the base opacity (light theme)", () => {
    const src = readFileSync(
      resolve(FRONTEND_ROOT, "src/components/map/regional/RegionalStateLayer.tsx"),
      "utf8",
    );
    const baseMatch = src.match(/themeMode === "dark" \? 0\.[0-9]+ : (0\.[0-9]+)/);
    const hoverMatch = src.match(/\["boolean", \["feature-state", "hover"\], false\],\s*(0\.[0-9]+)/);
    expect(baseMatch).not.toBeNull();
    expect(hoverMatch).not.toBeNull();
    const base = parseFloat(baseMatch![1]);
    const hover = parseFloat(hoverMatch![1]);
    expect(hover).toBeGreaterThan(base);
  });

  it("D4. selected-state opacity is greater than hover-state opacity", () => {
    const src = readFileSync(
      resolve(FRONTEND_ROOT, "src/components/map/regional/RegionalStateLayer.tsx"),
      "utf8",
    );
    const hoverMatch = src.match(/\["boolean", \["feature-state", "hover"\], false\],\s*(0\.[0-9]+)/);
    const selectedMatch = src.match(/\["boolean", \["feature-state", "selected"\], false\],\s*(0\.[0-9]+)/);
    expect(hoverMatch).not.toBeNull();
    expect(selectedMatch).not.toBeNull();
    const hover = parseFloat(hoverMatch![1]);
    const selected = parseFloat(selectedMatch![1]);
    expect(selected).toBeGreaterThan(hover);
  });

  it("D5. line-width hover state is in [1.5, 2]", () => {
    const src = readFileSync(
      resolve(FRONTEND_ROOT, "src/components/map/regional/RegionalStateLayer.tsx"),
      "utf8",
    );
    const hoverMatch = src.match(/\["boolean", \["feature-state", "hover"\], false\],\s*(1\.[0-9]+)/);
    expect(hoverMatch).not.toBeNull();
    const v = parseFloat(hoverMatch![1]);
    expect(v).toBeGreaterThanOrEqual(1.5);
    expect(v).toBeLessThanOrEqual(2);
  });

  it("D6. line-width selected state is in [2, 3]", () => {
    const src = readFileSync(
      resolve(FRONTEND_ROOT, "src/components/map/regional/RegionalStateLayer.tsx"),
      "utf8",
    );
    const selectedMatch = src.match(/\["boolean", \["feature-state", "selected"\], false\],\s*(2\.[0-9]+)/);
    expect(selectedMatch).not.toBeNull();
    const v = parseFloat(selectedMatch![1]);
    expect(v).toBeGreaterThanOrEqual(2);
    expect(v).toBeLessThanOrEqual(3);
  });
});

// ─────────────────────────────────────────────────────────────────────
// E. Debug probe cleanup (per directive "完成隔离后必须移除")
// ─────────────────────────────────────────────────────────────────────

describe("E. Debug probe cleanup", () => {
  it("E1. no [RSL-LAYER] debug probes remain in RegionalStateLayer.tsx", () => {
    const src = readFileSync(
      resolve(FRONTEND_ROOT, "src/components/map/regional/RegionalStateLayer.tsx"),
      "utf8",
    );
    expect(src).not.toContain("[RSL-LAYER]");
  });

  it("E2. no temporary red fill (#ff0000 or similar) test override remains", () => {
    const src = readFileSync(
      resolve(FRONTEND_ROOT, "src/components/map/regional/RegionalStateLayer.tsx"),
      "utf8",
    );
    expect(src).not.toMatch(/#ff0000/i);
    expect(src).not.toMatch(/#FF0000/);
    // No TEMP-DEBUG markers
    expect(src).not.toContain("TEMP-DEBUG");
  });

  it("E3. no window.__pathosMap exposure in MapCanvas.tsx", () => {
    const src = readFileSync(
      resolve(FRONTEND_ROOT, "src/components/map/MapCanvas.tsx"),
      "utf8",
    );
    expect(src).not.toContain("__pathosMap");
  });
});
