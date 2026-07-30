"use client";

// View state → URL bridge.
//
// Why:
//   - The map page is the primary landing route (/map). URL state lets
//     users share / bookmark a configured view (metric + selection +
//     compare tray).
//   - We deliberately use shallow updates (router.replace + scroll:false)
//     so the URL stays in sync without remounting the MapShell tree.
//
// Constraints:
//   - Initial state MUST come from `useSearchParams()` so server-rendered
//     HTML can hydrate with the right active metric. This keeps
//     shareable links meaningful.
//   - Any unknown / malformed param value is ignored silently — we
//     never crash the page because a number was passed for a metric id.
//   - compare tray (multi-id) is encoded as repeated `compare=foo` keys
//     rather than comma-separated so we don't have to escape state codes.
//
// Metric key unification (gate-bloker repair #GB-P0-5):
//   The set of valid metric IDs is the canonical list exported by
//   `@/config/metrics.config.ts`. TOEFL/SAT/admission_rate are
//   school-level attributes and intentionally NOT valid choropleth
//   metrics; an illegal `metric=` value falls back to the default and
//   is silently rewritten in the URL so a stale link becomes valid.

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { MetricId } from "@/lib/types";
import type { DatasetManifest } from "@/domain/dataset";
import { METRIC_DEFINITIONS } from "@/config/metrics.config";
import {
  BRIDGE_OWNED_KEYS,
  isBridgeOwnedKey,
  readAllSearchParams,
} from "@/lib/url-params";

export interface UrlBridgeState {
  activeMetricId: MetricId;
  selectedUniversityId: string | null;
  selectedRegionFips: string | null;
  compareIds: string[];
  viewMode: "parent" | "student";
  /**
   * Whether the user (or the URL they visited) explicitly chose a view
   * mode. `false` means the bridge resolved viewMode via its
   * manifest-driven default (e.g. parent→student downgrade because
   * the active manifest has `parent_mode` in `disabledFeatures`). The
   * bridge must NEVER write `mode=` back to the URL when this is
   * `false` — writing would silently mutate the user's deep-link.
   *
   * Only `setViewMode(...)` (an explicit user interaction) flips this
   * to `true`.
   */
  viewModeExplicit: boolean;
}

// Single source of truth for valid metric IDs. Derived from the same
// config the UI uses so we cannot drift from what `MetricTabs` shows.
const VALID_METRICS: ReadonlySet<string> = new Set(
  Object.keys(METRIC_DEFINITIONS) as MetricId[],
);
const DEFAULT_METRIC_ID: MetricId = "income";
const VALID_VIEW_MODES = new Set(["parent", "student"]);

export function isParentModeAvailable(
  manifest: DatasetManifest | null | undefined,
): boolean {
  if (!manifest) return false;
  if (manifest.disabledFeatures?.includes("parent_mode")) return false;
  if (manifest.enabledFeatures) {
    return manifest.enabledFeatures.includes("parent_mode");
  }
  // Legacy fixture manifests predate feature-readiness. Fixture mode
  // remains explicitly usable unless its own manifest disables parent.
  return true;
}

export function resolveAllowedViewMode(
  requested: UrlBridgeState["viewMode"],
  parentModeAvailable: boolean,
): UrlBridgeState["viewMode"] {
  return requested === "parent" && !parentModeAvailable ? "student" : requested;
}

