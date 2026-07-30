"use client";

// PathOS Stage 7R — State Choropleth Layer
//
// Renders a US state-level choropleth using `public/geography/us-states.topojson`
// as the geometry source and the four READY regional metrics from
// `@/regional/load` as the value source. The active metric drives fill
// color through the corresponding palette; missing values render in the
// palette's `missing` color.
//
// Behaviour:
//   • Inserts source "pathos-regional-states" + layers
//       - "pathos-regional-states-fill"
//       - "pathos-regional-states-line"
//     the first time the layer becomes active (no duplicate-source errors).
//   • Updates fill-color & feature-state on metric change.
//   • Exposes hover (sets `hover` feature-state) and click (notifies parent).
//   • Re-applies its layers after a theme switch (dark/light) so the colors
//     match the current theme.
//   • Sits BELOW the city choropleth & university POI layers (drawn first).
//
// Non-responsibilities:
//   • Loading the underlying GeoJSON (handled once by us via fetch).
//   • Switching basemap styles (parent handles via MapCanvas).

import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { feature } from "topojson-client";
import type { FeatureCollection, MultiPolygon, Polygon } from "geojson";

import { useMapContext } from "../MapCanvas";
import {
  REGIONAL_METRIC_IDS,
  type RegionalMetricId,
  type RegionalMetricRecord,
} from "@/regional/types";
import {
  getRegionalMetricRecords,
  getRegionalMetricDefinition,
} from "@/regional/load";
import { bucketFromNormalized, getPalette } from "@/regional/palettes";

const SRC_ID = "pathos-regional-states";
const FILL_LAYER = "pathos-regional-states-fill";
const LINE_LAYER = "pathos-regional-states-line";

const TOPO_URL = "/geography/us-states.topojson";

// Layer IDs the POI marker layer uses — used as the canonical
// insertion point when the city-drilldown stack isn't mounted. We
// prefer the POI layer over the (mostly absent) city layer because
// the POI marker layer is always present whenever the user is on the
// map page; the city layer is only mounted after `cityDrilldownEnabled`
// is flipped on. Inserting before the POI halo / points keeps the
// choropleth visually beneath every marker without depending on the
// optional city drilldown path.
const POI_HALO_ID = "pathos-universities-halo";
const POI_POINTS_ID = "pathos-universities-points";
const POI_LABELS_ID = "pathos-universities-labels";

interface Props {
  /** Which metric (if any) is currently active. `null` means layer is off. */
  activeMetricId: RegionalMetricId | null;
  /** Current theme mode used to pick the right palette stops. */
  themeMode: "light" | "dark";
  /** Notify parent when a state is hovered (passes FIPS, or null). */
  onHover?: (geoId: string | null, record: RegionalMetricRecord | null) => void;
  /** Notify parent when a state is clicked. */
  onClick?: (geoId: string, record: RegionalMetricRecord | null) => void;
  /** Notify parent that data loading status changed. */
  onStatus?: (status: "idle" | "loading" | "ready" | "error") => void;
}

let _cachedGeo: FeatureCollection<MultiPolygon | Polygon> | null = null;
let _cachePromise: Promise<FeatureCollection<MultiPolygon | Polygon>> | null = null;

function loadStateBoundaries(): Promise<FeatureCollection<MultiPolygon | Polygon>> {
  if (_cachedGeo) return Promise.resolve(_cachedGeo);
  if (_cachePromise) return _cachePromise;
  _cachePromise = fetch(TOPO_URL)
    .then((r) => {
      if (!r.ok) throw new Error(`Failed to fetch ${TOPO_URL}: HTTP ${r.status}`);
      return r.json();
    })
    .then((topology) => {
      const fc = feature(topology, topology.objects.states) as unknown as FeatureCollection<
        MultiPolygon | Polygon
      >;
      // Stage 7B-A.2 Phase 4 — Choropleth fill root cause fix.
      //
      // TopoJSON geometries carry their FIPS code at the FEATURE TOP
      // LEVEL (`feature.id === "01"`) — `topojson-client`'s `feature()`
      // preserves this top-level `id` rather than copying it into
      // `properties`. Without this normalisation, two things break:
      //
      //   1. The fill-color `match` expression (`["get", "id"]`) never
      //      matches any feature → every polygon falls through to the
      //      `palette.missing` branch → state interiors render
      //      uncolored. THIS was the visible "choropleth only shows
      //      borders" bug observed in the Phase 2 baseline screenshot.
      //
      //   2. The hover / click handlers read
      //      `(f.properties as { id?: string })?.id`, which is
      //      `undefined` for every feature. Hover state-set still
      //      runs (cursor changes to pointer because the layer's
      //      mousemove handler still fires on the layer itself) but
      //      no per-state highlighting or click payload is delivered.
      //
      // We normalise by mirroring the feature-level `id` into
      // `properties.id` so that BOTH the MapLibre expression
      // evaluator AND the JS handlers read from the same well-known
      // location. This keeps the choropleth layer's contract stable:
      // every downstream consumer reads `properties.id` and treats
      // it as a 2-digit FIPS string.
      const normalised: FeatureCollection<MultiPolygon | Polygon> = {
        ...fc,
        features: fc.features.map((f) => {
          const fips = (f as { id?: string | number }).id;
          const fipsStr =
            fips === undefined || fips === null
              ? ""
              : String(fips).padStart(2, "0");
          return {
            ...f,
            properties: { ...(f.properties ?? {}), id: fipsStr },
          };
        }),
      };
      _cachedGeo = normalised;
      return normalised;
    })
    .catch((err) => {
      _cachePromise = null;
      throw err;
    });
  return _cachePromise;
}

