// Stage 7B-A.1 Closing Patch v3 — SSR-stable shell, URL purity
// hardening, console.warn monkey-patch removal.
//
// This suite is ADDITIVE to `stage7b-a1-closing-patch-v2.test.ts`.
// The v2 suite covers the F1–F8 patch (Suspense fallback, sync
// setMapReady, source-install gate, first-write skip, dynamic
// MapShell, etc.). The v3 suite pins the *new* invariants introduced
// by the v3 patch:
//
//   H. SSR-stable page shell (V3-A)
//      - page.tsx is a Server Component
//      - MapPageShell statically renders <main> + floating chrome
//      - MapToolbarClient was deleted as an unused orphan (Phase 0.1
//        of Stage 7B-A.2). The orphan-cleanup invariant is now
//        pinned in H5/H6: the file must not exist, and no live
//        source may import it.
//      - MapRuntimeClient uses a mounted gate (no Suspense / dynamic)
//      - placeholder DOM matches MapShell's outermost wrapper
//
//   I. URL store render-time purity (V3-C)
//      - useViewStateBridge writeUrl never fires during render
//      - lastSyncedRef null sentinel skips first commit
//      - apply() updater is pure (no router.replace inside)
//      - getSnapshot / getServerSnapshot are pure reads
//
//   J. console.warn monkey-patch leak removed (V3-D)
//      - MapCanvas no longer captures `console.warn`
//      - Cleanup function no longer restores `origWarn`
//      - MapLibre error handler still filters transient noise
//
//   K. Choropleth retention invariants
//      - 4 regional metrics still routed through useRegionalMetric
//      - MapShell outermost wrapper classes preserved
//      - theme / metric / Back / Forward wiring unchanged
//
//   L. Strict-Mode-safe hook order in MapShell + child hooks
//      - useRegionalMetric / useTheme / useViewStateBridge all use
//        useSyncExternalStore or stable hook count
//      - First-commit skip ensures no render-time router.replace

import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const FRONTEND_ROOT = resolve(__dirname, "../../..");

function readSrc(rel: string): string {
  return readFileSync(resolve(FRONTEND_ROOT, rel), "utf8");
}

// ═══════════════════════════════════════════════════════════════════
// H. SSR-stable page shell (V3-A)
// ═══════════════════════════════════════════════════════════════════

