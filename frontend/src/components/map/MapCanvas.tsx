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
import { MapPin, Loader2 } from "lucide-react";
import type { MapViewState, Granularity, MetricId } from "@/lib/types";

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

/** Free CARTO Positron raster tile style — no API key needed. */
const DEFAULT_STYLE_URL =
  "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

/** Map centre: continental US. */
const INITIAL_CENTER: [number, number] = [-98.5, 39.8];

/** Starting zoom: full US view. */
const INITIAL_ZOOM = 3.5;

/** Minimum zoom before we revert to state-level granularity. */
const STATE_MAX_ZOOM = 6;

/** County-level band. */
const COUNTY_MAX_ZOOM = 9;

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

  /** Override the default tile style (e.g. a MapTiler or self-hosted URL). */
  styleUrl?: string;

  /** Override the initial centre coordinate. */
  initialCenter?: [number, number];

  /** Override the initial zoom level. */
  initialZoom?: number;

  /** Called every time the viewport moves (debounced). */
  onViewStateChange?: (state: MapViewState) => void;

  /** Called when granularity flips due to zoom crossing a threshold. */
  onGranularityChange?: (granularity: Granularity) => void;

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
}

// ── Component ─────────────────────────────────────────────────────────────────

export function MapCanvas({
  className,
  styleUrl = DEFAULT_STYLE_URL,
  initialCenter = INITIAL_CENTER,
  initialZoom = INITIAL_ZOOM,
  onViewStateChange,
  onGranularityChange,
  children,
  loadingFallback,
  interactiveLayerIds,
  activeMetricId,
}: MapCanvasProps) {
  // ── Refs ──
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const initializedRef = useRef(false);

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

  // ── Initialise / destroy MapLibre ─────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || initializedRef.current) return;
    initializedRef.current = true;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: styleUrl,
      center: initialCenter,
      zoom: initialZoom,
      attributionControl: false,
    });

    // Navigation controls (zoom +/- and compass)
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    // Compact attribution (bottom-right)
    map.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      "bottom-right",
    );

    // Style loaded → map is interactive
    map.on("load", () => {
      setMapReady(true);
    });

    // Style-load error — surface to console so devs can diagnose
    map.on("error", (e) => {
      console.error("[MapCanvas] MapLibre error:", e.error);
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

    // ── Cleanup ────────────────────────────────────────────────────────────
    return () => {
      map.remove();
      mapRef.current = null;
      initializedRef.current = false;
      setMapReady(false);
    };
    // Only run on mount/unmount — style changes happen via map.setStyle()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Render ──────────────────────────────────────────────────────────────────
  const isLoading = !mapReady;

  return (
    <MapContext.Provider value={contextValue}>
      <div
        className={`relative ${className ?? ""}`}
        role="region"
        aria-label="交互式留学地图 / Interactive Study-Abroad Map"
      >
        {/* ── Map container ────────────────────────────────────────────── */}
        <div
          ref={containerRef}
          className="h-full min-h-[400px] w-full rounded-lg border border-line bg-paper"
          aria-label="MapLibre 地图视窗"
        />

        {/* ── Loading overlay ──────────────────────────────────────────── */}
        {isLoading && (
          <div
            className="absolute inset-0 z-20 flex items-center justify-center rounded-lg bg-paper/70 backdrop-blur-sm"
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

        {/* ── Granularity badge (bottom-right) ────────────────────────────
             Visible after map loads; shows current zoom-derived granularity.
        */}
        {mapReady && (
          <div
            className="pointer-events-none absolute bottom-3 right-3 z-10 select-none"
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

        {/* ── Placeholder: choropleth layer injection point ─────────────────
             Rendered as an invisible marker.  When the choropleth hook is
             ready, import <ChoroplethLayer /> here and pass:
               • boundaries  (FeatureCollection from useBoundaries)
               • metrics     (RegionMetric[] from useMetrics)
               • metricId    (MetricId active layer)

             TODO: Replace with <ChoroplethLayer /> component
             TODO: Connect to Supabase when available

             Expected data shape for a single region when the choropleth
             layer is wired:
               {
                 fipsCode: "06",            // FIPS / GEOID string
                 granularity: "state",       // state | county | city
                 metricId: "income",         // MetricId
                 value: 0.90,               // 0–1 normalised
                 rawValue: 135000,          // actual $ or score
                 displayValue: "$135k",     // pre-formatted
                 year: 2025,                // data vintage
               }
        */}
        {/*
          TODO: Uncomment when ChoroplethLayer is implemented:
          <ChoroplethLayer
            boundaries={boundaries}
            metrics={metrics}
            metricId={activeMetricId}
            interactiveLayerIds={interactiveLayerIds}
          />
        */}

        {/* ── Placeholder: POI marker injection point ────────────────────────
             When the POI layer is ready, import <POIMarkerLayer /> here.

             TODO: Replace with <POIMarkerLayer /> component
             TODO: Connect to Supabase `universities` table when available

             Expected data shape for a single university POI:
               {
                 id: "harvard-university",
                 name: "Harvard University",
                 chineseName: "哈佛大学",
                 latitude: 42.3770,
                 longitude: -71.1167,
                 rankingTier: "top20",
                 annualCostRmb: 560000,
                 safetyScore: 78,
                 recognitionScore: 98,
                 chineseCommunity: "high",
               }
        */}
        {/*
          TODO: Uncomment when POIMarkerLayer is implemented:
          <POIMarkerLayer
            pois={universityPois}
            selectedId={selectedUniversityId}
            onSelect={setSelectedUniversityId}
            filters={mapFilters}
          />
        */}
      </div>
    </MapContext.Provider>
  );
}

// ── Exports ───────────────────────────────────────────────────────────────────

export default MapCanvas;