export function RegionalStateLayer({
  activeMetricId,
  themeMode,
  onHover,
  onClick,
  onStatus,
}: Props): null {
  const ctx = useMapContext();
  const map = ctx?.map ?? null;
  const mapReady = ctx?.mapReady ?? false;
  const [sourceAdded, setSourceAdded] = useState(false);
  const [dataLoaded, setDataLoaded] = useState(false);
  const recordsRef = useRef<RegionalMetricRecord[]>([]);

  const records = useMemo(() => {
    if (!activeMetricId) return [];
    return getRegionalMetricRecords(activeMetricId);
  }, [activeMetricId]);

  // Keep recordsRef current so handlers (added once) read latest data.
  useEffect(() => {
    recordsRef.current = records;
  }, [records]);

  const onStatusRef = useRef(onStatus);
  useEffect(() => {
    onStatusRef.current = onStatus;
  }, [onStatus]);

  // Load boundaries once — guarded by `style.load`.
  //
  // MapLibre throws "Style is not done loading" when addSource/addLayer
  // is called before the basemap style is loaded. The component mounts
  // immediately when the parent renders it, but the MapLibre `load`
  // event (which marks the basemap ready) fires asynchronously after
  // tile fetch + parse. We must therefore:
  //   1. Always check `isStyleLoaded()` before touching the map.
  //   2. If not loaded, register a one-time `style.load` handler that
  //      performs the same work.
  //   3. Remove the one-time listener on cleanup or unmount.
  //   4. Treat theme switches (parent calls `setStyle`) as a reload:
  //      MapLibre re-emits `style.load` after `setStyle` resolves, so
  //      the same one-time handler is safe to use as long as the
  //      previous map instance hasn't been removed.
  useEffect(() => {
    // Closing Patch v2: this effect now waits for BOTH `map` and
    // `mapReady`. The previous version fired as soon as `map` was
    // non-null, which meant it ran during the brief window where
    // MapLibre's `load` event had fired but our React-side
    // `mapReady` flag had not yet propagated. During that window,
    // `addSource()` was throwing "Style is not done loading" and the
    // try/catch was swallowing the failure silently — leaving the
    // regional layer's source/feature-state machinery in a broken
    // state for the lifetime of the page.
    //
    // `mapReady` is now flipped synchronously inside MapCanvas's
    // `map.on("load")` handler (no rAF indirection). When that flag
    // flips true, this effect re-runs, deferUntilStyleLoaded runs
    // immediately (style is already loaded by then), and the source
    // installs cleanly.
    if (!map || !mapReady) return;
    let cancelled = false;
    let cancelDefer: (() => void) | null = null;

    const installSourceAndLayers = (geo: FeatureCollection<MultiPolygon | Polygon>) => {
      if (cancelled) return;
      // Bail if the map was removed mid-flight (parent unmounted).
      const style = map.getStyle();
      if (!style) return;
      setDataLoaded(true);
      const existing = map.getSource(SRC_ID) as maplibregl.GeoJSONSource | undefined;
      if (!existing) {
        try {
          map.addSource(SRC_ID, { type: "geojson", data: geo });
        } catch (err) {
          // eslint-disable-next-line no-console
          console.error("[RegionalStateLayer] addSource failed:", err);
          onStatusRef.current?.("error");
          return;
        }
      } else {
        existing.setData(geo);
      }
      setSourceAdded(true);
      onStatusRef.current?.("ready");
    };

    onStatusRef.current?.("loading");

    loadStateBoundaries()
      .then((geo) => {
        if (cancelled) return;
        cancelDefer = deferUntilStyleLoaded(map, () => installSourceAndLayers(geo));
      })
      .catch((err) => {
        if (cancelled) return;
        // eslint-disable-next-line no-console
        console.error("[RegionalStateLayer] failed to load boundaries:", err);
        onStatusRef.current?.("error");
      });

    return () => {
      cancelled = true;
      if (cancelDefer) {
        cancelDefer();
        cancelDefer = null;
      }
    };
    // Closing Patch v2: `mapReady` is in the dep array so this effect
    // re-runs as soon as MapCanvas flips it true (synchronously inside
    // the load handler). Without `mapReady` in here, the effect would
    // never re-run after the initial mount and the source would never
    // install.
  }, [map, mapReady]);

  // Add / remove fill+line layers based on activeMetricId — guarded by
  // `style.load`. The source may already be present (added by the
  // first effect), but the layers must only be (re-)added once the
  // basemap style is ready, and the existing layers are removed by
  // `setStyle` on theme switch — so we re-install on every `style.load`
  // (one-shot per fire).
  useEffect(() => {
    // Closing Patch v2: explicit mapReady gate. Without this, the
    // effect can run after MapCanvas has re-mounted (e.g. on theme
    // swap + initial MapShell re-render) and try to addLayer against
    // a half-initialised map instance. `mapReady` is true only after
    // MapLibre's `load` event fires (now set synchronously inside the
    // load handler — see MapCanvas), which is the exact moment the
    // layer stack is stable.
    if (!map || !mapReady || !sourceAdded) {
      return;
    }

    const applyLayerState = () => {
      const style = map.getStyle();
      const hasFill = !!style?.layers?.some((l) => l.id === FILL_LAYER);
      const hasLine = !!style?.layers?.some((l) => l.id === LINE_LAYER);

      if (activeMetricId === null) {
        if (hasFill) {
          try { map.removeLayer(FILL_LAYER); } catch { /* already removed */ }
        }
        if (hasLine) {
          try { map.removeLayer(LINE_LAYER); } catch { /* already removed */ }
        }
        return;
      }

      const def = getRegionalMetricDefinition(activeMetricId);
      if (!def) return;
      const palette = getPalette(def.paletteId, themeMode);

      // build match expression for fill
      const fillExpr: maplibregl.ExpressionSpecification = [
        "match",
        ["get", "id"],
        ...records.flatMap((r) => {
          const fill = bucketFromNormalized(r.normalizedValue, palette);
          return [r.geoId, fill];
        }),
        palette.missing,
      ] as unknown as maplibregl.ExpressionSpecification;

      const lineColor = themeMode === "dark" ? "#5b6670" : "#7a8590";

      if (!hasFill) {
        // Re-check inside the closure: the basemap style may have been
        // swapped (setStyle) and the layer may have been removed by
        // MapLibre even though `hasFill` was true at the time of
        // `isStyleLoaded()` check. Defensive double-check via getStyle
        // covers both theme switches and React Strict-Mode double
        // invocation.
        const liveStyle = map.getStyle();
        const liveHasFill = !!liveStyle?.layers?.some((l) => l.id === FILL_LAYER);
        if (!liveHasFill) {
          const beforeId = pickInsertionId(map);
          try {
            map.addLayer(
              {
                id: FILL_LAYER,
                type: "fill",
                source: SRC_ID,
                paint: {
                  "fill-color": fillExpr,
                  "fill-opacity": [
                    "case",
                    ["boolean", ["feature-state", "selected"], false],
                    0.78,
                    ["boolean", ["feature-state", "hover"], false],
                    0.68,
                    themeMode === "dark" ? 0.48 : 0.62,
                  ],
                },
              },
              beforeId,
            );
          } catch (err) {
            // eslint-disable-next-line no-console
            console.error("[RegionalStateLayer] addLayer(fill) failed:", err);
          }
        } else {
          try { map.setPaintProperty(FILL_LAYER, "fill-color", fillExpr); } catch { /* style swapped mid-flight */ }
        }
      } else {
        try { map.setPaintProperty(FILL_LAYER, "fill-color", fillExpr); } catch { /* style swapped mid-flight */ }
      }

      if (!hasLine) {
        const liveStyle = map.getStyle();
        const liveHasLine = !!liveStyle?.layers?.some((l) => l.id === LINE_LAYER);
        if (!liveHasLine) {
          const beforeLineId = pickInsertionId(map);
          try {
            map.addLayer(
              {
                id: LINE_LAYER,
                type: "line",
                source: SRC_ID,
                paint: {
                  "line-color": lineColor,
                  "line-width": [
                    "case",
                    ["boolean", ["feature-state", "selected"], false],
                    2.4,
                    ["boolean", ["feature-state", "hover"], false],
                    1.6,
                    0.7,
                  ],
                  "line-opacity": themeMode === "dark" ? 0.75 : 0.6,
                },
              },
              beforeLineId,
            );
          } catch (err) {
            // eslint-disable-next-line no-console
            console.error("[RegionalStateLayer] addLayer(line) failed:", err);
          }
        } else {
          try { map.setPaintProperty(LINE_LAYER, "line-color", lineColor); } catch { /* style swapped mid-flight */ }
        }
      } else {
        try { map.setPaintProperty(LINE_LAYER, "line-color", lineColor); } catch { /* style swapped mid-flight */ }
      }
    };

    const cancel = deferUntilStyleLoaded(map, applyLayerState);
    return () => {
      try { cancel(); } catch { /* map may already be removed */ }
    };
  }, [map, mapReady, sourceAdded, activeMetricId, themeMode, records]);

  // Phase 4B fix — theme-switch re-install.
  //
  // When MapCanvas calls `map.setStyle(...)` to swap light↔dark, MapLibre
  // wipes EVERY layer and source we own. The dep array on the layer-add
  // effect above includes `themeMode`, but the source-install effect
  // does NOT — so after `setStyle` the source is gone and the layer-add
  // effect's `getSource(SRC_ID)` guard fails. The visible result is:
  // the choropleth goes blank and stays blank.
  //
  // Fix: register a `style.load` listener on the map that runs the same
  // `applyLayerState` logic after every style swap. MapLibre emits
  // `style.load` once the new style has finished parsing. We use this
  // as a trigger to re-add the source AND the fill/line layers.
  //
  // This effect is independent of the layer-add effect above (which
  // handles metric changes). They cooperate: the metric-change effect
  // runs on `activeMetricId` / `records` changes; this one runs on
  // `style.load` (i.e. theme swaps). Both call into the same
  // `applyLayerState` closure pattern via `deferUntilStyleLoaded`.
  useEffect(() => {
    if (!map || !mapReady || !sourceAdded || !activeMetricId) return;

    const onStyleLoad = () => {
      // Source was wiped by setStyle — re-install before re-adding
      // the layers. The cached _cachedGeo promise is still valid
      // (boundaries don't change between theme swaps).
      loadStateBoundaries()
        .then((geo) => {
          try {
            if (!map.getSource(SRC_ID)) {
              map.addSource(SRC_ID, { type: "geojson", data: geo });
            } else {
              (map.getSource(SRC_ID) as maplibregl.GeoJSONSource).setData(geo);
            }
          } catch (err) {
            // eslint-disable-next-line no-console
            console.error("[RegionalStateLayer] addSource on style.load failed:", err);
          }
          // Now re-install the layers via the same closure as the
          // metric-change effect. We inline the body here because the
          // outer closure (applyLayerState) is not in scope.
          const def = getRegionalMetricDefinition(activeMetricId);
          if (!def) return;
          const palette = getPalette(def.paletteId, themeMode);
          const fillExpr: maplibregl.ExpressionSpecification = [
            "match",
            ["get", "id"],
            ...records.flatMap((r) => {
              const fill = bucketFromNormalized(r.normalizedValue, palette);
              return [r.geoId, fill];
            }),
            palette.missing,
          ] as unknown as maplibregl.ExpressionSpecification;
          const lineColor = themeMode === "dark" ? "#5b6670" : "#7a8590";

          if (!map.getLayer(FILL_LAYER)) {
            try {
              map.addLayer(
                {
                  id: FILL_LAYER,
                  type: "fill",
                  source: SRC_ID,
                  paint: {
                    "fill-color": fillExpr,
                    "fill-opacity": [
                      "case",
                      ["boolean", ["feature-state", "selected"], false],
                      0.78,
                      ["boolean", ["feature-state", "hover"], false],
                      0.68,
                      themeMode === "dark" ? 0.48 : 0.62,
                    ],
                  },
                },
                pickInsertionId(map),
              );
            } catch (err) {
              // eslint-disable-next-line no-console
              console.error("[RegionalStateLayer] addLayer(fill) on style.load failed:", err);
            }
          }
          if (!map.getLayer(LINE_LAYER)) {
            try {
              map.addLayer(
                {
                  id: LINE_LAYER,
                  type: "line",
                  source: SRC_ID,
                  paint: {
                    "line-color": lineColor,
                    "line-width": [
                      "case",
                      ["boolean", ["feature-state", "selected"], false],
                      2.4,
                      ["boolean", ["feature-state", "hover"], false],
                      1.6,
                      0.7,
                    ],
                    "line-opacity": themeMode === "dark" ? 0.75 : 0.6,
                  },
                },
                pickInsertionId(map),
              );
            } catch (err) {
              // eslint-disable-next-line no-console
              console.error("[RegionalStateLayer] addLayer(line) on style.load failed:", err);
            }
          }
        })
        .catch((err) => {
          // eslint-disable-next-line no-console
          console.error("[RegionalStateLayer] style.load reload boundaries failed:", err);
        });
    };

    map.on("style.load", onStyleLoad);
    return () => {
      try { map.off("style.load", onStyleLoad); } catch { /* map removed */ }
    };
  }, [map, mapReady, sourceAdded, activeMetricId, themeMode, records]);

  // Hover / click handlers
  useEffect(() => {
    if (!map || !sourceAdded) return;
    if (activeMetricId === null) return;

    const handleMove = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
      const f = e.features?.[0];
      if (!f) return;
      const fips = String((f.properties as { id?: string })?.id ?? "").padStart(2, "0");
      const rec = recordsRef.current.find((r) => r.geoId === fips) ?? null;
      map.getCanvas().style.cursor = "pointer";
      map.setFeatureState({ source: SRC_ID, id: fips }, { hover: true });
      onHover?.(fips, rec);
    };
    const handleLeave = () => {
      map.getCanvas().style.cursor = "";
      // clear all hover states
      for (const r of recordsRef.current) {
        map.setFeatureState({ source: SRC_ID, id: r.geoId }, { hover: false });
      }
      onHover?.(null, null);
    };
    const handleClick = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
      const f = e.features?.[0];
      if (!f) return;
      const fips = String((f.properties as { id?: string })?.id ?? "").padStart(2, "0");
      const rec = recordsRef.current.find((r) => r.geoId === fips) ?? null;
      // Stage 7B-A.3.1: clear ALL previously-selected features before
      // applying the new selection. The previous implementation only
      // set `selected: true` on the new fips, which caused every
      // previously-clicked state to remain highlighted. We now
      // iterate all known geoIds and reset `selected: false` on each
      // before applying the new highlight, so the source is in a
      // single-selected state at all times.
      for (const r of recordsRef.current) {
        try { map.setFeatureState({ source: SRC_ID, id: r.geoId }, { selected: false }); } catch { /* fips missing from source */ }
      }
      try { map.setFeatureState({ source: SRC_ID, id: fips }, { selected: true }); } catch { /* skip */ }
      onClick?.(fips, rec);
    };

    map.on("mousemove", FILL_LAYER, handleMove);
    map.on("mouseleave", FILL_LAYER, handleLeave);
    map.on("click", FILL_LAYER, handleClick);
    return () => {
      try {
        map.off("mousemove", FILL_LAYER, handleMove);
        map.off("mouseleave", FILL_LAYER, handleLeave);
        map.off("click", FILL_LAYER, handleClick);
      } catch { /* map may already be removed */ }
    };
  }, [map, sourceAdded, activeMetricId, onHover, onClick]);

  return null;
}

