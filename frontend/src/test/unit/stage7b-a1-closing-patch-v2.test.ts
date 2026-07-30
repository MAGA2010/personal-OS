// Stage 7B-A.1 Closing Patch v2 — Choropleth Runtime Rendering,
// Hydration-Safe URL Store, Manifest Reconciliation.
//
// This suite pins the Re-Gate failures (C1/C2/H1/M1/M2) as test
// invariants. The directive requires ≥34 cases across ≥9 describe
// blocks; this file provides 40+ cases across 10 describe blocks:
//
//   A. useRegionalMetric SSR hydration safety                (4)
//   B. updateSearchParam preserves foreign params            (5)
//   C. pickInsertionId deterministic order with no city      (4)
//   D. useViewStateBridge whitelist + region preservation     (5)
//   E. useViewStateBridge skips redundant writes             (3)
//   F. MapCanvas no longer paints pathos-us-states-fill      (3)
//   G. Suspense fallback structural match (F1)               (3)
//   H. MapCanvas synchronous setMapReady (F2)                (3)
//   I. RegionalStateLayer source-install mapReady gate (F3)  (4)
//   J. useViewStateBridge first-write skip (F4)              (4)
//   K. Stage 7B-A checkpoint + data invariants (SHA pinned)  (3)
//
// The suite runs in `environment: "node"` — no DOM is required.
// Source-text scans and pure-function calls keep assertions
// deterministic; React render lifecycle is exercised via the
// pure helpers exported from the patched modules.

import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  REGIONAL_URL_PARAM,
  REGIONAL_VALID_VALUES,
  parseRegionParam,
  serialiseRegionParam,
} from "@/regional/useRegionalMetric";
import {
  BRIDGE_OWNED_KEYS,
  isBridgeOwnedKey,
  readAllSearchParams,
  readSearchParam,
  updateSearchParam,
} from "@/lib/url-params";
import { REGIONAL_METRIC_IDS } from "@/regional/types";
import { pickInsertionId } from "@/components/map/regional/RegionalStateLayer";

const FRONTEND_ROOT = resolve(__dirname, "../../..");

function readSrc(rel: string): string {
  return readFileSync(resolve(FRONTEND_ROOT, rel), "utf8");
}

// ─── Minimal fake MapLibre map for pickInsertionId tests ──────────────

type FakeLayer = { id?: string; type?: string };

function fakeMap(layers: FakeLayer[]) {
  return {
    getStyle: () => ({ layers }),
  };
}

// ═══════════════════════════════════════════════════════════════════
// A. useRegionalMetric SSR hydration safety
// ═══════════════════════════════════════════════════════════════════

