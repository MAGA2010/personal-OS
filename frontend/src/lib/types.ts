// ═══════════════════════════════════════════════════════════════
// PathOS · Map Module — Shared TypeScript Types
// ═══════════════════════════════════════════════════════════════
//
// This file defines every shape consumed or produced by the map
// module: metric layers, choropleth regions, university POIs,
// campus landmarks, news articles, map view state, and tooltip
// payloads.
//
// Conventions
// ───────────
// • Chinese labels are primary (`label`); English is the fallback
//   (`labelEn`).  Every UI‑visible string should follow this shape.
// • Placeholder data / mock values are tagged with:
//     // TODO: Replace with real {metric name} data
//     // TODO: Connect to Supabase when available
// • MapLibre‑specific types (like `LngLatBoundsLike`) are imported
//   dynamically inside components; this file stays framework‑agnostic.
// • Tailwind color tokens used across the UI:
//     ink        #152025    – body text, active states
//     paper      #f6f3ed    – page background
//     panel      #fffaf1    – card / panel background
//     line       #d9d1c3    – borders, dividers
//     jade       #23766b    – success / positive
//     persimmon  #c45f36    – warning / highlight
//     cobalt     #315d9f    – info / link / accent
//
// ═══════════════════════════════════════════════════════════════

// ── Identity / Perspective ──────────────────────────────────────

/** The two personas the advisory platform serves. */
export type Perspective = "student" | "parent";

/** Simplified affordability bucket for quick filtering. */
export type Affordability = "good" | "stretch" | "over";

// ── Metric System ───────────────────────────────────────────────

/**
 * Six metric layers the choropleth map can render.
 *
 * TODO: Confirm exact source for each metric (ACS, IPEDS, IIE, etc.)
 * TODO: Connect to Supabase when available — current values are mock
 */
export type MetricId =
  | "income"
  | "safety"
  | "toefl"
  | "sat"
  | "admission_rate"
  | "chinese_population";

/** Choropleth granularity controlled by zoom level. */
export type Granularity = "state" | "county" | "city";

/**
 * Color scheme identifiers mapped to d3-scale-chromatic interpolators.
 * Used by `color-ramp.ts` to build MapLibre paint expressions.
 */
export type ColorSchemeId =
  | "greens"      // income
  | "redblue"     // safety
  | "blues"       // TOEFL
  | "purples"     // SAT
  | "orangered"   // admission rate
  | "ylorrd";     // Chinese population

// ── Metric Definition ───────────────────────────────────────────

/**
 * Human‑readable metadata for one metric layer.
 * Displayed in the legend, metric‑tab bar, and info panel.
 */
export interface MetricDefinition {
  /** Machine‑readable key. */
  id: MetricId;

  /** Chinese label (primary display language). */
  label: string;

  /** English label (secondary / accessibility fallback). */
  labelEn: string;

  /** Abbreviated unit shown in the legend, e.g. "$", "/100k", "%". */
  unit: string;

  /** D3 color scheme to use for the choropleth fill. */
  colorScheme: ColorSchemeId;

  /**
   * When `true` the color ramp is reversed so that "worse" values
   * map to the darker/stronger end (e.g. crime rate → safety).
   */
  invertScale: boolean;

  /** One‑sentence description (Chinese) shown in tooltips / info. */
  description: string;
}

// ── Region / Choropleth Data ────────────────────────────────────

/**
 * A single metric value attached to a geographic region.
 *
 * One region may carry many `RegionMetric` rows — one per
 * `metricId`.  The `value` field is always **0‑1 normalised**
 * so the choropleth layer uses a uniform data range.
 */
export interface RegionMetric {
  /** FIPS / GEOID for this polygon (string to preserve leading zeros). */
  fipsCode: string;

  /** Granularity that produced this record. */
  granularity: Granularity;

  /** Which metric this value belongs to. */
  metricId: MetricId;

  /** Normalised value 0‑1 for the choropleth ramp. */
  value: number;

  /** Original (un‑normalised) value for display formatting. */
  rawValue: number;

