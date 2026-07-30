"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  createContext,
  useContext,
  type ReactNode,
} from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Loader2 } from "lucide-react";
import type { MapViewState, Granularity, MetricId } from "@/lib/types";

// PathOS Stage 7B-A.1 Closing Patch v2: MapCanvas no longer owns the
// state-level choropleth. The previous version imported METRIC_DEFINITIONS
// (for palette mapping), the d3-scale-chromatic interpolators, the
// topojson-client `feature()` decoder, and the RegionMetricSet type —
// none of which are used anymore. The imports are removed.

// ═══════════════════════════════════════════════════════════════════════════════
// MapCanvas — MapLibre GL map initialisation shell
// ═══════════════════════════════════════════════════════════════════════════════
//
// Responsibilities
// ────────────────
// 1. Create & manage a single `maplibregl.Map` instance.
// 2. Load the CARTO Positron raster tile style (free, no API key).
// 3. Provide a React context so descendants can access the map instance
//    (for adding sources, layers, markers, etc.).
// 4. Auto-derive `granularity` from zoom level.
// 5. Accept `children` for overlay components (legend, tooltip, metric tabs).
//
// Non-responsibilities (delegated to children / sibling components)
// ──────────────────────────────────────────────────────────────────
// • Choropleth fill layer   →  `ChoroplethLayer` (TODO: component)
// • POI markers / clusters  →  `POIMarkerLayer` (TODO: component)
// • Metric switcher          →  `MetricTabs`
// • Legend                   →  `MapLegend`
// • Tooltip                  →  `RegionTooltip`
// • Data fetching            →  parent / custom hooks
//
// Conventions
// ───────────
// • Chinese labels primary, English secondary (fallback).
// • Tailwind colour tokens: ink, paper, panel, line, jade, persimmon, cobalt.
// • TODO markers for data-dependent sections.
//
// TODO: Connect to Supabase when available — replace mock data in parent hooks.
// TODO: Add choropleth layer component once data pipeline is wired.
// TODO: Add POI marker cluster layer when `UniversityPOI[]` data is available.

// ── Constants ─────────────────────────────────────────────────────────────────

/**
 * Light basemap. Carto Voyager — clean, light cream land with
 * muted blue water; key-less, public, MIT-licensed raster style.
 * We rebuild it inline rather than fetching the remote style.json
 * so the style loads synchronously and we have full control over
 * attribution / paint properties.
 */
const LIGHT_BASEMAP_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    "carto-light": {
      type: "raster",
      tiles: [
        "https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
        "https://b.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
        "https://c.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
        "https://d.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
      ],
      tileSize: 256,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    },
  },
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#f6f3ed" } },
    { id: "carto-light", type: "raster", source: "carto-light" },
  ],
  // NOTE: No `glyphs` field — both inline basemaps are raster-only
  // (background + raster source). MapLibre v3 rejects styles that declare
  // any property as explicit `undefined`; omitting the key entirely is
  // the canonical fix when no symbol/text-field layer is present.
};

/**
 * Dark basemap. Carto Dark Matter — public, key-less raster style.
 * Built inline so we don't depend on remote style.json loading.
 * Uses cool charcoal land + dark blue water; light labels remain
 * legible against the deep background.
 */
const DARK_BASEMAP_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    "carto-dark": {
      type: "raster",
      tiles: [
        "https://a.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png",
        "https://b.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png",
        "https://c.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png",
        "https://d.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png",
      ],
      tileSize: 256,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    },
  },
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#181e24" } },
    { id: "carto-dark", type: "raster", source: "carto-dark" },
  ],
  // NOTE: No `glyphs` field — raster-only style. See LIGHT_BASEMAP_STYLE
  // for the rationale on omitting the key entirely.
};

/**
 * Public constants so callers can introspect which style is in use.
 * Note: these are inline styles (no remote style.json fetch); both
 * are key-less public CARTO basemaps.
 */
export const DEFAULT_LIGHT_STYLE = LIGHT_BASEMAP_STYLE;
export const DEFAULT_DARK_STYLE = DARK_BASEMAP_STYLE;
export { LIGHT_BASEMAP_STYLE, DARK_BASEMAP_STYLE };

/** Map centre: continental US. */
const INITIAL_CENTER: [number, number] = [-98.5, 39.8];

/** Starting zoom: full US view. */
const INITIAL_ZOOM = 4.0;

/** Minimum zoom before we revert to state-level granularity. */
const STATE_MAX_ZOOM = 6;

/** County-level band. */
const COUNTY_MAX_ZOOM = 9;