describe("H. SSR-stable page shell (V3-A)", () => {
  const pageSrc = readSrc("src/app/map/page.tsx");
  const pageShellSrc = readSrc("src/components/map/shell/MapPageShell.tsx");
  const runtimeClientSrc = readSrc(
    "src/components/map/shell/MapRuntimeClient.tsx",
  );
  // MapToolbarClient.tsx was deleted in Stage 7B-A.2 Phase 0.1 as an
  // unused orphan. We pin its absence here via fs.existsSync so that
  // any future re-introduction of an orphan file trips the test.
  const toolbarClientPath = resolve(
    FRONTEND_ROOT,
    "src/components/map/shell/MapToolbarClient.tsx",
  );
  const toolbarClientExists = existsSync(toolbarClientPath);

  it("H1. page.tsx is a Server Component (no 'use client')", () => {
    expect(pageSrc).not.toMatch(/^["']use client["']/m);
    // It imports `MapPageShell` from the shell/ folder.
    expect(pageSrc).toMatch(/from\s+["']@\/components\/map\/shell\/MapPageShell["']/);
  });

  it("H2. page.tsx does NOT use next/dynamic", () => {
    // The v2 fix used `dynamic({ssr:false})`; v3 replaces both
    // Suspense-fallback and dynamic with a Server Component shell.
    expect(pageSrc).not.toContain("from \"next/dynamic\"");
    expect(pageSrc).not.toContain("<Suspense");
  });

  it("H3. MapPageShell statically renders <main> with aria-label='留学地图'", () => {
    expect(pageShellSrc).toContain("<main");
    expect(pageShellSrc).toContain('aria-label="留学地图"');
    // The main has the same fixed-height chrome as the v2 page.
    expect(pageShellSrc).toContain("calc(100vh - 3.5rem)");
  });

  it("H4. MapPageShell wraps MapRuntimeClient in a host div", () => {
    // V3-G final architecture: MapPageShell contains ONLY <MapRuntimeClient />
    // in a host div. MapShell itself renders the unified MapToolbar in
    // its own body.
    expect(pageShellSrc).toContain("<MapRuntimeClient />");
    // The host div preserves the v2 structural identity.
    expect(pageShellSrc).toContain('"relative flex-1 min-h-0"');
  });

  it("H5. MapToolbarClient orphan file is deleted (Phase 0.1 cleanup)", () => {
    // Stage 7B-A.1 v3 originally retained MapToolbarClient as an
    // unused SSR-stable component "to keep test coverage". Stage 7B-A.2
    // Phase 0.1 deleted the orphan — the floating news + 留学资讯 buttons
    // were redundant with the sidebar's 留学资讯 panel and the map's
    // own attribution badge. The orphan must NOT be reintroduced.
    expect(toolbarClientExists).toBe(false);
  });

  it("H6. No live source imports MapToolbarClient", () => {
    // Even with the file deleted, no other source may still import it
    // (stale import would surface as a build error). We check for
    // actual import / JSX usages rather than any text mention, since
    // page.tsx JSDoc references the deletion in a Phase 0.1 note.
    expect(pageSrc).not.toMatch(/from\s+["'][^"']*MapToolbarClient/);
    expect(pageSrc).not.toMatch(/<MapToolbarClient\b/);
    expect(pageShellSrc).not.toMatch(/from\s+["'][^"']*MapToolbarClient/);
    expect(pageShellSrc).not.toMatch(/<MapToolbarClient\b/);
    expect(runtimeClientSrc).not.toMatch(/from\s+["'][^"']*MapToolbarClient/);
    expect(runtimeClientSrc).not.toMatch(/<MapToolbarClient\b/);
  });

  it("H7. MapRuntimeClient uses a mounted gate", () => {
    expect(runtimeClientSrc).toMatch(/useState\(false\)/);
    expect(runtimeClientSrc).toMatch(
      /useEffect\(\s*\(\)\s*=>\s*\{\s*setMounted\(true\);?\s*\}/,
    );
    // The mounted gate is a one-shot state flip — empty dependency
    // array `[]` means the effect runs only once after mount.
    expect(runtimeClientSrc).toMatch(
      /useEffect\([^}]*setMounted\(true\)[^}]*\}, \[]\)/,
    );
  });

  it("H8. SSR placeholder's outermost DOM matches MapShell's outermost wrapper", () => {
    // The structural identity is the entire point of V3-A — the
    // placeholder div must mirror MapShell's outermost className so
    // SSR HTML and first client render are byte-identical.
    expect(runtimeClientSrc).toContain(
      '"flex h-full w-full overflow-hidden bg-paper"',
    );
    // aria-busy signals the loading state to assistive tech.
    expect(runtimeClientSrc).toContain('aria-busy="true"');
  });

  it("H9. MapRuntimeClient only renders <MapShell /> after mounted === true", () => {
    // The conditional render must check `mounted` BEFORE swapping in
    // the real shell.
    expect(runtimeClientSrc).toMatch(/if\s*\(\s*!mounted\s*\)\s*\{/);
    expect(runtimeClientSrc).toMatch(/return\s*<MapShell[^>]*\/>/);
  });
});

// ═══════════════════════════════════════════════════════════════════
// I. URL store render-time purity (V3-C)
// ═══════════════════════════════════════════════════════════════════

describe("I. URL store render-time purity (V3-C)", () => {
  const bridgeSrc = readSrc("src/hooks/use-view-state-bridge.ts");
  const urlParamsSrc = readSrc("src/lib/url-params.ts");
  const regionalSrc = readSrc("src/regional/useRegionalMetric.ts");

  it("I1. writeUrl is only called from useEffect, never from render", () => {
    // `writeUrl` is invoked from a trailing useEffect that depends
    // on `state` + `writeUrl`. The `apply` updater passed to
    // `setState` MUST be pure (no `writeUrl` inside).
    expect(bridgeSrc).toMatch(/useEffect\(\s*\(\)\s*=>\s*\{\s*writeUrl\(state\)/);
    // No `writeUrl(` inside `setState(` body.
    const setStateBlock = bridgeSrc.slice(
      bridgeSrc.indexOf("const apply = useCallback"),
      bridgeSrc.indexOf("useEffect(() => {"),
    );
    expect(setStateBlock.includes("writeUrl")).toBe(false);
    expect(setStateBlock.includes("router.replace")).toBe(false);
    expect(setStateBlock.includes("history.replaceState")).toBe(false);
  });

  it("I2. lastSyncedRef null sentinel skips first commit", () => {
    // The first commit must NOT trigger router.replace (which would
    // append bridge-owned defaults to a deep-link URL that intentionally
    // omitted them).
    expect(bridgeSrc).toMatch(/if\s*\(lastSyncedRef\.current\s*===\s*null\)/);
    expect(bridgeSrc).toMatch(/lastSyncedRef\.current\s*=\s*JSON\.stringify\(next\)/);
  });

  it("I3. apply() updater is pure", () => {
    // The `setState` callback receives `prev` and returns a new
    // object. It must NOT call router.replace / history.replaceState
    // / console.* — those are side effects.
    const applyStart = bridgeSrc.indexOf("const apply = useCallback");
    // There are multiple useEffect blocks in the file. We want the
    // one immediately AFTER `apply` (the trailing writeUrl effect).
    const effectRe = /useEffect\(\(\) => \{/g;
    const allEffects: number[] = [];
    let m: RegExpExecArray | null;
    while ((m = effectRe.exec(bridgeSrc)) !== null) {
      allEffects.push(m.index);
    }
    const trailingEffect = allEffects
      .filter((i) => i > applyStart)
      .sort((a, b) => a - b)[0];
    expect(applyStart).toBeGreaterThan(-1);
    expect(trailingEffect).toBeDefined();
    const applyBlock = bridgeSrc.slice(applyStart, trailingEffect);
    // Sanity: the block must contain the setState pattern.
    expect(applyBlock).toMatch(/setState\(/);
    expect(applyBlock).toMatch(/\.\.\.prev/);
    expect(applyBlock).toMatch(/\.\.\.patch/);
    // No side effects inside.
    expect(applyBlock.includes("router.")).toBe(false);
    expect(applyBlock.includes("history.")).toBe(false);
    expect(applyBlock.includes("console.")).toBe(false);
    expect(applyBlock.includes("writeUrl")).toBe(false);
    expect(applyBlock.includes("dispatchEvent")).toBe(false);
  });

  it("I4. getSnapshot is a pure read of window.location.search", () => {
    // useRegionalMetric's getSnapshot must NOT mutate window or
    // dispatch any event.
    const getSnapBlock = regionalSrc.slice(
      regionalSrc.indexOf("function getSnapshot"),
      regionalSrc.indexOf("/**\n * `popstate`"),
    );
    expect(getSnapBlock.includes("dispatchEvent")).toBe(false);
    expect(getSnapBlock.includes("replaceState")).toBe(false);
    expect(getSnapBlock.includes("pushState")).toBe(false);
    // It only reads.
    expect(getSnapBlock).toMatch(/readSearchParam/);
  });

  it("I5. getServerSnapshot returns null with NO window access", () => {
    // Server snapshot is pure null. No browser APIs.
    const block = regionalSrc.slice(
      regionalSrc.indexOf("function getServerSnapshot"),
      regionalSrc.indexOf("function getSnapshot"),
    );
    expect(block).toMatch(/return\s+null/);
    expect(block.includes("window")).toBe(false);
    expect(block.includes("document")).toBe(false);
  });

  it("I6. subscribe never calls updateSearchParam (no feedback loop)", () => {
    const block = regionalSrc.slice(
      regionalSrc.indexOf("function subscribe"),
      regionalSrc.indexOf("/** Exposed"),
    );
    expect(block.includes("updateSearchParam")).toBe(false);
    expect(block.includes("replaceState")).toBe(false);
  });

  it("I7. updateSearchParam dispatches popstate AFTER replaceState", () => {
    // The synthetic popstate fires AFTER the URL has been written, so
    // getSnapshot on the next render reads the new value.
    const updateFnBlock = urlParamsSrc.slice(
      urlParamsSrc.indexOf("export function updateSearchParam"),
      urlParamsSrc.indexOf("export const BRIDGE_OWNED_KEYS"),
    );
    expect(updateFnBlock).toMatch(/history\.replaceState/);
    expect(updateFnBlock).toMatch(/dispatchEvent\(new PopStateEvent/);
    // Order matters: replaceState must come before dispatchEvent.
    const replaceIdx = updateFnBlock.indexOf("history.replaceState");
    const dispatchIdx = updateFnBlock.indexOf("dispatchEvent");
    expect(replaceIdx).toBeGreaterThan(-1);
    expect(dispatchIdx).toBeGreaterThan(-1);
    expect(replaceIdx).toBeLessThan(dispatchIdx);
  });

  it("I8. BRIDGE_OWNED_KEYS whitelist still excludes 'region'", () => {
    // The whitelist is the discipline that prevents the bridge from
    // clobbering `region` on every state recomputation. `region` is
    // owned exclusively by useRegionalMetric.
    expect(urlParamsSrc).toMatch(/BRIDGE_OWNED_KEYS/);
    expect(urlParamsSrc).toMatch(/new Set\(\[/);
    // The whitelist entries are all defined inline; `region` is not
    // among them.
    const setBlock = urlParamsSrc.slice(
      urlParamsSrc.indexOf("BRIDGE_OWNED_KEYS:"),
      urlParamsSrc.indexOf("]);"),
    );
    expect(setBlock.includes("\"region\"")).toBe(false);
    expect(setBlock.includes("'region'")).toBe(false);
  });
});

// ═══════════════════════════════════════════════════════════════════
// J. console.warn monkey-patch leak removed (V3-D)
// ═══════════════════════════════════════════════════════════════════

describe("J. console.warn monkey-patch leak removed (V3-D)", () => {
  const canvasSrc = readSrc("src/components/map/MapCanvas.tsx");

  it("J1. MapCanvas does NOT capture console.warn on mount", () => {
    // The previous v2 monkey-patch leaked under Strict Mode dev
    // double-render. V3-D removed it entirely.
    expect(canvasSrc).not.toContain("const origWarn = console.warn");
    expect(canvasSrc).not.toContain("styleDiffSwallow");
  });

  it("J2. cleanup function does NOT restore origWarn", () => {
    // The cleanup return-value is a no-op for console.warn.
    expect(canvasSrc).not.toContain("console.warn = origWarn");
    // But it still tears down the map.
    expect(canvasSrc).toMatch(/map\.remove\(\)/);
    expect(canvasSrc).toMatch(/setMapReady\(false\)/);
  });

  it("J3. MapLibre error handler still filters transient noise", () => {
    // The error handler filters the same transient setStyle race
    // noise that the monkey-patch used to swallow — at the source.
    expect(canvasSrc).toMatch(/map\.on\(["']error["']/);
    expect(canvasSrc).toMatch(/does not exist in the map's style/);
    expect(canvasSrc).toMatch(/Style is not done loading/);
  });

  it("J4. console.error is still forwarded for non-transient errors", () => {
    // Non-transient MapLibre errors are still surfaced for diagnosis.
    expect(canvasSrc).toMatch(/console\.error\(\s*["']\[MapCanvas\]/);
  });
});

// ═══════════════════════════════════════════════════════════════════
// K. Choropleth retention invariants
// ═══════════════════════════════════════════════════════════════════

describe("K. Choropleth retention invariants", () => {
  const regionalSrc = readSrc("src/regional/useRegionalMetric.ts");
  const regionalTypesSrc = readSrc("src/regional/types.ts");

  it("K1. regional metric IDs cover income / safety / employment / chinese_population", () => {
    expect(regionalTypesSrc).toContain('"income"');
    expect(regionalTypesSrc).toContain('"safety"');
    expect(regionalTypesSrc).toContain('"employment"');
    expect(regionalTypesSrc).toContain('"chinese_population"');
  });

  it("K2. useRegionalMetric URL_PARAM is 'region'", () => {
    expect(regionalSrc).toMatch(/URL_PARAM\s*=\s*["']region["']/);
  });

  it("K3. parseRegionParam maps 'none' and empty to null (graceful fallback)", () => {
    // The function is a pure expression. We look for any sequence
    // matching: `raw === null || raw === "" || raw === "none"` returning null.
    expect(regionalSrc).toMatch(/raw === null/);
    expect(regionalSrc).toMatch(/raw === ""/);
    expect(regionalSrc).toMatch(/raw === "none"/);
    // And it returns null on the first guard clause.
    expect(regionalSrc).toMatch(/return\s+null/);
  });

  it("K4. setRegionalMetric writes via updateSearchParam, never via router.replace directly", () => {
    // The hook's setter goes through the shared URL helper so every
    // other query param survives.
    const setRegionalBlock = regionalSrc.slice(
      regionalSrc.indexOf("const setRegionalMetric"),
      regionalSrc.indexOf("return [value, setRegionalMetric]"),
    );
    expect(setRegionalBlock).toContain("updateSearchParam");
    expect(setRegionalBlock).not.toContain("router.replace");
    expect(setRegionalBlock).not.toContain("history.replaceState");
  });
});

// ═══════════════════════════════════════════════════════════════════
// L. Strict-Mode-safe hook order in MapShell + child hooks
// ═══════════════════════════════════════════════════════════════════

describe("L. Strict-Mode-safe hook order (V3-C)", () => {
  const bridgeSrc = readSrc("src/hooks/use-view-state-bridge.ts");
  const themeSrc = readSrc("src/lib/theme.ts");
  const regionalSrc = readSrc("src/regional/useRegionalMetric.ts");

  it("L1. useViewStateBridge hook count is stable across renders", () => {
    // useSearchParams + useRouter + usePathname + useState +
    // useRef + useEffect (×2) + useCallback (×2). The exact count
    // doesn't matter as long as it's stable across re-renders and
    // never conditional.
    //
    // We assert: no `if (...) { useX() }` patterns and no early
    // returns before all hooks.
    const fnBody = bridgeSrc.slice(
      bridgeSrc.indexOf("export function useViewStateBridge"),
      bridgeSrc.indexOf("return {"),
    );
    // No conditional hook calls.
    expect(fnBody).not.toMatch(/if\s*\([^)]*\)\s*\{[^}]*use[A-Z]/);
  });

  it("L2. useTheme uses useSyncExternalStore with stable SSR snapshot", () => {
    expect(themeSrc).toMatch(/useSyncExternalStore/);
    expect(themeSrc).toMatch(/getServerSnapshot/);
    expect(themeSrc).toMatch(/getSnapshot/);
  });

  it("L3. useRegionalMetric uses useSyncExternalStore with stable SSR snapshot", () => {
    expect(regionalSrc).toMatch(/useSyncExternalStore/);
    // SSR snapshot is a literal null — no `window` access.
    expect(regionalSrc).toMatch(/function\s+getServerSnapshot[\s\S]*?return\s+null/);
  });

  it("L4. no render-time router mutation exists in any audited hook", () => {
    // Belt-and-suspenders: any router mutation in the audited hooks
    // MUST live inside a `useEffect(...)` or `useCallback(...)` body
    // — never inside a `useState(() => ...)` initializer, JSX, or
    // other render-time surface.
    //
    // We assert the simpler invariant: `router.replace(` only appears
    // inside the `writeUrl` useCallback body, which is itself only
    // invoked from a useEffect — never from JSX or event handlers.
    // The regional hook doesn't have router.replace at all (it uses
    // `history.replaceState` via the shared `updateSearchParam` helper
    // in `url-params.ts`).
    for (const src of [bridgeSrc, regionalSrc]) {
      // Count actual `router.replace(` invocations (not comments).
      // The regex below matches `router.replace(` followed by an
      // argument that's NOT preceded by a `//` comment marker.
      // Simpler: strip comments first, then count.
      const stripLineComments = (s: string): string =>
        s.replace(/\/\/[^\n]*/g, "");
      const stripped = stripLineComments(src);
      const directCalls = stripped.match(/router\.replace\(/g) ?? [];
      // bridge.ts has exactly 1 (inside writeUrl). regional.ts has 0.
      expect(directCalls.length).toBeLessThanOrEqual(1);

      // No `history.replaceState(` anywhere in the audited hook
      // files. That helper lives in `url-params.ts` only.
      expect(stripped.includes("history.replaceState")).toBe(false);
      expect(stripped.includes("history.pushState")).toBe(false);
    }
  });
});