  /** Pre‑formatted string ready for tooltip / sidebar display. */
  displayValue: string;

  /** Data‑source year (e.g. 2025 ACS estimates). */
  year: number;
}

/**
 * A geographic region (state, county, or city) as it appears on the
 * choropleth map.  This is the "fat" view used by the sidebar and
 * tooltip — it merges boundary metadata with all available metrics.
 *
 * TODO: Replace `metrics` with live Supabase query once region tables exist
 */
export interface MapRegion {
  /** FIPS / GEOID. */
  fipsCode: string;

  /** Human‑readable Chinese name (e.g. "加利福尼亚州"). */
  name: string;

  /** English name. */
  nameEn: string;

  /** State abbreviation (2‑letter, e.g. "CA") — only for county/city. */
  stateAbbr?: string;

  granularity: Granularity;

  /** All metrics available for this region (empty array until loaded). */
  metrics: RegionMetric[];

  /** Total number of universities within this region. */
  universityCount: number;
}

// ── Metric Layer (MapLibre paint configuration) ─────────────────

/**
 * A fully‑resolved metric layer ready to be applied to a MapLibre
 * source.  Built from a `MetricDefinition` + live data range.
 */
export interface MetricLayer {
  /** The metric being rendered. */
  metricId: MetricId;

  /** Human‑readable Chinese label for the layer. */
  label: string;

  /** English label for the layer. */
  labelEn: string;

  /** Unit abbreviation. */
  unit: string;

  /** D3 colour scheme used for the choropleth fill. */
  colorScheme: ColorSchemeId;

  /** Whether the colour ramp is inverted. */
  invertScale: boolean;

  /** The lowest raw value across all regions (for legend labels). */
  minRawValue: number;

  /** The highest raw value across all regions. */
  maxRawValue: number;

  /** Formatted min label ready for the legend, e.g. "1050". */
  minLabel: string;

  /** Formatted max label ready for the legend, e.g. "1550". */
  maxLabel: string;

  /** Is the underlying metric data still loading? */
  isLoading: boolean;

  /** Error message — only set when a fetch / parse error occurs. */
  error?: string;
}

// ── University & Campus POI Types ───────────────────────────────

/**
 * Legacy university shape used by the advisory workbench.
 * @deprecated Migrate to `UniversityPOI` for map rendering.
 */
export type University = {
  id: string;
  name: string;
  chineseName: string;
  country: string;
  city: string;
  /** @deprecated use latitude/longitude instead */
  mapPosition: {
    x: number;
    y: number;
  };
  rankingBand: string;
  annualCostRmb: number;
  safetyScore: number;
  recognitionScore: number;
  chineseCommunity: "low" | "medium" | "high";
  directFlight: boolean;
  cssa: boolean;
  postStudyVisa: string;
  programs: string[];
  parentHighlights: string[];
  studentHighlights: string[];
  verifiedAt: string;
  sourceCount: number;
};

/** Numeric tier used for POI clustering and icon sizing. */
export type RankingTier = "top20" | "top50" | "top100" | "other";

/** Chinese community density for filtering. */
export type ChineseCommunityLevel = "low" | "medium" | "high";

/**
 * Primary university POI for the interactive map.
 *
 * TODO: Connect to Supabase `universities` table when available
 * TODO: Replace campusImages & nearby with real API responses
 */
export interface UniversityPOI {
  id: string;
  name: string;
  chineseName: string;
  country: string;
  city: string;
  latitude: number;
  longitude: number;
  rankingBand: string;
  rankingTier: RankingTier;
  annualCostRmb: number;
  safetyScore: number; // 0‑100
  recognitionScore: number; // 0‑100
  chineseCommunity: ChineseCommunityLevel;
  directFlight: boolean;
  postStudyVisa: string;
  programs: string[];
  parentHighlights: string[];
  studentHighlights: string[];
  verifiedAt: string;
  sourceCount: number;

  // ── Campus Experience ──
  /** Google / MapLibre Street View panorama ID for this campus. */
  streetviewPanoId?: string;

