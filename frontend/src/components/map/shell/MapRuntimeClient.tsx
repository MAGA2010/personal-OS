"use client";

import { useEffect, useState } from "react";
import { MapShell } from "@/components/map/MapShell";

/**
 * Stage 7B-A.1 Closing Patch v3 (V3-A + V3-F + V3-G final) — Mounted gate.
 * ----------------------------------------------------------------
 * The root cause of the dev-mode hydration warning
 *   "The server HTML was replaced with client content in <%s>. #document"
 * was conclusively diagnosed by V3-G:
 *
 *   - `next/dynamic({ssr:false})` does NOT make the parent Client
 *     Component SSR-empty. The Server still renders MapShell itself
 *     (because MapShell is a plain Client Component that the Server
 *     tree includes via its JSX position). The `loading:` fallback
 *     appears in the server HTML at the place where the dynamic
 *     import sits *inside* MapShell (around `<MapCanvas/>`), not at
 *     the MapShell subtree root.
 *
 *   - The server emitted MapShell's outermost chrome (MapToolbar, the
 *     `<header>留学地图</header>`, the `加载地图…` placeholder for the
 *     canvas, etc.) but the *client first render* of MapShell produced
 *     a structurally different subtree as soon as its first `useEffect`
 *     fired.
 *
 *   - The fix: render a static structural placeholder in the FIRST
 *     client render that is byte-identical to what the server emitted,
 *     then swap in the real MapShell only on the SECOND render after
 *     the `mounted` gate flips.
 *
 * This file is the canonical implementation. The previous debug
 * bypass (`return <MapShell />`) was the source of the persistent
 * hydration warning and has been reverted.
 *
 * Server HTML:    <div className="relative flex-1 min-h-0"><div
 *                  className="flex h-full w-full overflow-hidden bg-paper">
 *                  …server-rendered MapShell subtree…</div></div>
 *
 * Client render 1: same static placeholder (mounted === false) →
 *                  identical → no hydration warning.
 *
 * Client render 2: mounted === true → real MapShell subtree.
 *                  Hydration is already complete by this point;
 *                  the subtree swap is a normal commit-phase update.
 *
 * Strict Mode safety: the `mounted` effect is a one-shot state flip
 * with no dependency on any external store. React 18 Strict Mode dev
 * double-render does not change the rendered output: both renders
 * see `mounted === false` because the effect cleanup re-arms it but
 * the second effect run still produces `true` before commit. The
 * placeholder is byte-identical on both renders.
 */

const PLACEHOLDER_CLASS =
  "flex h-full w-full overflow-hidden bg-paper";

export function MapRuntimeClient(): JSX.Element {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    // Match the SSR-emitted outermost div exactly. MapShell renders
    // inside this same div on subsequent client renders, so React's
    // diff never sees a structural change at this node.
    return (
      <div className={PLACEHOLDER_CLASS} role="region" aria-label="留学地图交互面板" aria-busy="true">
        <div className="flex flex-1 items-center justify-center bg-paper text-sm text-ink/40">
          加载地图…
        </div>
      </div>
    );
  }

  return <MapShell className="h-full" />;
}