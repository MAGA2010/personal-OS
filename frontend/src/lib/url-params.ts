// PathOS Stage 7B-A.1 Closing Patch v2 — Hydration-safe URL param helpers
//
// Why this exists
// ────────────────
// The map page has two competing URL writers:
//   1. `useViewStateBridge` writes `metric`, `u`, `r`, `mode`, `compare` via
//      `router.replace()` and intentionally drops everything else.
//   2. `useRegionalMetric` writes `region` via `history.pushState`.
// Both fire on the same render pass; whoever runs second wins. Before
// this patch the bridge ran second and erased `region`, so a deep-link
// like `/map?region=income` silently degraded to `/map?mode=student`
// (or `/map` if parent-mode-available was already known) on hydration.
//
// The fix below provides a single shared helper that writes a single
// query param while preserving every other param. Both the bridge and
// the regional hook funnel through it.
//
// Constraints
// ───────────
//   • Must be a no-op on the server (no `window` access).
//   • Must preserve the path, hash, and all other query params.
//   • Must NOT trigger a Next.js route segment re-render (use
//     `history.replaceState`, never `router.replace` or `router.push`).
//   • Must dispatch a synthetic `popstate` so `useSyncExternalStore`
//     listeners re-read the URL. (Native `replaceState` does not fire
//     `popstate`.)
//   • Must NOT create a new history entry (we want replace, not push,
//     so back/forward keeps the meaningful coarser-grained entry).
//
// Why replaceState, not pushState
// ───────────────────────────────
// The regional metric toggles rapidly while the user pans the map.
// Each toggle used to push a history entry, so Back became useless.
// replaceState updates the current entry in place. Back then returns
// to the page before /map — which is the right UX.

/**
 * Read a single query param from the current URL.
 *
 * Returns `null` on the server (so SSR renders are deterministic).
 * Returns `null` when the key is not present.
 */
export function readSearchParam(key: string): string | null {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get(key);
}

/**
 * Read all query params from the current URL as a plain object.
 *
 * Returns `{}` on the server. Iterating order matches URL declaration
 * order, which is what the search params dictionary preserves.
 */
export function readAllSearchParams(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const out: Record<string, string> = {};
  const params = new URLSearchParams(window.location.search);
  params.forEach((value, key) => {
    out[key] = value;
  });
  return out;
}

/**
 * Update a single query param, preserving all other params, the path,
 * and the hash. Uses `history.replaceState` so we do NOT push a new
 * history entry. Dispatches a synthetic `popstate` so external-store
 * subscribers (e.g. `useRegionalMetric`) re-read the URL.
 *
 * Pass `null` or `""` to delete the key.
 */
export function updateSearchParam(key: string, value: string | null): void {
  if (typeof window === "undefined") return;
  if (!key) return;

  const url = new URL(window.location.href);
  if (value === null || value === "") {
    url.searchParams.delete(key);
  } else {
    url.searchParams.set(key, value);
  }

  const next = url.pathname + (url.search ? url.search : "") + url.hash;
  // Preserve the current history.state so any consumers that read it
  // (e.g. Next.js' own router) keep their handle. We intentionally use
  // replaceState — not pushState — because rapid metric toggles should
  // not pollute the back/forward stack.
  window.history.replaceState(window.history.state, "", next);
  // `replaceState` does not fire `popstate`. We dispatch one manually
  // so `useSyncExternalStore` subscribers re-read the URL. We use
  // `PopStateEvent` with no state delta — listeners that compare
  // against the previous URL (e.g. via `readSearchParam`) will see
  // the new value and re-render.
  window.dispatchEvent(new PopStateEvent("popstate"));
}

/**
 * The set of query keys that `useViewStateBridge` owns and serializes.
 *
 * Any other key (notably `region`) is treated as foreign and preserved
 * across `useViewStateBridge` writes. Used by both the bridge (to skip
 * writes when nothing in this whitelist changed) and tests (to assert
 * preservation invariants).
 */
export const BRIDGE_OWNED_KEYS: ReadonlySet<string> = new Set([
  "metric",
  "u",
  "r",
  "mode",
  "compare",
]);

/** True if the given key is owned by `useViewStateBridge`. */
export function isBridgeOwnedKey(key: string): boolean {
  return BRIDGE_OWNED_KEYS.has(key);
}