  /** Curated campus images shown in the POI card. */
  campusImages: CampusImage[];

  /** University logo URL (for POI marker & detail card). */
  logoUrl?: string;

  // ── Nearby Amenities ──
  nearby: UniversityNearby;
}

/** Amenities within walking / short‑transit distance of campus. */
export interface UniversityNearby {
  /** Number of subway / metro stations within 1 km. */
  subwayStations: number;

  /** Number of Chinese restaurants within 2 km. */
  chineseRestaurants: number;

  /** Number of Asian grocery stores within 3 km. */
  asianGroceries: number;

  /** Average monthly rent (RMB) for a 1‑bedroom near campus. */
  avgRentRmb: number;
}

/** A labelled photograph of a campus landmark. */
export interface CampusImage {
  /** URL to the image asset (CDN / S3). */
  url: string;

  /** Chinese label, e.g. "主图书馆". */
  label: string;

  /** Optional geotag for placing on the map. */
  latitude?: number;
  longitude?: number;
}

/**
 * A discrete point‑of‑interest on a university campus.
 * Used for the campus‑detail / street‑view drill‑in experience.
 *
 * TODO: Connect to Supabase `campus_pois` table when available
 */
export interface CampusPOI {
  /** Unique POI identifier. */
  id: string;

  /** Owning university ID. */
  universityId: string;

  /** Chinese name, e.g. "工程学院". */
  name: string;

  /** English name, e.g. "College of Engineering". */
  nameEn: string;

  /** Category determines the map icon and filter group. */
  type:
    | "library"
    | "engineering"
    | "business"
    | "student_center"
    | "dining"
    | "dormitory"
    | "other";

  latitude: number;
  longitude: number;

  /** Street View panorama ID for immersive preview. */
  streetviewPanoId?: string;
}

// ── News / Sidebar Types ────────────────────────────────────────

/** Category tags used to filter the news feed. */
export type NewsCategory =
  | "admissions"
  | "visa"
  | "ranking"
  | "life"
  | "career"
  | "policy";

/**
 * A single news / advisory article shown in the sidebar feed.
 *
 * TODO: Connect to Supabase `news_articles` table when available
 * TODO: Replace imageUrl with real CMS / CDN URLs
 */
export interface NewsArticle {
  id: string;

  /** Chinese title (primary). */
  title: string;

  /** English title (fallback). */
  titleEn?: string;

  /** Two‑line Chinese summary. */
  summary: string;

  /** Publisher / source name, e.g. "US News", "EIC Education". */
  source: string;

  /** Canonical link to the full article. */
  url: string;

  /** ISO‑8601 publication date. */
  publishedAt: string;

  /** Thumbnail / hero image URL. */
  imageUrl?: string;

  category: NewsCategory;
}

// ── Map View State ──────────────────────────────────────────────

/**
 * Serializable snapshot of the map viewport.
 * Used to restore map state from URL search params, localStorage,
 * or shared links.  All fields are optional so partial updates
 * (e.g. zoom‑only) are supported.
 *
 * TODO: Persist view state in URL search params via nuqs or next-usequerystate
 */
export interface MapViewState {
  /** Longitude of map centre. */
  longitude?: number;

  /** Latitude of map centre. */
  latitude?: number;

  /** Zoom level (MapLibre: 0‑22). */
  zoom?: number;

  /** Bearing in degrees (0 = north‑up). */
  bearing?: number;

  /** Pitch in degrees (0 = top‑down). */
  pitch?: number;

  /** Active metric layer shown on the choropleth. */
  activeMetricId?: MetricId;

  /** Currently selected university POI ID (null = none). */
  selectedUniversityId?: string | null;

  /** Currently selected campus POI ID (null = none). */
  selectedCampusPoiId?: string | null;

  /** Active map mode: standard choropleth or street‑view immersive. */
  mode?: "map" | "streetview";

  /** Sidebar panel visibility. */
  panelOpen?: boolean;
}

// ── Map Interaction Types ───────────────────────────────────────

