"use client";

// PathOS Stage 7B-A.1 Closing Patch v2 — Regional Metric Single Source of Truth
//
// All consumers of the regional heatmap metric MUST read from a single
// state value (`activeRegionalMetric`). This module is the only place
// that owns that state. URL query is the canonical persistent form;
// the in-memory value is derived from URL via `useRegionalMetric()`
// and written back via `setRegionalMetric()`. Invalid query values
// fall back to `null` (no regional heatmap shown).
//
// Allowed values:
//   - null
//   - "income"
//   - "safety"
//   - "employment"
//   - "chinese_population"
//
// The legacy `cost` metric (留学成本) is intentionally NOT a regional
// metric — it is city-level only and lives outside this hook.
//
// Closing Patch v2 changes
// ────────────────────────
// The previous version of this hook used a `useState(() => …)`
// initializer that read `window.location.search` on the client and
// returned `null` on the server. That produced a hydration mismatch in
// `RegionalLegend` (C2 in the Re-Gate report).
//
// This version uses `useSyncExternalStore` with three explicit
// snapshots:
//   - `getServerSnapshot` always returns `null`. SSR is deterministic.
//   - `getSnapshot` reads `window.location.search` on the client. It's
//     stable until the next `popstate` (dispatched manually by
//     `updateSearchParam` after every write).
//   - `subscribe` listens for `popstate` on `window`.
// React's `useSyncExternalStore` guarantees that the first client
// render produces the same value as the SSR render (`null`), then
// fires a `useEffect`-driven re-render with the real URL value, which
// is the standard hydration-safe pattern.

import { useCallback, useSyncExternalStore } from "react";
import {
  REGIONAL_METRIC_IDS,
  type RegionalMetricId,
} from "@/regional/types";
import { updateSearchParam, readSearchParam } from "@/lib/url-params";

const URL_PARAM = "region";
const VALID_VALUES: ReadonlyArray<RegionalMetricId | null> = [
  null,
  ...REGIONAL_METRIC_IDS,
];

export type SetRegionalMetric = (next: RegionalMetricId | null) => void;

/** Returns null when the URL value is not a valid RegionalMetricId. */
export function parseRegionParam(raw: string | null): RegionalMetricId | null {
  if (raw === null || raw === "" || raw === "none") return null;
  if ((REGIONAL_METRIC_IDS as readonly string[]).includes(raw)) {
    return raw as RegionalMetricId;
  }
  return null;
}

export function serialiseRegionParam(value: RegionalMetricId | null): string {
  return value === null ? "none" : value;
}

/**
 * `useRegionalMetric` — single-source-of-truth hook for the active
 * regional metric. Reads from the URL on mount + on `popstate`, writes
 * back via `updateSearchParam` (which preserves all other URL params).
 *
 * All consumers (RegionalLayerControl, RegionalStateLayer,
 * RegionalLegend, RegionalHoverTooltip, MapToolbar, SourcePanel) MUST
 * call this hook.
 *
 * Browser back / forward MUST round-trip through the same URL key —
 * which is guaranteed because `popstate` is the only subscription
 * trigger and `updateSearchParam` dispatches a synthetic `popstate`
 * after every write.
 */
export function useRegionalMetric(): readonly [
  RegionalMetricId | null,
  SetRegionalMetric,
] {
  // SSR snapshot: always null. The first client render returns null
  // too (because useSyncExternalStore demands the server and first-
  // client snapshots match). After mount, React calls getSnapshot
  // again — this time on the client — and re-renders with the real
  // value. This is the canonical hydration-safe pattern.
  const value = useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot,
  );

  const setRegionalMetric: SetRegionalMetric = useCallback((next) => {
    if (!VALID_VALUES.includes(next)) {
      // invalid → fall back to null; never silently set a forbidden value
      next = null;
    }
    // Route through the shared helper so every other query param
    // (mode=student, metric=, u=, r=, compare=…) is preserved. The
    // helper dispatches a synthetic popstate after the replaceState,
    // which causes getSnapshot to return the new value on the next
    // render.
    updateSearchParam(URL_PARAM, serialiseRegionParam(next));
  }, []);

  return [value, setRegionalMetric] as const;
}

/**
 * SSR snapshot — always `null`. Makes the SSR markup deterministic
 * regardless of URL.
 */
function getServerSnapshot(): RegionalMetricId | null {
  return null;
}

/**
 * Client snapshot — re-reads `?region=` on every call. The store is
 * stable between `popstate` events (the search string only changes on
 * popstate), so React's identity comparison dedupes renders cheaply.
 */
function getSnapshot(): RegionalMetricId | null {
  return parseRegionParam(readSearchParam(URL_PARAM));
}

/**
 * `popstate` listener. Returns the unsubscribe function. The
 * signature must match React's `useSyncExternalStore` subscribe
 * contract: `(onChange) => () => void`. `onChange` takes no args.
 */
function subscribe(onChange: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("popstate", onChange);
  return () => window.removeEventListener("popstate", onChange);
}

/** Exposed for tests / consumers that need to read the URL param key. */
export const REGIONAL_URL_PARAM = URL_PARAM;
export const REGIONAL_VALID_VALUES: ReadonlyArray<RegionalMetricId | null> =
  VALID_VALUES;