/**
 * Decide the layer id under which `pathos-regional-states-fill` /
 * `-line` should be inserted. The choropleth must sit:
 *   - ABOVE the raster basemap (so the fills are visible),
 *   - BELOW any city drilldown layer (so city bubbles win on hit-test),
 *   - BELOW the POI marker layer (so university pins win on hit-test),
 *   - BELOW any text label layer (so labels remain readable).
 *
 * The previous version of this helper only searched for `pathos-city-*`
 * layers, which are not present by default (city drilldown is off on
 * first mount). With no matching layer, `addLayer(…, undefined)` would
 * append to the end of the layer stack and the choropleth would render
 * UNDER every symbol layer — including the POI halo and the basemap
 * symbol tiles — making it effectively invisible.
 *
 * Closing Patch v2: look in priority order
 *   1. A `pathos-city-*` fill (city drilldown choropleth) — most
 *      specific; the regional fill must sit beneath it.
 *   2. The POI points layer (always present once `UniversityPoiLayer`
 *      mounts) — keep the choropleth under university pins.
 *   3. The POI halo layer (also always present) — same rationale.
 *   4. The POI labels layer — labels are text, choropleth goes beneath.
 *   5. Any text/symbol layer — the basemap rarely has any, but in case
 *      the user picked a labeled style we still keep below.
 *   6. `undefined` (append to end) as last resort.
 *
 * Exported so unit tests can target the rule without a real MapLibre.
 */
