// PathOS Stage 7B-A — Map Provider Abstraction
//
// Provider-neutral contracts so the rest of the app never imports
// `maplibre-gl` or the Baidu JSAPI directly. Both adapters are
// expected to implement the same surface area; UI components must
// only consume these interfaces.
//
// Two providers are wired today:
//
//   - `maplibre`  — fully implemented in this round via
//                   MapLibreProviderAdapter; preserves the existing
//                   MapCanvas behavior exactly.
//
//   - `baidu`     — Experimental; activates only when
//                   NEXT_PUBLIC_BAIDU_MAP_AK is configured. While AK
//                   is missing the adapter stays in the
//                   "ak-missing" state and the host falls back to
//                   MapLibre. See baidu/BaiduMapProviderAdapter.ts.

export type MapProviderId = "maplibre" | "baidu";

export type ThemeMode = "light" | "dark" | "system";

export interface MapViewState {
  center: [number, number]; // [lng, lat] in WGS84
  zoom: number;
  bearing?: number;
  pitch?: number;
}

export interface MapMoveEvent {
  center: [number, number];
  zoom: number;
}

export interface MapClickEvent {
  lngLat: [number, number];
  /** true if the click landed on a UI overlay rather than the basemap. */
  onOverlay: boolean;
}

export type MapProviderErrorCode =
  | "ak-missing"
  | "ak-invalid"
  | "referer-invalid"
  | "service-disabled"
  | "overseas-unavailable"
  | "quota-exceeded"
  | "script-timeout"
  | "script-load-error"
  | "tile-failure"
  | "not-implemented";

export interface MapProviderError {
  code: MapProviderErrorCode;
  message: string;
  /** Optional user-actionable hint; never include the AK value. */
  hint?: string;
}

export interface MapMarkerSpec {
  id: string;
  lng: number;
  lat: number;
  /** Short label visible on the map (≤ 8 chars). */
  shortLabel: string;
  /** Full name shown on hover or in tooltip. */
  fullLabel: string;
  /** Optional payload passed back to click handlers. */
  payload?: unknown;
}

export interface RegionalFillSpec {
  /** Stable FIPS-like identifier (e.g. "06" for California). */
  geoId: string;
  /** Polygon ring in WGS84. Outer ring only is sufficient for states. */
  ring: Array<[number, number]>;
  /** Normalized 0–1 value driving color. null = missing (gray). */
  value: number | null;
  /** Whether this region is currently hovered. */
  hovered?: boolean;
  /** Whether this region is currently selected. */
  selected?: boolean;
}

/**
 * Provider-neutral adapter. Every adapter must implement this surface
 * (some methods may be no-ops when the underlying engine lacks the
 * capability, but they must still exist and return without throwing).
 */
export interface MapProviderAdapter {
  readonly id: MapProviderId;

  /** Called once with the host container element. Returns a dispose fn. */
  initialize(container: HTMLElement, options: {
    theme: ThemeMode;
    view: MapViewState;
    onReady?: () => void;
    onMove?: (e: MapMoveEvent) => void;
    onMoveEnd?: (e: MapMoveEvent) => void;
    onClick?: (e: MapClickEvent) => void;
    onError?: (e: MapProviderError) => void;
  }): () => void;

  destroy(): void;

  setCenter(center: [number, number], zoom?: number): void;
  setZoom(zoom: number): void;
  flyTo(view: MapViewState, opts?: { durationMs?: number }): void;
  fitBounds(bounds: [[number, number], [number, number]], padding?: number): void;

  getCenter(): [number, number] | null;
  getZoom(): number | null;

  setTheme(theme: ThemeMode): void;
  resize(): void;

  project(lngLat: [number, number]): { x: number; y: number } | null;
  unproject(point: { x: number; y: number }): [number, number] | null;

  /** University POI marker API. */
  addUniversityMarkers(markers: MapMarkerSpec[]): void;
  updateUniversityMarkers(markers: MapMarkerSpec[]): void;
  removeUniversityMarkers(ids: string[]): void;

  /** Regional choropleth API. The adapter is expected to render the
   *  single active metric at a time; switching metricId should
   *  update fills in place rather than stacking 204 overlay objects. */
  setRegionalFill(metricId: string, specs: RegionalFillSpec[]): void;
  clearRegionalFill(): void;

  /** Select / hover highlight on a regional feature. */
  setSelectedRegion(geoId: string | null): void;
  setHoveredRegion(geoId: string | null): void;
}

/**
 * Configuration consumed by MapProviderHost to choose an adapter.
 *
 * Resolution order:
 *   1. `NEXT_PUBLIC_PATHOS_MAP_PROVIDER` env (if set and recognized)
 *   2. Else `"maplibre"` (the safe default)
 *
 * A `baidu` config without an AK silently falls back to MapLibre; the
 * host emits `ak-missing` to its onError callback so the UI can show
 * a banner explaining the configuration gap.
 */
export interface MapProviderConfig {
  id: MapProviderId;
  baiduAk: string | null;
  theme: ThemeMode;
}

export function resolveMapProviderId(raw: string | undefined | null): MapProviderId {
  if (raw === "baidu") return "baidu";
  return "maplibre"; // default — safe fallback for any unrecognized value
}

export function resolveMapProviderConfig(env: {
  provider?: string | undefined;
  baiduAk?: string | undefined;
}): MapProviderConfig {
  const id = resolveMapProviderId(env.provider);
  const baiduAk = env.baiduAk && env.baiduAk.trim().length > 0 ? env.baiduAk.trim() : null;
  return {
    id,
    baiduAk,
    theme: "system",
  };
}