// PathOS Stage 7B-A.1 Closing Patch v2: the state-level choropleth is
// now owned EXCLUSIVELY by `RegionalStateLayer` (it listens to the
// regional metric from `useRegionalMetric`). The previous version of
// `MapCanvas` maintained its own `pathos-us-states-fill` layer driven
// by the city-level `activeMetricId`, which produced two competing
// choropleth layers (C1 in the Re-Gate report) and made the regional
// metric visually invisible.
//
// All choropleth constants/helpers/effects have been removed. The
// `activeMetricId` prop is preserved (used by `syncViewState` to keep
// the URL bridge informed about the city-level metric) but it no
// longer drives any paint expression.

// ── Map Context ───────────────────────────────────────────────────────────────

export interface MapContextValue {
  /** The underlying MapLibre GL map instance (null before initialisation). */
  map: maplibregl.Map | null;

  /** Whether the map's `load` event has fired. */
  mapReady: boolean;

  /** Current granularity derived from zoom level. */
  granularity: Granularity;

  /** Current viewport state for URL persistence. */
  viewState: MapViewState;
}

const MapContext = createContext<MapContextValue | null>(null);

/**
 * Access the MapLibre map instance and derived state from any descendant
 * of `MapCanvas`.  Returns `null` when called outside the provider.
 */
export function useMapContext(): MapContextValue | null {
  return useContext(MapContext);
}

// ── Props ─────────────────────────────────────────────────────────────────────

export interface MapCanvasProps {
  /** Extra CSS classes appended to the outermost wrapper. */
  className?: string;

  /** Override the light-theme tile style. Defaults to Carto Voyager raster. */
  lightStyle?: maplibregl.StyleSpecification;

  /** Override the dark-theme tile style. Defaults to Carto Dark Matter raster. */
  darkStyle?: maplibregl.StyleSpecification;

  /** Override the initial centre coordinate. */
  initialCenter?: [number, number];

  /** Override the initial zoom level. */
  initialZoom?: number;

  /** Called every time the viewport moves (debounced). */
  onViewStateChange?: (state: MapViewState) => void;

  /** Called when granularity flips due to zoom crossing a threshold. */
  onGranularityChange?: (granularity: Granularity) => void;

  /** Called when a state choropleth region is clicked. */
  onRegionClick?: (fipsCode: string) => void;

  /**
   * Called when the user clicks the map outside any POI / region.
   * Used by the parent to clear the selected university profile
   * when the user clicks empty space (replaces the previous
   * full-bleed transparent backdrop which was intercepting
   * mousedown / wheel / touch and locking MapLibre drag/zoom).
   */
  onMapEmptyClick?: () => void;

  /** Called once the MapLibre instance has been created. */
  onMapInit?: (map: maplibregl.Map) => void;

  /** Overlay components rendered inside the map container (e.g. legend, tooltip). */
  children?: ReactNode;

  /** Content shown while the map and basemap tiles are still loading. */
  loadingFallback?: ReactNode;

  /** Boundary GeoJSON features (for hover tooltip — optional). */
  // TODO: Replace with real {featureCollection} from useBoundaries
  interactiveLayerIds?: string[];

  /** Active metric for tooltip display formatting. */
  // TODO: Replace with real {metricId} from parent state
  activeMetricId?: MetricId;