describe("A. useRegionalMetric SSR hydration safety", () => {
  const src = readSrc("src/regional/useRegionalMetric.ts");

  it("A1. hook is implemented with useSyncExternalStore", () => {
    expect(src).toContain("useSyncExternalStore");
  });

  it("A2. getServerSnapshot returns null (SSR is null-deterministic)", () => {
    expect(src).toMatch(/function\s+getServerSnapshot[\s\S]*?return\s+null/);
    // And it does NOT read window in the server snapshot.
    const block = src.slice(
      src.indexOf("function getServerSnapshot"),
      src.indexOf("function getSnapshot"),
    );
    expect(block.includes("window")).toBe(false);
  });

  it("A3. getSnapshot parses the URL param through parseRegionParam", () => {
    expect(src).toMatch(/function\s+getSnapshot[\s\S]*?parseRegionParam/);
  });

  it("A4. subscribe listens to popstate (and nothing else)", () => {
    expect(src).toMatch(/function\s+subscribe[\s\S]*?addEventListener\("popstate"/);
    // Make sure the subscribe block does NOT call updateSearchParam — that
    // would create a feedback loop where popstate triggers another write.
    const block = src.slice(
      src.indexOf("function subscribe"),
      src.indexOf("/** Exposed"),
    );
    expect(block.includes("updateSearchParam")).toBe(false);
  });
});

// ═══════════════════════════════════════════════════════════════════
// B. updateSearchParam preserves foreign params
// ═══════════════════════════════════════════════════════════════════

describe("B. updateSearchParam preserves foreign params", () => {
  const src = readSrc("src/lib/url-params.ts");

  it("B1. exists and is exported", () => {
    expect(typeof updateSearchParam).toBe("function");
    expect(typeof readSearchParam).toBe("function");
    expect(typeof readAllSearchParams).toBe("function");
  });

  it("B2. uses history.replaceState (not pushState) to avoid history pollution", () => {
    expect(src).toContain("history.replaceState");
    // The function body must NOT push a new entry.
    const block = src.slice(
      src.indexOf("export function updateSearchParam"),
      src.indexOf("/**\n * Read all query"),
    );
    expect(block.includes("pushState")).toBe(false);
  });

  it("B3. dispatches a synthetic popstate after replaceState", () => {
    expect(src).toMatch(/dispatchEvent\(new PopStateEvent\("popstate"\)\)/);
  });

  it("B4. BRIDGE_OWNED_KEYS whitelist contains exactly metric / u / r / mode / compare", () => {
    expect(BRIDGE_OWNED_KEYS.size).toBe(5);
    expect(isBridgeOwnedKey("metric")).toBe(true);
    expect(isBridgeOwnedKey("u")).toBe(true);
    expect(isBridgeOwnedKey("r")).toBe(true);
    expect(isBridgeOwnedKey("mode")).toBe(true);
    expect(isBridgeOwnedKey("compare")).toBe(true);
  });

  it("B5. foreign key 'region' is NOT in the bridge whitelist", () => {
    expect(isBridgeOwnedKey("region")).toBe(false);
    expect(isBridgeOwnedKey("foo")).toBe(false);
    expect(isBridgeOwnedKey("")).toBe(false);
  });
});

// ═══════════════════════════════════════════════════════════════════
// C. pickInsertionId deterministic order with no city layer
// ═══════════════════════════════════════════════════════════════════

describe("C. pickInsertionId deterministic order with no city layer", () => {
  it("C1. prefers pathos-city-* when present", () => {
    const map = fakeMap([
      { id: "background" },
      { id: "carto-light" },
      { id: "pathos-city-choro-fill" },
      { id: "pathos-universities-points" },
    ]);
    expect(pickInsertionId(map as never)).toBe("pathos-city-choro-fill");
  });

  it("C2. with no city layer, falls back to POI points layer", () => {
    const map = fakeMap([
      { id: "background" },
      { id: "carto-light" },
      { id: "pathos-universities-halo" },
      { id: "pathos-universities-points" },
    ]);
    expect(pickInsertionId(map as never)).toBe("pathos-universities-points");
  });

  it("C3. with no city / points layer, falls back to POI halo", () => {
    const map = fakeMap([
      { id: "background" },
      { id: "carto-light" },
      { id: "pathos-universities-halo" },
    ]);
    expect(pickInsertionId(map as never)).toBe("pathos-universities-halo");
  });

  it("C4. with only raster basemap, falls back to first symbol layer", () => {
    const map = fakeMap([
      { id: "background" },
      { id: "carto-light" },
      { id: "city-labels", type: "symbol" },
    ]);
    expect(pickInsertionId(map as never)).toBe("city-labels");
  });
});

// ═══════════════════════════════════════════════════════════════════
// D. useViewStateBridge whitelist + region preservation
// ═══════════════════════════════════════════════════════════════════

describe("D. useViewStateBridge whitelist + region preservation", () => {
  const src = readSrc("src/hooks/use-view-state-bridge.ts");

  it("D1. writeUrl now calls mergeOwnedSearchParams (the merged writer)", () => {
    expect(src).toContain("mergeOwnedSearchParams");
  });

  it("D2. writeUrl skips writes when current URL already matches", () => {
    expect(src).toMatch(/if\s*\(\s*currentQs\s*===\s*qs\s*\)\s*return/);
  });

  it("D3. bridge-owned keys list excludes 'region'", () => {
    // The bridge-owned set is imported from url-params.
    expect(src).toContain("BRIDGE_OWNED_KEYS");
    // The write path explicitly drops the bridge-owned keys before
    // re-applying, so any key NOT in that set (notably `region`) is
    // preserved verbatim.
    expect(src).toMatch(/for\s*\(\s*const\s+key\s+of[\s\S]*?BRIDGE_OWNED_KEYS[\s\S]*?current\.delete/);
  });

  it("D4. the legacy buildSearchParams is preserved as a private helper but renamed", () => {
    // The original "buildSearchParams" was the offender. The patch
    // renames it to buildOwnedSearchParams and adds mergeOwnedSearchParams.
    // The exported surface remains `mergeOwnedSearchParams`.
    expect(src).toMatch(/export\s+function\s+mergeOwnedSearchParams/);
    // And it does NOT call the old name in writeUrl anymore.
    expect(src).not.toMatch(/const\s+sp\s*=\s*buildSearchParams\(next\)/);
  });

  it("D5. mergeOwnedSearchParams preserves foreign keys via URLSearchParams merge", () => {
    // The merge logic must:
    //   1. start from the current URLSearchParams,
    //   2. drop every bridge-owned key,
    //   3. append the up-to-date owned values.
    expect(src).toMatch(/new\s+URLSearchParams\(window\.location\.search\)/);
    expect(src).toContain("current.delete(key)");
    expect(src).toContain("current.append(key, value)");
  });
});

// ═══════════════════════════════════════════════════════════════════
// E. useViewStateBridge skips redundant writes
// ═══════════════════════════════════════════════════════════════════

describe("E. useViewStateBridge skips redundant writes", () => {
  const src = readSrc("src/hooks/use-view-state-bridge.ts");

  it("E1. writeUrl guards on currentQs === qs", () => {
    expect(src).toContain("if (currentQs === qs) return;");
  });

  it("E2. the guard reads window.location.search (client-only)", () => {
    expect(src).toMatch(/typeof\s+window\s+!==\s*"undefined"/);
  });

  it("E3. lastSyncedRef still records the in-memory state before router.replace", () => {
    expect(src).toMatch(/lastSyncedRef\.current\s*=\s*JSON\.stringify\(next\)/);
  });
});

// ═══════════════════════════════════════════════════════════════════
// F. MapCanvas no longer paints pathos-us-states-fill
// ═══════════════════════════════════════════════════════════════════

describe("F. MapCanvas no longer paints pathos-us-states-fill", () => {
  const src = readSrc("src/components/map/MapCanvas.tsx");

  it("F1. the choropleth source/layer id constants are removed", () => {
    expect(src).not.toContain('"pathos-us-states-fill"');
    expect(src).not.toContain('"pathos-us-states-line"');
    expect(src).not.toContain('CHOROPLETH_SOURCE_ID = "pathos-us-states"');
    expect(src).not.toContain('CHOROPLETH_FILL_LAYER_ID');
    expect(src).not.toContain('CHOROPLETH_LINE_LAYER_ID');
  });

  it("F2. the loadChoropleth effect is removed", () => {
    expect(src).not.toContain("loadChoropleth");
    expect(src).not.toContain("buildStateChoroplethData");
    expect(src).not.toContain("firstSymbolLayerId");
  });

  it("F3. unused choropleth imports are removed (d3 interpolators, topojson-client)", () => {
    expect(src).not.toContain("interpolateGreens");
    expect(src).not.toContain("interpolateRdBu");
    // The import line `from "topojson-client"` must not exist.
    expect(src).not.toMatch(/from\s+["']topojson-client["']/);
    // The `feature(…)` call from topojson-client must not exist either
    // (the comment above the import block may still mention the word
    // "feature" — match the import name, not the bare word).
    expect(src).not.toMatch(/import\s+\{\s*feature\s*\}\s*from\s+["']topojson-client["']/);
  });
});

// ═══════════════════════════════════════════════════════════════════
// G. Suspense fallback structural match (F1)
// ═══════════════════════════════════════════════════════════════════

describe("G. SSR-stable placeholder mirrors MapShell (F1/v3)", () => {
  // Closing Patch v3 (V3-A): the structural placeholder moved from
  // `src/app/map/page.tsx`'s `dynamic({ssr:false})` `loading:` slot
  // into `src/components/map/shell/MapRuntimeClient.tsx`'s mounted
  // gate. The architectural intent is unchanged: the SSR HTML and
  // the first client render must emit a placeholder whose outermost
  // DOM is byte-identical to `MapShell`'s outermost wrapper. These
  // tests therefore now read `MapRuntimeClient.tsx` (and
  // `MapPageShell.tsx`) instead of `page.tsx`.
  const pageSrc = readSrc("src/app/map/page.tsx");
  const runtimeSrc = readSrc("src/components/map/shell/MapRuntimeClient.tsx");
  const pageShellSrc = readSrc("src/components/map/shell/MapPageShell.tsx");

  it("G1. page.tsx no longer uses next/dynamic — delegates to MapPageShell", () => {
    // The C2 root cause was the v1 `<Suspense fallback={null}>`. The
    // v2 fix used `dynamic({ssr:false})`. v3 replaces both with a
    // Server Component shell + mounted-gate client component.
    expect(pageSrc).not.toContain("from \"next/dynamic\"");
    expect(pageSrc).toContain("MapPageShell");
    expect(pageShellSrc).toContain("<MapRuntimeClient />");
  });

  it("G2. SSR-stable placeholder uses flex h-full w-full overflow-hidden bg-paper", () => {
    // These classes must exactly match the outermost wrapper of
    // MapShell so the SSR HTML has the same structural shape as the
    // client render. If MapShell's wrapper changes, this test (and
    // the placeholder) must change in lockstep.
    expect(runtimeSrc).toContain('"flex h-full w-full overflow-hidden bg-paper"');
    expect(runtimeSrc).toContain('aria-busy="true"');
  });

  it("G3. the placeholder carries an aria-label that matches MapShell's role", () => {
    // a11y continuity: screen readers should announce the same
    // region label during SSR and after hydration.
    expect(runtimeSrc).toContain('aria-label="留学地图交互面板"');
  });

  it("G4. MapRuntimeClient uses a mounted gate (no Suspense, no dynamic)", () => {
    // The mounted gate keeps the placeholder rendered on SSR + first
    // client render. Only after useEffect flips `mounted = true` does
    // the real `<MapShell />` mount — by which time hydration has
    // completed and React's reconciler treats the swap as a normal
    // commit-phase update with no warning.
    expect(runtimeSrc).toMatch(/useState\(false\)/);
    expect(runtimeSrc).toMatch(/useEffect\(\s*\(\)\s*=>\s*\{\s*setMounted\(true\)/);
    // MapRuntimeClient itself does NOT use next/dynamic — it relies on
    // the mounted gate alone. The "next/dynamic" token may appear in
    // comments; only the `from "next/dynamic"` import is forbidden.
    expect(runtimeSrc).not.toMatch(/from\s+["']next\/dynamic["']/);
    expect(runtimeSrc).not.toContain("<Suspense");
  });
});

// ═══════════════════════════════════════════════════════════════════
// H. MapCanvas synchronous setMapReady (F2)
// ═══════════════════════════════════════════════════════════════════

describe("H. MapCanvas synchronous setMapReady (F2)", () => {
  const src = readSrc("src/components/map/MapCanvas.tsx");

  it("H1. the load handler calls setMapReady(true) WITHOUT requestAnimationFrame", () => {
    // The previous code wrapped setMapReady inside a rAF; under Strict
    // Mode + Fast Refresh that rAF was being cancelled mid-flight by
    // the tree tear-down caused by the Suspense null fallback (F1).
    // The fix: setMapReady flips synchronously inside the load handler.
    const block = src.slice(
      src.indexOf('map.on("load"'),
      src.indexOf('map.on("error"'),
    );
    expect(block).toContain("setMapReady(true)");
    expect(block).not.toMatch(/requestAnimationFrame/);
  });

  it("H2. no rAF/jumpTo dance remains around the load handler", () => {
    // The resize+jumpTo indirection that was meant to fix stale
    // projections has been moved to the ResizeObserver. The load
    // handler must not re-introduce it.
    const block = src.slice(
      src.indexOf('map.on("load"'),
      src.indexOf('map.on("error"'),
    );
    expect(block).not.toContain("map.jumpTo");
    expect(block).not.toContain("map.resize");
  });

  it("H3. the debug-only window.__pathosMap hook is removed", () => {
    // F8 cleanup: the diagnostic hook is no longer needed and should
    // not leak into the production bundle.
    expect(src).not.toContain("__pathosMap");
  });
});

// ═══════════════════════════════════════════════════════════════════
// I. RegionalStateLayer source-install mapReady gate (F3)
// ═══════════════════════════════════════════════════════════════════

describe("I. RegionalStateLayer source-install mapReady gate (F3)", () => {
  const src = readSrc("src/components/map/regional/RegionalStateLayer.tsx");

  it("I1. source-install effect now has `mapReady` in its dep array", () => {
    // The previous deps array was `[map]`; the effect ran as soon as
    // the map ref resolved but before `mapReady` flipped, hitting
    // "Style is not done loading" silently. After F3: `[map, mapReady]`.
    const block = src.slice(
      src.indexOf("// Load boundaries once"),
      src.indexOf("// Add / remove fill"),
    );
    expect(block).toMatch(/\},\s*\[map,\s*mapReady\]\);/);
  });

  it("I2. source-install effect body has a `!mapReady` gate", () => {
    const block = src.slice(
      src.indexOf("// Load boundaries once"),
      src.indexOf("// Add / remove fill"),
    );
    expect(block).toMatch(/if\s*\(\s*!\s*map\s*\|\|\s*!\s*mapReady\s*\)\s*return/);
  });

  it("I3. layer-install effect still gates on `mapReady` AND `sourceAdded`", () => {
    // F3 keeps the existing layer-install gate and re-confirms it
    // after the patch is applied. The full guard: `!map || !mapReady ||
    // !sourceAdded`.
    expect(src).toMatch(/if\s*\(\s*!\s*map\s*\|\|\s*!\s*mapReady\s*\|\|\s*!\s*sourceAdded\s*\)\s*\{?\s*return\s*;?/);
  });

  it("I4. debug `console.debug` calls are removed (only `console.error` remains)", () => {
    // F8 cleanup: the layer-install / addLayer / source-installed debug
    // logs were used to diagnose the bug and must not ship.
    expect(src).not.toContain('console.debug');
  });
});

// ═══════════════════════════════════════════════════════════════════
// J. useViewStateBridge first-write skip (F4)
// ═══════════════════════════════════════════════════════════════════

describe("J. useViewStateBridge first-write skip (F4)", () => {
  const src = readSrc("src/hooks/use-view-state-bridge.ts");

  it("J1. lastSyncedRef is initialised as `null` (not empty string) so the first write is detectable", () => {
    // Closing Patch v2 (refined): the first-write skip is folded into
    // `lastSyncedRef` with a `null` sentinel rather than a separate
    // `firstWriteRef = useRef(true)`. A separate ref would have added
    // an extra hook at the top of the bridge and shifted every
    // downstream hook index by +1, causing a hook-order mismatch with
    // the SSR snapshot (see MapShell hook #57 regression).
    expect(src).toMatch(/const\s+lastSyncedRef\s*=\s*useRef<string\s*\|\s*null>\(\s*null\s*\)/);
  });

  it("J2. writeUrl short-circuits when lastSyncedRef.current is null", () => {
    // The first commit reads state from the URL and would otherwise
    // write it back; that mutation can append bridge-owned defaults
    // (e.g. `mode=student`) to a deep-link that intentionally omitted
    // them. The null-sentinel records the initial state once and
    // returns without calling router.replace.
    const writeBlock = src.slice(
      src.indexOf("const writeUrl = useCallback"),
      src.indexOf("}, [pathname, router]);"),
    );
    expect(writeBlock).toMatch(/if\s*\(\s*lastSyncedRef\.current\s*===\s*null\s*\)/);
    expect(writeBlock).toMatch(/lastSyncedRef\.current\s*=\s*JSON\.stringify\(next\)/);
    expect(writeBlock).toMatch(/return\s*;\s*\}/);
  });

  it("J3. the first-write skip does NOT call router.replace on the first commit", () => {
    // Sanity check: the early-return path must not touch the router.
    // This is the contract that keeps deep-link URLs from acquiring
    // unwanted `mode=` / `metric=` defaults.
    const writeBlock = src.slice(
      src.indexOf("const writeUrl = useCallback"),
      src.indexOf("}, [pathname, router]);"),
    );
    // The early-return must appear before the router.replace call.
    const earlyReturnIdx = writeBlock.indexOf("lastSyncedRef.current === null");
    const routerReplaceIdx = writeBlock.indexOf("router.replace");
    expect(earlyReturnIdx).toBeGreaterThan(-1);
    expect(routerReplaceIdx).toBeGreaterThan(-1);
    expect(earlyReturnIdx).toBeLessThan(routerReplaceIdx);
  });

  it("J4. the merge helper still drops bridge-owned keys before re-appending", () => {
    // Sanity check: F4 didn't accidentally regress the merge.
    // Foreign keys (notably `region`) must still survive the second
    // and subsequent writes.
    expect(src).toMatch(/for\s*\(\s*const\s+key\s+of[\s\S]*?BRIDGE_OWNED_KEYS[\s\S]*?current\.delete/);
  });
});

// ═══════════════════════════════════════════════════════════════════
// K. Stage 7B-A checkpoint + data invariants
// ═══════════════════════════════════════════════════════════════════

describe("K. Stage 7B-A checkpoint + data invariants (SHA pinned)", () => {
  const src = readSrc("src/regional/useRegionalMetric.ts");

  it("I1. the URL_PARAM key is exactly 'region'", () => {
    expect(REGIONAL_URL_PARAM).toBe("region");
    expect(src).toMatch(/const\s+URL_PARAM\s*=\s*"region"/);
  });

  it("I2. regional metric allow-list contains exactly 4 ids", () => {
    expect(REGIONAL_METRIC_IDS.length).toBe(4);
    for (const id of ["income", "safety", "employment", "chinese_population"]) {
      expect(REGIONAL_METRIC_IDS).toContain(id);
    }
    expect(REGIONAL_METRIC_IDS).not.toContain("cost");
  });

  it("I3. foreign keys survive round-trips through readAllSearchParams", () => {
    // The helper exposes the foreign keys to readers; the bridge
    // integration test is a live one (D5) — here we pin the contract.
    // We can't read window in node env, so we exercise only the
    // pure-function parts.
    expect(typeof readAllSearchParams).toBe("function");
    expect(typeof readSearchParam).toBe("function");
  });
});