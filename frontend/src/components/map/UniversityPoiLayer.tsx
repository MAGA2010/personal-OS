"use client";

// UniversityPoiLayer — GeoJSON source + circle layer for university POIs.
//
// Why GeoJSON instead of `new maplibregl.Marker({ element })`:
//   - HTML markers rely on MapLibre projecting the lng/lat into screen
//     pixels at construction time. If the projection matrix is still
//     degenerate (zero-height container, late layout), every marker
//     collapses onto the same screen point. Repeating the projection on
//     `resize` doesn't help, because the marker elements cache their
//     `transform: translate(Xpx, Ypx)` until the next 'moveend'.
//   - GeoJSON + a single circle layer is part of the GL render path:
//     positions are recomputed every frame and never cache a stale
//     screen point. Going from 62 broken HTML markers to 1 GeoJSON
//     source with 62 features also lets us use clustering, feature-state,
//     and data-driven paint expressions — none of which work with
//     HTML markers.
//
// Source of truth for this file:
//   - Universities list comes from the same `UniversityPOI[]` the rest
//     of the app consumes (data source → useUniversitySummaries).
//   - Click/hover behaviour matches the legacy HTML marker contract so
//     callers (MapShell) need no changes beyond renaming the import.
//   - Map instance comes from `useMapContext`, registered in `MapCanvas`.
//
// Constraints:
//   - The component owns its source/layer lifecycle; cleanup removes
//     both. It never reaches into the parent MapCanvas.
//   - Selection state uses MapLibre's `setFeatureState` so we don't
//     rebuild the source on every selection change.
//   - Filter (zoom threshold) is implemented as a paint expression
//     driven by `feature-state` so show/hide is fast and doesn't
//     require re-clustering.

import { useCallback, useEffect, useMemo, useRef } from "react";
import type { Feature, FeatureCollection, Point } from "geojson";
import { useMapContext } from "./MapCanvas";
import type { UniversityPOI, RankingTier, ChineseCommunityLevel } from "@/lib/types";
import type { UniversitySummary } from "@/domain/dataset";
import { pickAbbreviation } from "@/lib/abbreviation";

const SOURCE_ID = "pathos-universities";
const POINT_LAYER_ID = "pathos-universities-points";
const HOVER_LAYER_ID = "pathos-universities-hover";
const LABEL_LAYER_ID = "pathos-universities-labels";
const HALO_LAYER_ID = "pathos-universities-halo";

interface POIFeatureProps {
  id: string;
  rankingTier: RankingTier;
  chineseCommunity: ChineseCommunityLevel;
  /** 1–3 char abbreviation rendered as a label on the marker. */
  abbr: string;
  /** Chinese display name (used for tooltip / aria-label). */
  nameZh: string;
  /** English display name. */
  name: string;
  /** City display name (used for tooltip). */
  city: string;
  /** State abbreviation or Chinese state name (used for tooltip). */
  state: string;
  /** "1" = visible, "0" = hidden via zoom threshold. */
  visible: 0 | 1;
  /** "1" = selected. Drives the highlight ring colour. */
  selected: 0 | 1;
  /** "1" = hovered. */
  hover: 0 | 1;
  /** "1" = part of compare set. */
  compare: 0 | 1;
  /** "1" = saved (added to portfolio/calculator). */
  saved: 0 | 1;
}

type POIFeature = Feature<Point, POIFeatureProps>;

/**
 * Internal: pick the first pair of finite lat/lng we can find on
 * either the legacy `UniversityPOI` shape or the canonical
 * `UniversitySummary` shape. The legacy mapper
 * (`summaryToLegacyUniversityPOI`) zero-fills lat/lng when the
 * summary's value is `null`, so we cannot trust that path; this
 * helper reaches across both shapes.
 */