  /**
   * Region metric records for choropleth fill — REMOVED in Closing
   * Patch v2. The state-level choropleth is owned exclusively by
   * `RegionalStateLayer` now; `MapCanvas` no longer paints the US
   * states. The prop is removed from the type surface entirely;
   * callers passing it via the legacy `MapCanvasProps` spread will
   * hit a TypeScript error pointing them at the new owner. We keep
   * this comment block so the next reader understands why the prop
   * disappeared.
   *
   * @deprecated use `RegionalStateLayer` to drive the state choropleth.
   */
  regionMetricSet?: never;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function MapCanvas({
  className,
  lightStyle = LIGHT_BASEMAP_STYLE,
  darkStyle = DARK_BASEMAP_STYLE,
  initialCenter = INITIAL_CENTER,
  initialZoom = INITIAL_ZOOM,
  onViewStateChange,
  onGranularityChange,
  onRegionClick,
  onMapEmptyClick,
  onMapInit,
  children,
  loadingFallback,
  interactiveLayerIds,
  activeMetricId,
  regionMetricSet,
}: MapCanvasProps) {
  // ── Refs ──
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const initializedRef = useRef(false);
  const regionClickRef = useRef<MapCanvasProps["onRegionClick"]>(onRegionClick);
  const emptyClickRef = useRef<MapCanvasProps["onMapEmptyClick"]>(onMapEmptyClick);

  // ── State ──
 const [mapReady, setMapReady] = useState(false);
  const [granularity, setGranularity] = useState<Granularity>("state");
  const [viewState, setViewState] = useState<MapViewState>({
    longitude: initialCenter[0],
    latitude: initialCenter[1],
    zoom: initialZoom,
    bearing: 0,
    pitch: 0,
    activeMetricId,
    selectedUniversityId: null,
    selectedCampusPoiId: null,
    mode: "map",
    panelOpen: false,
  });

  // ── Derived context value ──
  //
  // `mapRef.current` is captured at memo time, but reading a ref doesn't
  // track changes. We re-derive the context object whenever the
  // `mapReady` boolean flips (which happens in lockstep with the ref
  // being populated), so the memo's dep array stays ESLint-clean while
  // descendants still get a fresh `map` reference after init.
  const contextValue = useMemo<MapContextValue>(
    () => ({
      map: mapRef.current,
      mapReady,
      granularity,
      viewState,
    }),
    [mapReady, granularity, viewState],
  );

  // ── Keep viewState in sync with activeMetricId prop ──
  useEffect(() => {
    setViewState((prev) => ({ ...prev, activeMetricId }));
  }, [activeMetricId]);


  useEffect(() => {
    regionClickRef.current = onRegionClick;
  }, [onRegionClick]);
  useEffect(() => {
    emptyClickRef.current = onMapEmptyClick;
  }, [onMapEmptyClick]);

  // ── Initialise / destroy MapLibre ─────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || initializedRef.current) return;
    initializedRef.current = true;

    const map = new maplibregl.Map({
      container: containerRef.current,
      // Initial style is read on first mount; the theme-listener
      // below will swap to the dark style whenever the user (or the
      // OS in System mode) flips to dark mode. We pick the right
      // style up front so the very first paint is already correct.
      style:
        typeof document !== "undefined" && document.documentElement.classList.contains("dark")
          ? darkStyle
          : lightStyle,
      center: initialCenter,
      zoom: initialZoom,
      attributionControl: false,
      // Restrict view to US only
      maxBounds: [[-135, 17], [-55, 55]],
      minZoom: 1.5,
      scrollZoom: true,
      touchZoomRotate: true,
      dragPan: true,
      dragRotate: false,
    });

    // Theme switch — when the user toggles Light↔Dark (or the OS
    // listener flips us in System mode) we swap `setStyle` here.
    // We use a `data-theme` observer on <html>; MapLibre takes
    // care of re-emitting `style.load` after `setStyle` resolves,
    // and our POI / choropleth layers are re-added inside the
    // existing `style.load` handler so markers and the choropleth
    // fill are preserved across the switch.
    //
    // We only react to `data-theme` (the attribute set by the
    // no-flash bootstrap + our own theme hook) — observing the
    // `class` attribute would also fire for unrelated class changes
    // (e.g. iOS Safari toggling "dark" on the document element for
    // status-bar styling), causing spurious basemap swaps.
    if (typeof MutationObserver !== "undefined") {
      const themeObserver = new MutationObserver(() => {
        const dataTheme = document.documentElement.getAttribute("data-theme");
        const isDark = dataTheme === "dark";
        const target = isDark ? darkStyle : lightStyle;
        try { map.setStyle(target); } catch { /* ignore transient errors */ }
      });
      themeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"],
      });
    }

    // Map-level empty click → let parent clear the selected POI profile
    // when the user clicks map empty space (was previously done via a
    // full-bleed transparent `<div className="absolute inset-0 z-20">`
    // which intercepted mousedown / wheel / touch and broke drag/zoom).
    // We check the POI layer: if it was not hit, it's a true empty click.
    // The state choropleth (RegionalStateLayer) and the city drilldown
    // (CityLayer) handle their own clicks via the layer-level `click`
    // binding they own; this handler only fires when neither was hit.
    map.on("click", (event) => {
      try {
        // Filter to layer IDs that actually exist in the current style.
        // setStyle() (theme switch) removes all custom layers, so
        // querying a stale layer ID raises
        // "The layer 'X' does not exist in the map's style".
        const styleLayerIds = new Set(
          (map.getStyle()?.layers ?? []).map((l) => l.id).filter(Boolean) as string[],
        );
        const candidates = ["pathos-universities-points"]
          .filter((id): id is string => !!id && styleLayerIds.has(id));
        if (candidates.length === 0) {
          emptyClickRef.current?.();
          return;
        }
        const hits = map.queryRenderedFeatures(event.point, { layers: candidates });
        if (hits.length === 0) {
          emptyClickRef.current?.();
        }
      } catch {
        // MapLibre's `queryRenderedFeatures` can throw before the
        // style has finished loading; ignore and let the event pass.
      }
    });

    // Navigation controls (zoom +/- and compass)
    map.addControl(new maplibregl.NavigationControl(), "top-left");
    // Compact attribution (bottom-right)
    map.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      "bottom-right",
    );

    // MapLibre caches the container size at instantiation. If the
    // container is still 0-height at this point (because the flex
    // chain above us hasn't laid out yet, e.g. MapShell → MapCanvas →
    // containerRef), the projection becomes degenerate and POI
    // markers all project to the same screen point. Force a resize
    // once the layout has had a chance to settle so the projection
    // gets correct dimensions. The ResizeObserver below handles
    // subsequent size changes.
    requestAnimationFrame(() => {
      try { map.resize(); } catch { /* ignore */ }
    });

    // Style loaded → map is interactive.
    //
    // Closing Patch v2: setMapReady(true) is now called SYNCHRONOUSLY
    // here (no rAF indirection). The previous version wrapped the
    // ready flip inside requestAnimationFrame() + a resize/jumpTo dance
    // that was meant to work around a stale-projection bug. Under the
    // current code path, that dance was being cancelled mid-flight by
    // the React Strict Mode / Fast Refresh rebuild caused by the
    // Suspense fallback mismatch in /app/map/page.tsx (F1). The chain
    // was the real reason `mapReady` stayed `false` indefinitely,
    // which in turn prevented the regional choropleth fill layer from
    // ever being installed.
    //
    // Layout projection is handled separately by the ResizeObserver
    // registered further down (it fires `map.resize() + map.fire("move")`
    // whenever the container size settles). Marking the map ready
    // here only gates "are MapLibre's APIs usable?" — projection is a
    // separate concern owned by the resize observer.
    map.on("load", () => {
      setMapReady(true);
    });

    // Style-load error — surface to console so devs can diagnose
    map.on("error", (e) => {
      // Suppress the post-setStyle race noise: when the user toggles
      // the theme, MapLibre removes every custom source/layer and
      // child effects (POI layer, choropleth, regional) call methods
      // on those sources/layers for a brief render frame before
      // noticing the swap. The MapLibre error is caught in those
      // effects' own try/catch; logging it again here just floods the
      // console. We only forward errors that look unrecoverable.
      const msg = String((e as { error?: unknown })?.error ?? "");
      const isTransientStyleSwapNoise =
        msg.includes("does not exist in the map's style") ||
        msg.includes("Style is not done loading");
      if (!isTransientStyleSwapNoise) {
        // eslint-disable-next-line no-console
        console.error("[MapCanvas] MapLibre error:", e.error);
      }
    });

    // ── Zoom → Granularity derivation ──────────────────────────────────────
    map.on("zoom", () => {
      const z = map.getZoom();
      let next: Granularity;
      if (z < STATE_MAX_ZOOM) {
        next = "state";
      } else if (z < COUNTY_MAX_ZOOM) {
        next = "county";
      } else {
        next = "city";
      }
      setGranularity((prev) => {
        if (prev !== next) {
          onGranularityChange?.(next);
        }
        return next;
      });
    });

    // ── View state sync ────────────────────────────────────────────────────
    const syncViewState = () => {
      const center = map.getCenter();
      const next: MapViewState = {
        longitude: center.lng,
        latitude: center.lat,
        zoom: map.getZoom(),
        bearing: map.getBearing(),
        pitch: map.getPitch(),
        activeMetricId,
        selectedUniversityId: null,
        selectedCampusPoiId: null,
        mode: "map",
        panelOpen: false,
      };
      setViewState(next);
      onViewStateChange?.(next);
    };

    map.on("moveend", syncViewState);

    mapRef.current = map;
    onMapInit?.(map);

    // ── Cleanup ────────────────────────────────────────────────────────────
    // Stage 7B-A.1 v3 (V3-D): the previous cleanup restored a captured
    // `origWarn` because we had monkey-patched `console.warn` to swallow
    // benign MapLibre style-diff warnings. That monkey-patch leaked across
    // remounts under React Strict Mode dev double-render (each mount
    // captured the *patched* `console.warn`, then the second cleanup
    // restored the first mount's patch — leaving console.warn suppressed
    // for the entire page lifetime). The monkey-patch has been removed
    // entirely; the cleanup is therefore a no-op for console.warn.
    // Benign style-diff warnings are now routed through MapLibre's own
    // `error` handler filter (above) and child-effect try/catch wrappers.
    return () => {
      map.remove();
      mapRef.current = null;
      initializedRef.current = false;
      setMapReady(false);
    };
    // MapLibre init runs exactly once (mount + unmount); re-running
    // it would destroy & recreate the entire map instance. We
    // intentionally exclude callback props from deps and rely on the
    // `*Ref.current` pattern (above) to read the latest values at
    // call time — see MapShell's `regionClickRef`, `emptyClickRef`,
    // `metricIdRef`, `regionMetricSetRef` for the up-to-date handles.
    // The disable covers `onMapInit` / `onViewStateChange` / etc.
    // that ESLint can't statically see as "intentionally excluded".
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Re-measure when the container resizes ─────────────────────────
  // MapLibre caches the container size at init; if the layout changes
  // height after init (e.g. flex chain propagation, browser resize, or
  // a parent collapsing) the canvas / canvas-container end up with
  // height=0 and POI markers fall outside the visible area. Calling
  // `map.resize()` after any size change recomputes the viewport and
  // a follow-up 'move' event forces MapLibre to re-project existing
  // markers (markers' transform style is not refreshed on resize
  // alone, only on move).
  useEffect(() => {
    const map = mapRef.current;
    const container = containerRef.current;
    if (!map || !container) return;
    const ro = new ResizeObserver(() => {
      try {
        map.resize();
        map.fire('move');
      } catch { /* map destroyed mid-tear-down */ }
    });
    ro.observe(container);
    return () => ro.disconnect();
  }, [mapReady]);

  // ── Render ──────────────────────────────────────────────────────────────────
  const isLoading = !mapReady;

  return (
    <MapContext.Provider value={contextValue}>
      <div
        className={`relative h-full w-full ${className ?? ""}`}
        role="region"
        aria-label="交互式留学地图 / Interactive Study-Abroad Map"
      >
        {/* ── Map container ────────────────────────────────────────────── */}
        <div
          ref={containerRef}
          data-map-canvas-root="true"
          className="h-full min-h-[400px] w-full rounded-lg border border-line bg-paper"
          aria-label="MapLibre 地图视窗"
        />

        {/* ── Loading overlay ──────────────────────────────────────────── */}
        {isLoading && (
          <div
            className="pointer-events-none absolute inset-0 z-map-modal flex items-center justify-center rounded-lg bg-paper/70 backdrop-blur-sm"
            role="status"
            aria-live="polite"
          >
            {loadingFallback ?? (
              <div className="flex items-center gap-2.5 rounded-lg border border-line bg-white/96 px-4 py-2.5 text-sm text-ink/62 shadow-panel">
                <Loader2
                  aria-hidden="true"
                  size={16}
                  className="animate-spin text-cobalt"
                />
                <span>加载地图中...</span>
                <span className="text-ink/36" lang="en">
                  Loading map...
                </span>
              </div>
            )}
          </div>
        )}

        {/* ── Error banner (map initialised but errored) ──────────────────
             Shown when the map object exists but encountered a fatal load
             error.  Currently a placeholder — MapLibre itself shows a
             degraded state; we add an unobtrusive banner.

             TODO: Replace with a real error boundary / retry button when
                   we have a proper error event pipeline.
        */}

        {/* ── Overlay children (metric tabs, legend, tooltip, etc.) ────── */}
        {children}

        {/* ── State hover tooltip is provided by RegionalStateLayer via
             the `children` overlay (RegionalHoverTooltip). It is no
             longer rendered here to avoid the dual-tooltip path that
             duplicated RegionalStateLayer's tooltip behaviour. */}



        {/* ── Granularity badge (bottom-right) ────────────────────────────
             Visible after map loads; shows current zoom-derived granularity.
        */}
        {mapReady && (
          <div
            className="pointer-events-none absolute bottom-3 right-3 z-map-basemap select-none"
            aria-hidden="true"
          >
            <span className="rounded-full border border-line bg-white/88 px-2.5 py-1 text-[11px] font-medium text-ink/56 backdrop-blur">
              {granularity === "state"
                ? "州级 / State"
                : granularity === "county"
                  ? "县级 / County"
                  : "市级 / City"}
            </span>
          </div>
        )}
      </div>
    </MapContext.Provider>
  );
}

// ── Exports ───────────────────────────────────────────────────────────────────

export default MapCanvas;