function readStateFromParams(
  params: URLSearchParams,
  parentModeAvailable = true,
): UrlBridgeState {
  const metric = params.get("metric");
  const activeMetricId: MetricId =
    metric && VALID_METRICS.has(metric) ? (metric as MetricId) : DEFAULT_METRIC_ID;
  const selectedUniversityId = params.get("u");
  const selectedRegionFips = params.get("r");
  const compareIds = params.getAll("compare").filter((s) => s.length > 0);
  const viewModeRaw = params.get("mode");
  const requestedViewMode: "parent" | "student" =
    viewModeRaw && VALID_VIEW_MODES.has(viewModeRaw)
      ? (viewModeRaw as "parent" | "student")
      : "parent";
  const viewMode = resolveAllowedViewMode(
    requestedViewMode,
    parentModeAvailable,
  );
  // Closing Patch v2 (refined): only mark viewMode as "explicit" when
  // the URL actually carried a `mode=` key. A manifest-driven
  // parent→student downgrade (parent_mode disabled in the active
  // manifest) must NOT cause `mode=student` to be appended to a URL
  // the user never asked to write. Without this gate, the Re-Gate's
  // H1 finding reproduces on every deep-link that omits `mode`.
  const viewModeExplicit = viewModeRaw !== null && VALID_VIEW_MODES.has(viewModeRaw);
  return {
    activeMetricId,
    selectedUniversityId,
    selectedRegionFips,
    compareIds,
    viewMode,
    viewModeExplicit,
  };
}

function buildOwnedSearchParams(state: Partial<UrlBridgeState>): URLSearchParams {
  const sp = new URLSearchParams();
  if (state.activeMetricId && state.activeMetricId !== DEFAULT_METRIC_ID) {
    sp.set("metric", state.activeMetricId);
  }
  if (state.selectedUniversityId) sp.set("u", state.selectedUniversityId);
  if (state.selectedRegionFips) sp.set("r", state.selectedRegionFips);
  // Closing Patch v2 (refined): only emit `mode=` when the user (or
  // their deep-link) explicitly named a view mode. The previous
  // condition `state.viewMode !== "parent"` would happily write
  // `mode=student` for a manifest-driven parent→student downgrade,
  // which is exactly what the Re-Gate flagged as H1.
  if (state.viewModeExplicit && state.viewMode) {
    sp.set("mode", state.viewMode);
  }
  if (state.compareIds && state.compareIds.length > 0) {
    for (const id of state.compareIds) sp.append("compare", id);
  }
  return sp;
}

/**
 * Read the current URL and produce the search string this bridge will
 * own. Foreign keys (anything outside `BRIDGE_OWNED_KEYS`) are
 * preserved verbatim.
 *
 * Why we don't just hand `buildOwnedSearchParams` to `URLSearchParams#toString`:
 * — that helper builds a *new* URLSearchParams from scratch, so it
 *   drops every key not in our whitelist. We need to merge instead.
 */
export function mergeOwnedSearchParams(
  state: Partial<UrlBridgeState>,
): URLSearchParams {
  const current =
    typeof window !== "undefined"
      ? new URLSearchParams(window.location.search)
      : new URLSearchParams();

  // 1. Drop every key we own — we'll re-add the up-to-date values below.
  for (const key of Array.from(BRIDGE_OWNED_KEYS)) {
    current.delete(key);
  }

  // 2. Re-add the values we own, computed from the current state.
  const owned = buildOwnedSearchParams(state);
  owned.forEach((value, key) => {
    current.append(key, value);
  });

  return current;
}

export interface UseViewStateBridgeResult {
  state: UrlBridgeState;
  setActiveMetric: (id: MetricId) => void;
  setSelectedUniversity: (id: string | null) => void;
  setSelectedRegion: (fips: string | null) => void;
  setCompareIds: (ids: string[]) => void;
  setViewMode: (mode: "parent" | "student") => void;
}

const MAX_COMPARE = 3;

function dedupeCap(ids: string[], cap = MAX_COMPARE): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const id of ids) {
    if (typeof id !== "string" || id.length === 0) continue;
    if (seen.has(id)) continue;
    seen.add(id);
    out.push(id);
    if (out.length >= cap) break;
  }
  return out;
}

