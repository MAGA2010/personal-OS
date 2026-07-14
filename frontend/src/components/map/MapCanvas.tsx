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
import { METRIC_DEFINITIONS } from "@/lib/metrics";
import regionMetrics from "@/data/region-metrics.json";
import {
  interpolateGreens,
  interpolateRdBu,
  interpolateYlGn,
  interpolateOranges,
  interpolateOrRd,
  interpolateYlOrRd,
} from "d3-scale-chromatic";
import { feature } from "topojson-client";
import type { FeatureCollection, Geometry } from "geojson";

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
  "https://demotiles.maplibre.org/style.json";

/** Map centre: continental US. */
const INITIAL_CENTER: [number, number] = [-98.5, 39.8];

/** Starting zoom: full US view. */
const INITIAL_ZOOM = 4.0;

/** Minimum zoom before we revert to state-level granularity. */
const STATE_MAX_ZOOM = 6;

/** County-level band. */
const COUNTY_MAX_ZOOM = 9;

const CHOROPLETH_SOURCE_ID = "pathos-us-states";
const CHOROPLETH_FILL_LAYER_ID = "pathos-us-states-fill";
const CHOROPLETH_LINE_LAYER_ID = "pathos-us-states-line";
const STATE_TOPOJSON_URL = "/geography/us-states.topojson";
const DEFAULT_METRIC_ID: MetricId = "income";
const MISSING_REGION_COLOR = "rgba(21, 32, 37, 0.08)";

type TopologyWithStates = {
  objects: {
    states: unknown;
  };
};

type ChoroplethFeatureProperties = {
  name?: string;
  fipsCode: string;
  metricValue?: number;
  metricColor?: string;
};

type ChoroplethFeatureCollection = FeatureCollection<
  Geometry,
  ChoroplethFeatureProperties
>;

const COLOR_INTERPOLATORS: Record<string, (t: number) => string> = {
  greens: interpolateGreens,
  redblue: interpolateRdBu,
  tealgrn: interpolateYlGn,
  oranges: interpolateOranges,
  orangered: interpolateOrRd,
  ylorrd: interpolateYlOrRd,
};

function metricColor(metricId: MetricId, value?: number): string {
  if (value === undefined) return MISSING_REGION_COLOR;
  const metric = METRIC_DEFINITIONS[metricId];
  const t = Math.max(0, Math.min(1, value));
  const clipped = 0.08 + t * 0.84;
  const interpolator = COLOR_INTERPOLATORS[metric.colorScheme];
  return interpolator(metric.invertScale ? 1 - clipped : clipped);
}

function firstSymbolLayerId(map: maplibregl.Map): string | undefined {
  return map.getStyle().layers?.find((layer) => layer.type === "symbol")?.id;
}