export function pickInsertionId(map: maplibregl.Map): string | undefined {
  const style = map.getStyle();
  const layers = style?.layers ?? [];

  const cityLayer = layers.find(
    (l) => l.id?.startsWith("pathos-city-") ?? false,
  );
  if (cityLayer?.id) return cityLayer.id;

  const pointsLayer = layers.find((l) => l.id === POI_POINTS_ID);
  if (pointsLayer?.id) return pointsLayer.id;

  const haloLayer = layers.find((l) => l.id === POI_HALO_ID);
  if (haloLayer?.id) return haloLayer.id;

  const labelsLayer = layers.find((l) => l.id === POI_LABELS_ID);
  if (labelsLayer?.id) return labelsLayer.id;

  const anySymbol = layers.find((l) => l.type === "symbol");
  if (anySymbol?.id) return anySymbol.id;

  return undefined;
}

/**
 * Minimal map interface required by {@link deferUntilStyleLoaded}. Both
 * the source-install and the layer-install effects rely on this exact
 * set of methods, so it is exported to make the deferral lifecycle
 * unit-testable without standing up a full MapLibre instance.
 *
 * `isStyleLoaded` is typed `boolean | void` to match MapLibre's own
 * signature, which calls the implementation through a void-returning
 * hook and returns `undefined` from certain code paths.
 */