export function useViewStateBridge({
  parentModeAvailable = true,
}: {
  parentModeAvailable?: boolean;
} = {}): UseViewStateBridgeResult {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const initial = readStateFromParams(
    new URLSearchParams(params?.toString() ?? ""),
    parentModeAvailable,
  );
  const [state, setState] = useState<UrlBridgeState>(initial);
  // Closing Patch v2 (refined): `firstWriteSkippedRef` is folded into
  // `lastSyncedRef` to avoid adding an extra `useRef` at the top of this
  // hook — a v2 interim added a separate `firstWriteRef` which created
  // a hook-order mismatch with the SSR snapshot (hook #N was `useEffect`
  // in one render and `useRef` in the next because the new ref shifted
  // every downstream hook index by +1). The merged ref starts as `null`
  // and once we've recorded the initial state in it, every subsequent
  // write runs through the normal flow.
  const lastSyncedRef = useRef<string | null>(null);

  // Re-sync state when search params change externally (e.g. back button).
  useEffect(() => {
    const next = readStateFromParams(
      new URLSearchParams(params?.toString() ?? ""),
      parentModeAvailable,
    );
    const serialized = JSON.stringify(next);
    if (serialized !== lastSyncedRef.current) {
      lastSyncedRef.current = serialized;
      setState(next);
    }
  }, [params, parentModeAvailable]);

  const writeUrl = useCallback(
    (next: UrlBridgeState) => {
      // Closing Patch v2 (refined): the first commit's URL write is
      // folded into `lastSyncedRef` initialisation rather than a
      // separate ref. Initial state is read from the URL via
      // `readStateFromParams`, so writing it back on the first commit
      // would append bridge-owned defaults (e.g. `mode=student`) to a
      // deep-link that intentionally omitted them. We record the
      // initial state once and let the URL stay as the user wrote it
      // until an explicit interaction triggers a real write.
      if (lastSyncedRef.current === null) {
        lastSyncedRef.current = JSON.stringify(next);
        return;
      }

      // Merge the bridge-owned values with every foreign key already
      // present in the URL. Foreign keys (notably `region`) survive
      // this write untouched.
      const sp = mergeOwnedSearchParams(next);
      const qs = sp.toString();

      // Skip redundant writes — if the resulting query string matches
      // what the URL already shows, do nothing. This prevents the
      // bridge from clobbering a foreign key on every state
      // recomputation even when nothing in the bridge-owned set
      // actually changed.
      if (typeof window !== "undefined") {
        const currentQs = window.location.search.replace(/^\?/, "");
        if (currentQs === qs) return;
      }

      lastSyncedRef.current = JSON.stringify(next);
      // Use `router.replace` for query-only changes. We pass
      // `scroll: false` so the map does not jump. This will trigger
      // a Next.js App Router shallow re-render of the segment which
      // is fine — the URL we set has the same pathname, so no
      // component remounts.
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router],
  );

  // Apply patches via a stable updater. We deliberately do NOT call
  // writeUrl() inside the setState updater function — React's setState
  // updater must be pure, and triggering router.replace() during render
  // produces "Cannot update a component (Router) while rendering a
  // different component (MapShell)" warnings and an infinite re-render
  // loop that crashes the MapShell subtree (so the MapCanvas is never
  // mounted). Instead we schedule the URL write into an effect that runs
  // after state commits.
  const apply = useCallback(
    (patch: Partial<UrlBridgeState>) => {
      setState((prev) => ({ ...prev, ...patch }));
    },
    [],
  );

  useEffect(() => {
    writeUrl(state);
  }, [state, writeUrl]);

  return {
    state,
    setActiveMetric: (id) => apply({ activeMetricId: id }),
    setSelectedUniversity: (id) => apply({ selectedUniversityId: id }),
    setSelectedRegion: (fips) => apply({ selectedRegionFips: fips }),
    setCompareIds: (ids) => apply({ compareIds: dedupeCap(ids) }),
    setViewMode: (mode) =>
      apply({
        viewMode: resolveAllowedViewMode(mode, parentModeAvailable),
        // Closing Patch v2 (refined): setViewMode is the only place
        // where the user explicitly chooses a view mode, so it is the
        // only place that flips `viewModeExplicit` to `true`. Without
        // this flip, the bridge would re-resolve mode=student from
        // manifest readiness and never re-emit mode= to the URL.
        viewModeExplicit: true,
      }),
  };
}

export const COMPARE_CAP = MAX_COMPARE;