function buildStateChoroplethData(
  topology: TopologyWithStates,
  metricId: MetricId,
): ChoroplethFeatureCollection {
  const collection = feature(
    topology as never,
    topology.objects.states as never,
  ) as unknown as ChoroplethFeatureCollection;

  const metricForMetricId = regionMetrics.records.filter((r) => r.metricId === metricId);
  const metricByFips = new Map(metricForMetricId.map((metric) => [metric.fipsCode, metric]));

  return {
    ...collection,
    features: collection.features.map((stateFeature) => {
      const fipsCode = String(stateFeature.id ?? "");
      const metric = metricByFips.get(fipsCode);
      return {
        ...stateFeature,
        properties: {
          ...(stateFeature.properties ?? {}),
          fipsCode,
          metricValue: metric?.value,
          metricColor: metricColor(metricId, metric?.value),
        },
      };
    }),
  };
}

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

  /** Called when a state choropleth region is clicked. */
  onRegionClick?: (fipsCode: string) => void;

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
  onRegionClick,
  children,
  loadingFallback,
  interactiveLayerIds,
  activeMetricId,
}: MapCanvasProps) {
  // ── Refs ──
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const initializedRef = useRef(false);
  const topologyRef = useRef<TopologyWithStates | null>(null);
  const regionClickRef = useRef<MapCanvasProps["onRegionClick"]>(onRegionClick);
  const metricIdRef = useRef<MetricId>(DEFAULT_METRIC_ID);

  // ── State ──
  const [tooltipData, setTooltipData] = useState<{
    x: number;
    y: number;
    name: string;
    displayValue: string;
  } | null>(null);
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


  useEffect(() => {
    regionClickRef.current = onRegionClick;
  }, [onRegionClick]);
  useEffect(() => {
    metricIdRef.current = activeMetricId ?? DEFAULT_METRIC_ID;
  }, [activeMetricId]);

  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    const map = mapRef.current;
    const metricId = activeMetricId ?? DEFAULT_METRIC_ID;
    let cancelled = false;

    async function loadChoropleth() {
      try {
        if (!topologyRef.current) {
          const response = await fetch(STATE_TOPOJSON_URL);
          if (!response.ok) throw new Error("Failed to load " + STATE_TOPOJSON_URL);
          topologyRef.current = (await response.json()) as TopologyWithStates;
        }
        if (cancelled || !topologyRef.current) return;
        const data = buildStateChoroplethData(topologyRef.current, metricId);
        const existingSource = map.getSource(CHOROPLETH_SOURCE_ID);
        if (existingSource) {
          (existingSource as maplibregl.GeoJSONSource).setData(data);
        } else {
          map.addSource(CHOROPLETH_SOURCE_ID, { type: "geojson", data });
          map.addLayer({ id: CHOROPLETH_FILL_LAYER_ID, type: "fill", source: CHOROPLETH_SOURCE_ID, paint: { "fill-color": ["coalesce", ["get", "metricColor"], MISSING_REGION_COLOR], "fill-opacity": 0.58 } });
          map.addLayer({ id: CHOROPLETH_LINE_LAYER_ID, type: "line", source: CHOROPLETH_SOURCE_ID, paint: { "line-color": "rgba(21, 32, 37, 0.32)", "line-width": 0.7 } });
         map.on("mouseenter", CHOROPLETH_FILL_LAYER_ID, () => { map.getCanvas().style.cursor = "pointer"; });
         map.on("mouseleave", CHOROPLETH_FILL_LAYER_ID, () => { map.getCanvas().style.cursor = ""; });
            setTooltipData(null);
         map.on("mousemove", CHOROPLETH_FILL_LAYER_ID, (e) => {
            if (!e.features || e.features.length === 0) return;
            const props = e.features[0].properties as Record<string, any>;
            const currentMetricId = metricIdRef.current;
            const metricRecord = (regionMetrics.records as any[]).find(
              (r: any) => r.fipsCode === props.fipsCode && r.metricId === currentMetricId
            );
            setTooltipData({
              x: e.point.x,
              y: e.point.y,
              name: props.name || props.fipsCode,
              displayValue: metricRecord?.displayValue ?? "N/A",
            });
          });
         map.on("click", CHOROPLETH_FILL_LAYER_ID, (event) => {
            const fipsCode = event.features?.[0]?.properties?.fipsCode;
            if (typeof fipsCode === "string") regionClickRef.current?.(fipsCode);
          });
        }
      } catch (error) {
        console.error("[MapCanvas] Failed to render state choropleth:", error);
      }
    }
    void loadChoropleth();
    return () => { cancelled = true; };
  }, [activeMetricId, mapReady]);
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
      // Restrict view to US only
      maxBounds: [[-135, 17], [-55, 55]],
      minZoom: 1.5,
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
       {/* State hover tooltip */}
       {tooltipData && (
         <div className="pointer-events-none absolute z-50 rounded border border-line bg-white/85 px-1.5 py-0.5 text-[10px] leading-tight shadow-sm backdrop-blur" style={{ left: tooltipData.x + 10, top: tooltipData.y - 10 }}>
           <span className="font-medium text-ink">{tooltipData.name}</span>
           <span className="text-ink/40 mx-0.5">·</span><span className="text-ink/60">{tooltipData.displayValue}</span>
         </div>
       )}



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






