"use client";

// Stage 7B-A.3.1 — Selected region URL sync.
//
// Two-way sync between `selectedRegionFips` (state) and the `?state=`
// URL search param. Owned by MapShell so the URL stays in sync as the
// user clicks states, presses Back/Forward, or refreshes.
//
// Whitelist behavior:
//   - Selecting a new state REPLACES the `state` param (no duplicates).
//   - Clearing selection REMOVES the `state` param (region kept).
//   - Region / metric / mode params are foreign keys — preserved.

import { useCallback, useEffect, useRef } from "react";
import { normalizeStateFips } from "./normalizeStateFips";
import { readSearchParam, updateSearchParam } from "@/lib/url-params";

const STATE_PARAM = "state";

export interface UseSelectedRegionUrlResult {
  /** The currently selected state FIPS (canonical 2-digit string), or null. */
  selectedRegionFips: string | null;
  /** Set the selected region. Pass null to clear. */
  setSelectedRegionFips: (next: string | null) => void;
  /** Force-read from URL once (e.g. on hydration sync). */
  syncFromUrl: () => void;
}

/**
 * Two-way URL sync for the selected state. The hook:
 *   - On mount: reads `?state=` once and reports the initial value via
 *     `syncFromUrl` (called by the parent after hydration).
 *   - On `setSelectedRegionFips` change: writes only the `state` key
 *     through the shared live-URL helper. Foreign keys (`region`,
 *     `metric`, etc.) are preserved even when controls update rapidly.
 *   - On popstate: re-reads `?state=` and reports via a ref callback.
 */
export function useSelectedRegionUrl(
  onExternalChange: (fips: string | null) => void,
): UseSelectedRegionUrlResult {
  const lastWrittenRef = useRef<string | null>(null);
  // We mirror the current selected into this ref so the writeUrl
  // closure can read the latest without rebuilding.
  const currentRef = useRef<string | null>(null);

  const readFromUrl = useCallback((): string | null => {
    return normalizeStateFips(readSearchParam(STATE_PARAM));
  }, []);

  const syncFromUrl = useCallback(() => {
    const next = readFromUrl();
    if (next !== currentRef.current) {
      currentRef.current = next;
      lastWrittenRef.current = next;
      onExternalChange(next);
    }
  }, [readFromUrl, onExternalChange]);

  const setSelectedRegionFips = useCallback(
    (next: string | null) => {
      const normalized = next === null ? null : normalizeStateFips(next);
      currentRef.current = normalized;
      // Keep the rendered selection in lock-step with the URL write. Next's
      // searchParams update is asynchronous, so relying on a later render left
      // the map outline/sidebar stale after toolbar-driven selection.
      onExternalChange(normalized);
      if (normalized === lastWrittenRef.current) return;
      lastWrittenRef.current = normalized;
      updateSearchParam(STATE_PARAM, normalized);
    },
    [onExternalChange],
  );

  // popstate: browser Back/Forward updates the URL → re-read.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const onPop = () => {
      const next = readFromUrl();
      if (next !== currentRef.current) {
        currentRef.current = next;
        lastWrittenRef.current = next;
        onExternalChange(next);
      }
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [readFromUrl, onExternalChange]);

  return {
    selectedRegionFips: currentRef.current,
    setSelectedRegionFips,
    syncFromUrl,
  };
}