function readLatLng(
  row: UniversityPOI | UniversitySummary,
): { lat: number; lng: number } | null {
  const candLat: unknown[] = [
    (row as UniversityPOI).latitude,
    (row as UniversitySummary).latitude,
  ];
  const candLng: unknown[] = [
    (row as UniversityPOI).longitude,
    (row as UniversitySummary).longitude,
  ];
  for (let i = 0; i < candLat.length; i++) {
    const lat = candLat[i];
    const lng = candLng[i];
    if (typeof lat === "number" && typeof lng === "number" && Number.isFinite(lat) && Number.isFinite(lng)) {
      // The legacy mapper produces (0, 0) for missing coords. Treat
      // that as missing so we don't end up with 62 markers on Null
      // Island.
      if (lat === 0 && lng === 0) continue;
      return { lat, lng };
    }
  }
  return null;
}

function buildFeatureCollection(
  rows: readonly (UniversityPOI | UniversitySummary)[],
  options?: { compareIds?: ReadonlySet<string>; savedIds?: ReadonlySet<string> },
): FeatureCollection<Point, POIFeatureProps> {
  const compareIds = options?.compareIds ?? new Set<string>();
  const savedIds = options?.savedIds ?? new Set<string>();
  const features: POIFeature[] = [];
  for (const row of rows) {
    const ll = readLatLng(row);
    if (!ll) continue;
    const nameZh = ((row as UniversityPOI).chineseName ?? (row as UniversitySummary).nameZh ?? "").trim();
    const nameEn = ((row as UniversityPOI).name ?? (row as UniversitySummary).name ?? "").trim();
    const city = ((row as UniversityPOI).city ?? "").trim();
    // Legacy POIs and new summaries both carry a state at runtime
    // (via the legacy mapper extension) even though `UniversityPOI`'s
    // declared shape doesn't include it.
    const state = String(((row as unknown as { state?: string }).state ?? (row as UniversitySummary).state ?? "")).trim();
    const shortName = ((row as unknown as { shortName?: string }).shortName ?? null);
    const abbr = pickAbbreviation({ shortName, englishName: nameEn, chineseName: nameZh, id: row.id });
    features.push({
      type: "Feature",
      id: row.id,
      geometry: { type: "Point", coordinates: [ll.lng, ll.lat] },
      properties: {
        id: row.id,
        // rankingTier is required on legacy POIs but optional on the
        // new Summary shape; fall back to "other" so the paint
        // expression always receives a valid RankingTier.
        rankingTier: (row.rankingTier ?? "other") as RankingTier,
        chineseCommunity: (row as UniversityPOI).chineseCommunity ?? "medium",
        abbr,
        nameZh,
        name: nameEn,
        city,
        state,
        visible: 1,
        selected: 0,
        hover: 0,
        compare: compareIds.has(row.id) ? 1 : 0,
        saved: savedIds.has(row.id) ? 1 : 0,
      },
    });
  }
  return { type: "FeatureCollection", features };
}

export interface UniversityPoiLayerProps {
  universities: ReadonlyArray<UniversityPOI | UniversitySummary>;
  /** Called when a user clicks a POI. Passes `null` for deselect. */
  onSelect: (id: string | null) => void;
  /** Currently selected university ID (for the highlight ring). */
  selectedId?: string | null;
  /** Optional hover callback — receives the hovered ID or `null`. */
  onHover?: (id: string | null) => void;
  /** Below this zoom, points disappear (clusters should take over later). */
  pinMinZoom?: number;
  /** IDs currently in the compare set. Drives a subtle accent ring. */
  compareIds?: ReadonlyArray<string>;
  /** IDs currently saved to the user's portfolio. */
  savedIds?: ReadonlyArray<string>;
}

/**
 * `UniversityPoiLayer` — renders university POIs as a single GeoJSON
 * source with three layers (point circle, hover halo, label).
 *
 * Why this exists:
 *   The previous implementation used `new maplibregl.Marker({ element })`
 *   for each university. MapLibre positions HTML markers by setting
 *   `element.style.transform = translate(Xpx, Ypx)`; that DOM-level
 *   positioning means the marker screen position is computed once
 *   when the marker is added (using whatever the projection matrix
 *   says at that exact moment) and reused until the marker is
 *   removed. If the projection is degenerate at add time (zero-height
 *   container, late layout, parent map <Map> replaced mid-render),
 *   every marker gets the same `(Xpx, Ypx)` and they all stack at
 *   one screen point.
 *
 *   GeoJSON sources compute positions on the GPU every frame; the
 *   wrong-projection bug is structurally impossible.
 */