/**
 * Transient tooltip payload computed on `mousemove` over a choropleth
 * region.  Displayed via `RegionTooltip` component.
 */
export interface MapTooltip {
  /** Pixel‑x of the cursor relative to the map container. */
  x: number;

  /** Pixel‑y of the cursor relative to the map container. */
  y: number;

  /** Human‑readable region name (Chinese when available). */
  regionName: string;

  /** Numeric metric value (null when data is missing). */
  metricValue: number | null;

  /** Pre‑formatted display string, e.g. "$85k", "32.5%". */
  displayValue: string;
}

/** Top‑level map display mode. */
export type MapViewMode = "map" | "streetview";

// ── Map Filter State ────────────────────────────────────────────

/**
 * User‑controlled filters that narrow the POI set and data overlay.
 * Kept separate from `MapViewState` because filters do not represent
 * viewport state — they are application‑level UI state.
 *
 * TODO: Wire filter controls to this shape in the sidebar panel
 */
export interface MapFilters {
  /** Only show universities in this ranking tier (null = all). */
  rankingTier: RankingTier | null;

  /** Only show universities with this max annual cost (null = all). */
  maxCostRmb: number | null;

  /** Only show universities with at least this safety score. */
  minSafetyScore: number | null;

  /** Only show universities in these countries (empty = all). */
  countries: string[];

  /** Only show universities with direct flights from China. */
  directFlightOnly: boolean;

  /** Only show universities with a Chinese student association. */
  cssaOnly: boolean;
}

// ── POI Clustering (Phase 3) ────────────────────────────────────

/**
 * A cluster aggregate produced by supercluster / MapLibre cluster
 * source.  Displayed as a numbered circle on the map.
 *
 * TODO: Replace with real supercluster integration in Phase 3
 */
export interface POICluster {
  id: string;
  latitude: number;
  longitude: number;
  /** Number of universities collapsed into this cluster. */
  count: number;
  /** Average metric value for the cluster (for colouring). */
  averageMetricValue?: number;
  /** IDs of the aggregated POIs (for expansion on click). */
  poiIds: string[];
}

// ── Map Layer Config (MapLibre style helpers) ───────────────────

/**
 * Describes a named MapLibre layer within the style spec.
 * Used internally by `choropleth-map.tsx` for layer ordering.
 */
export interface MapLayerConfig {
  /** Unique layer ID within the MapLibre style. */
  id: string;

  /** MapLibre layer type. */
  type: "fill" | "line" | "symbol" | "circle" | "heatmap" | "raster";

  /** Source ID this layer draws from. */
  sourceId: string;

  /** Insert before this layer ID (undefined = append to end). */
  beforeId?: string;
}

// ── Street View / Campus Immersive (Phase 4) ────────────────────

/**
 * Campus immersive view state used by the street‑view overlay
 * component.  Activated when the user clicks a campus POI or
 * toggles `MapViewMode` to `"streetview"`.
 *
 * TODO: Wire to Google Street View / MapLibre GL JS Street View API in Phase 4
 */
export interface StreetViewState {
  /** Whether the immersive panel is active. */
  active: boolean;

  /** Pano ID for the 360° view or street‑view widget. */
  panoId: string | null;

  /** University POI this immersive session is anchored to. */
  universityId: string | null;

  /** Campus POI currently in focus (null = general campus view). */
  campusPoiId: string | null;
}

// ── API Response Shapes (Phase 4+) ──────────────────────────────

/**
 * Generic paginated API response envelope.
 * Used for university list, news articles, etc.
 *
 * TODO: Connect to Supabase REST / PostgREST responses when available
 */
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

/**
 * API response for a single university detail query.
 *
 * TODO: Connect to Supabase `universities` table + joined relations
 */
export interface UniversityDetailResponse {
  university: UniversityPOI;
  /** Campus landmarks for the drill‑in view. */
  campusPois: CampusPOI[];
  /** Neighbouring universities within 50 km. */
  nearbyUniversities: UniversityPOI[];
  /** Regional metrics for the university's county / city. */
  regionMetrics: RegionMetric[];
}