export interface StyleLoadedGate {
  isStyleLoaded(): boolean | void;
  once(event: "style.load", listener: () => void): unknown;
  off(event: "style.load", listener: () => void): unknown;
}

/**
 * Run `apply` either immediately (when the map style is already
 * loaded) or once on the next `style.load` event. Returns a cancel
 * function that removes the one-time listener and silences the
 * pending callback.
 *
 * This is the central guard added in Stage 7B-A Final Closure to
 * prevent MapLibre's "Style is not done loading" error when source /
 * layer effects fire before the basemap tiles finish loading.
 */
export function deferUntilStyleLoaded(
  map: StyleLoadedGate,
  apply: () => void,
): () => void {
  let cancelled = false;
  // MapLibre's `isStyleLoaded()` can briefly return `false` even after
  // the `load` event has fired (e.g. immediately after a fresh
  // initialisation, the flag toggles inside an internal render frame).
  // If we register a one-shot `style.load` listener at that moment, it
  // will never fire (style is already loaded — only `setStyle` re-emits
  // it), leaving `apply` permanently dead. To avoid that, we poll
  // `isStyleLoaded()` on the next animation frames (max 12) and apply
  // as soon as it stabilises to `true`. The previous implementation
  // fell through to `once("style.load")` which is exactly the dead
  // path the Phase 4B debug probes surfaced.
  let attempts = 0;
  const tick = () => {
    if (cancelled) return;
    if (map.isStyleLoaded()) {
      apply();
      return;
    }
    attempts += 1;
    if (attempts >= 12) {
      // Give up waiting — apply anyway. addSource/addLayer are wrapped
      // in try/catch in the caller, so a still-not-loaded style will
      // surface as an error rather than silently strand the layer.
      apply();
      return;
    }
    if (typeof requestAnimationFrame !== "undefined") {
      requestAnimationFrame(tick);
    } else {
      setTimeout(tick, 16);
    }
  };
  tick();
  return () => {
    cancelled = true;
  };
}

// Re-export a tiny id type guard for tests.
export function isKnownRegionalMetricId(id: string): id is RegionalMetricId {
  return (REGIONAL_METRIC_IDS as readonly string[]).includes(id);
}

// Re-export shape coercion helper used by tests.
export function summarizeRegionalRecords(): Record<RegionalMetricId, number> {
  const out: Record<RegionalMetricId, number> = {
    income: 0,
    safety: 0,
    employment: 0,
    chinese_population: 0,
  };
  for (const m of REGIONAL_METRIC_IDS) {
    out[m] = getRegionalMetricRecords(m).length;
  }
  return out;
}