export function UniversityPoiLayer({
  universities,
  onSelect,
  selectedId,
  onHover,
  pinMinZoom = 0,
  compareIds,
  savedIds,
}: UniversityPoiLayerProps) {
  const mapContext = useMapContext();
  const sourceDataRef = useRef<FeatureCollection<Point, POIFeatureProps> | null>(null);
  // We use refs for the latest callback so the effect that wires events
  // doesn't re-fire on every parent re-render.
  const onSelectRef = useRef(onSelect);
  const onHoverRef = useRef(onHover);
  onSelectRef.current = onSelect;
  onHoverRef.current = onHover;
  const selectedIdRef = useRef<string | null>(selectedId ?? null);
  selectedIdRef.current = selectedId ?? null;

  const compareSet = useMemo(() => new Set(compareIds ?? []), [compareIds]);
  const savedSet = useMemo(() => new Set(savedIds ?? []), [savedIds]);

  const collection = useMemo(
    () => buildFeatureCollection(universities, { compareIds: compareSet, savedIds: savedSet }),
    [universities, compareSet, savedSet],
  );
  sourceDataRef.current = collection;

  // ── Mount source + layers + events once the map is ready. ────────────────
  useEffect(() => {
    const map = mapContext?.map;
    if (!map) return;
    const ready = () => {
      // 1. Add the GeoJSON source if it isn't there yet.
      if (!map.getSource(SOURCE_ID)) {
        map.addSource(SOURCE_ID, {
          type: "geojson",
          data: sourceDataRef.current ?? { type: "FeatureCollection", features: [] },
          promoteId: "id",
        });
      } else {
        const src = map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
        if (src) src.setData(sourceDataRef.current ?? { type: "FeatureCollection", features: [] });
      }

      // 2. Add the point layer if it isn't there yet. The visible
      //    expression respects `pinMinZoom` via a feature-state flag
      //    flipped in the zoom handler below.
      if (!map.getLayer(HALO_LAYER_ID)) {
        map.addLayer({
          id: HALO_LAYER_ID,
          type: "circle",
          source: SOURCE_ID,
          paint: {
            "circle-radius": [
              "interpolate", ["linear"], ["zoom"],
              3, 9,
              6, 13,
              9, 17,
            ],
            "circle-color": [
              "match", ["get", "rankingTier"],
              "top20", "#c45f36",
              "top50", "#315d9f",
              "top100", "#23766b",
              "#152025",
            ],
            "circle-opacity": [
              "case",
              ["==", ["feature-state", "hover"], 1], 0.18,
              ["==", ["feature-state", "compare"], 1], 0.14,
              0,
            ],
          },
        });
      }
      if (!map.getLayer(POINT_LAYER_ID)) {
        map.addLayer({
          id: POINT_LAYER_ID,
          type: "circle",
          source: SOURCE_ID,
          paint: {
            "circle-radius": [
              "interpolate", ["linear"], ["zoom"],
              3, 6,
              6, 9,
              9, 12,
            ],
            "circle-color": [
              "match", ["get", "rankingTier"],
              "top20", "#c45f36",
              "top50", "#315d9f",
              "top100", "#23766b",
              "#152025",
            ],
            "circle-stroke-color": [
              "case",
              ["==", ["feature-state", "selected"], 1], "#fffaf1",
              ["==", ["feature-state", "compare"], 1], "#23766b",
              ["==", ["feature-state", "saved"], 1], "#c45f36",
              "#fffaf1",
            ],
            "circle-stroke-width": [
              "case",
              ["==", ["feature-state", "selected"], 1], 3.2,
              ["==", ["feature-state", "hover"], 1], 2.4,
              ["==", ["feature-state", "compare"], 1], 2.0,
              ["==", ["feature-state", "saved"], 1], 2.0,
              1.5,
            ],
            "circle-opacity": [
              "case",
              ["==", ["feature-state", "visible"], 1], 0.96,
              0,
            ],
            "circle-stroke-opacity": [
              "case",
              ["==", ["feature-state", "visible"], 1], 1,
              0,
            ],
            "circle-pitch-alignment": "viewport",
          },
        });
      }
      if (!map.getLayer(HOVER_LAYER_ID)) {
        map.addLayer({
          id: HOVER_LAYER_ID,
          type: "circle",
          source: SOURCE_ID,
          paint: {
            "circle-radius": [
              "interpolate", ["linear"], ["zoom"],
              3, 8,
              6, 12,
              9, 15,
            ],
            "circle-color": "rgba(0,0,0,0)",
            "circle-stroke-color": "#315d9f",
            "circle-stroke-width": 2,
            "circle-stroke-opacity": [
              "case",
              ["==", ["feature-state", "hover"], 1], 0.95, 0,
            ],
            "circle-opacity": [
              "case",
              ["==", ["feature-state", "visible"], 1], 0.001, 0,
            ],
          },
        });
      }
      if (!map.getLayer(LABEL_LAYER_ID)) {
        // Detect which fonts the active style actually exposes.
        const availableFonts = new Set<string>();
        try {
          const layers = map.getStyle().layers ?? [];
          for (const lyr of layers) {
            const ref = (lyr as { layout?: Record<string, unknown> }).layout?.["text-font"];
            if (Array.isArray(ref)) for (const f of ref) if (typeof f === "string") availableFonts.add(f);
          }
        } catch { /* ignore */ }
        const candidates = ["Noto Sans Regular", "Open Sans Regular", "Arial Unicode MS Regular", "DIN Pro Medium", "DIN Pro Regular"];
        const textFont = candidates.find((f) => availableFonts.has(f)) ?? candidates[0];
        map.addLayer({
          id: LABEL_LAYER_ID,
          type: "symbol",
          source: SOURCE_ID,
          minzoom: 3,
          layout: {
            "text-field": ["get", "abbr"],
            "text-allow-overlap": true,
            "text-ignore-placement": true,
            "text-size": [
              "interpolate", ["linear"], ["zoom"],
              3, 9,
              6, 11,
              9, 13,
            ],
            "text-font": [textFont],
          },
          paint: {
            "text-color": "#fffaf1",
            "text-halo-color": "#152025",
            "text-halo-width": 0.6,
            "text-opacity": [
              "case",
              ["==", ["feature-state", "visible"], 1], 1,
              0,
            ],
          },
        });
      }

      // 3. Wire click → onSelect.
      const handleClick = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
        const feat = e.features?.[0];
        if (!feat) {
          onSelectRef.current?.(null);
          return;
        }
        const id = typeof feat.id === "string" ? feat.id : null;
        if (!id) return;
        onSelectRef.current?.(selectedIdRef.current === id ? null : id);
      };
      // Defensive: remove any pre-existing handler before adding, in case
      // the effect re-ran without proper cleanup.
      map.off("click", POINT_LAYER_ID, handleClick);
      map.on("click", POINT_LAYER_ID, handleClick);

      // 4. Hover → onHover + cursor + feature-state.
      const handleMouseEnter = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
        map.getCanvas().style.cursor = "pointer";
        const feat = e.features?.[0];
        const id = feat ? (typeof feat.id === "string" ? feat.id : null) : null;
        if (id) {
          try { map.setFeatureState({ source: SOURCE_ID, id }, { hover: 1 }); } catch { /* race */ }
          onHoverRef.current?.(id);
        }
      };
      const handleMouseMove = handleMouseEnter;
      const handleMouseLeave = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
        map.getCanvas().style.cursor = "";
        const feat = e.features?.[0];
        const id = feat ? (typeof feat.id === "string" ? feat.id : null) : null;
        if (id) {
          try { map.setFeatureState({ source: SOURCE_ID, id }, { hover: 0 }); } catch { /* race */ }
        }
        onHoverRef.current?.(null);
      };
      map.on("mouseenter", POINT_LAYER_ID, handleMouseEnter);
      map.on("mousemove", POINT_LAYER_ID, handleMouseMove);
      map.on("mouseleave", POINT_LAYER_ID, handleMouseLeave);

      // 5. Pin-visibility driven by zoom threshold.
      const applyPinVisibility = () => {
        const z = map.getZoom();
        const visible = z >= pinMinZoom;
        const setVisibleFor = (id: string, value: 0 | 1) => {
          try { map.setFeatureState({ source: SOURCE_ID, id }, { visible: value }); } catch { /* race during teardown */ }
        };
        for (const feat of (sourceDataRef.current?.features ?? []) as POIFeature[]) {
          const id = String(feat.id ?? feat.properties.id);
          setVisibleFor(id, visible ? 1 : 0);
        }
      };
      applyPinVisibility();
      map.on("zoom", applyPinVisibility);

      // 6. Cleanup
      const cleanup = () => {
        map.off("click", POINT_LAYER_ID, handleClick);
        map.off("mouseenter", POINT_LAYER_ID, handleMouseEnter);
        map.off("mousemove", POINT_LAYER_ID, handleMouseMove);
        map.off("mouseleave", POINT_LAYER_ID, handleMouseLeave);
        map.off("zoom", applyPinVisibility);
        try { if (map.getLayer(HALO_LAYER_ID)) map.removeLayer(HALO_LAYER_ID); } catch { /* noop */ }
        try { if (map.getLayer(LABEL_LAYER_ID)) map.removeLayer(LABEL_LAYER_ID); } catch { /* noop */ }
        try { if (map.getLayer(HOVER_LAYER_ID)) map.removeLayer(HOVER_LAYER_ID); } catch { /* noop */ }
        try { if (map.getLayer(POINT_LAYER_ID)) map.removeLayer(POINT_LAYER_ID); } catch { /* noop */ }
        try { if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID); } catch { /* noop */ }
      };
      return cleanup;
    };
    // A theme change calls map.setStyle(), which removes every custom
    // source and layer. Reinstall the POI runtime after each style load,
    // first cleaning the previous event handlers to avoid duplicates.
    let cleanupActive: (() => void) | undefined;
    const install = () => {
      cleanupActive?.();
      cleanupActive = ready();
    };
    const onStyleLoad = () => install();
    map.on("style.load", onStyleLoad);
    if (map.loaded()) install();
    else map.once("load", install);
    return () => {
      map.off("style.load", onStyleLoad);
      map.off("load", install);
      cleanupActive?.();
    };
  }, [mapContext?.map, mapContext?.mapReady, pinMinZoom]);

  // ── Update data when the input list changes. ──────────────────────────────
  useEffect(() => {
    const map = mapContext?.map;
    if (!map) return;
    const apply = () => {
      const src = map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
      if (!src) return;
      src.setData(sourceDataRef.current ?? { type: "FeatureCollection", features: [] });
    };
    // `map.loaded()` can be false after the one-time `load` event while
    // raster tiles are still settling. Waiting for another `load` in that
    // state strands late-arriving university data forever. If our source
    // exists, GeoJSONSource#setData is safe immediately; if it does not,
    // the installer above will read the latest sourceDataRef.
    apply();
  }, [collection, mapContext?.map, mapContext?.mapReady]);

  // ── Apply selection / compare / saved highlight via feature-state ────
  useEffect(() => {
    const map = mapContext?.map;
    if (!map || !mapContext?.mapReady) return;
    const apply = () => {
      const features = (sourceDataRef.current?.features ?? []) as POIFeature[];
      for (const feat of features) {
        const id = String(feat.id ?? feat.properties.id);
        try {
          map.setFeatureState({ source: SOURCE_ID, id }, {
            selected: selectedId === id ? 1 : 0,
            compare: compareSet.has(id) ? 1 : 0,
            saved: savedSet.has(id) ? 1 : 0,
          });
        } catch { /* race */ }
      }
    };
    apply();
  }, [selectedId, compareSet, savedSet, mapContext?.map, mapContext?.mapReady]);

  return null;
}

export default UniversityPoiLayer;
