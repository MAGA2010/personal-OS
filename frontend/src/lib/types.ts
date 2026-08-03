// 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?// PathOS 路 Map Module 鈥?Shared TypeScript Types
// 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?//
// This file defines every shape consumed or produced by the map
// module: metric layers, choropleth regions, university POIs,
// campus landmarks, news articles, map view state, and tooltip
// payloads.
//
// Conventions
// 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
// 鈥?Chinese labels are primary (`label`); English is the fallback
//   (`labelEn`).  Every UI鈥憊isible string should follow this shape.
// 鈥?Placeholder data / mock values are tagged with:
//     // TODO: Replace with real {metric name} data
//     // TODO: Connect to Supabase when available
// 鈥?MapLibre鈥憇pecific types (like `LngLatBoundsLike`) are imported
//   dynamically inside components; this file stays framework鈥慳gnostic.
// 鈥?Tailwind color tokens used across the UI:
//     ink        #152025    鈥?body text, active states
//     paper      #f6f3ed    鈥?page background
//     panel      #fffaf1    鈥?card / panel background
//     line       #d9d1c3    鈥?borders, dividers
//     jade       #23766b    鈥?success / positive
//     persimmon  #c45f36    鈥?warning / highlight
//     cobalt     #315d9f    鈥?info / link / accent
//
// 鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺?
// 鈹€鈹€ Identity / Perspective 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

/** The two personas the advisory platform serves. */
export type Perspective = "student" | "parent";

/** Simplified affordability bucket for quick filtering. */
export type Affordability = "good" | "stretch" | "over";

// 鈹€鈹€ Metric System 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

/**
 * Six metric layers the choropleth map can render.
 *
 * TODO: Confirm exact source for each metric (ACS, IPEDS, IIE, etc.)
 * TODO: Connect to Supabase when available 鈥?current values are mock
 */
export type MetricId =
  | "income"
  | "safety"
  | "employment"
  | "cost"
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
  | "tealgrn"     // employment
  | "oranges"     // cost
  | "orangered"   // admission rate
  | "ylorrd";     // Chinese population

// 鈹€鈹€ Metric Definition 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

/**
 * Human鈥憆eadable metadata for one metric layer.
 * Displayed in the legend, metric鈥憈ab bar, and info panel.
 */
export interface MetricDefinition {
  /** Machine鈥憆eadable key. */
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
   * map to the darker/stronger end (e.g. crime rate 鈫?safety).
   */
  invertScale: boolean;

  /** One鈥憇entence description (Chinese) shown in tooltips / info. */
  description: string;
}

// 鈹€鈹€ Region / Choropleth Data 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

/**
 * A single metric value attached to a geographic region.
 *
 * One region may carry many `RegionMetric` rows 鈥?one per
 * `metricId`.  The `value` field is always **0鈥? normalised**
 * so the choropleth layer uses a uniform data range.
 */
export interface RegionMetric {
  /** FIPS / GEOID for this polygon (string to preserve leading zeros). */
  fipsCode: string;

  /** Granularity that produced this record. */
  granularity: Granularity;

  /** Which metric this value belongs to. */
  metricId: MetricId;

  /** Normalised value 0鈥? for the choropleth ramp. */
  value: number;

  /** Original (un鈥憂ormalised) value for display formatting. */
  rawValue: number;

  /** Pre鈥慺ormatted string ready for tooltip / sidebar display. */
  displayValue: string;

  /** Data鈥憇ource year (e.g. 2025 ACS estimates). */
  year: number;
}

/**
 * A geographic region (state, county, or city) as it appears on the
 * choropleth map.  This is the "fat" view used by the sidebar and
 * tooltip 鈥?it merges boundary metadata with all available metrics.
 *
 * TODO: Replace `metrics` with live Supabase query once region tables exist
 */
export interface MapRegion {
  /** FIPS / GEOID. */
  fipsCode: string;

  /** Human鈥憆eadable Chinese name (e.g. "鍔犲埄绂忓凹浜氬窞"). */
  name: string;

  /** English name. */
  nameEn: string;

  /** State abbreviation (2鈥憀etter, e.g. "CA") 鈥?only for county/city. */
  stateAbbr?: string;

  granularity: Granularity;

  /** All metrics available for this region (empty array until loaded). */
  metrics: RegionMetric[];

  /** Total number of universities within this region. */
  universityCount: number;
}

// 鈹€鈹€ Metric Layer (MapLibre paint configuration) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

/**
 * A fully鈥憆esolved metric layer ready to be applied to a MapLibre
 * source.  Built from a `MetricDefinition` + live data range.
 */
export interface MetricLayer {
  /** The metric being rendered. */
  metricId: MetricId;

  /** Human鈥憆eadable Chinese label for the layer. */
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

  /** Error message 鈥?only set when a fetch / parse error occurs. */
  error?: string;
}

// 鈹€鈹€ University & Campus POI Types 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

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
  // Gate-bloker repair #RG-P0-B: legacy POI fields used to be
  // non-nullable, so the legacy mapper had to zero-fill them and
  // downstream components rendered Y NaN / 0/100 / "low" / (0,0).
  // Making them nullable means consumers can no longer paper over
  // missing values with `?? 0`; instead they render an empty-state
  // label such as "学费数据补充中".
  latitude: number | null;
  longitude: number | null;
  rankingBand: string;
  rankingTier: RankingTier;
  annualCostRmb: number | null;
  safetyScore: number | null; // 0-100
  recognitionScore: number | null; // 0-100
  chineseCommunity: ChineseCommunityLevel | null;
  directFlight: boolean;
  postStudyVisa: string;
  programs: string[];
  parentHighlights: string[];
  studentHighlights: string[];
  verifiedAt: string;
  sourceCount: number;
  admissionRate: number | null;
  studentFacultyRatio: number | null;
  undergraduateEnrollment: number | null;
  graduateEnrollment: number | null;
  totalEnrollment: number | null;
  enrollmentReferenceYear: number | null;

  // 鈹€鈹€ Campus Experience 鈹€鈹€
  /** Google / MapLibre Street View panorama ID for this campus. */
  streetviewPanoId?: string;

  /** Curated campus images shown in the POI card. */
  campusImages: CampusImage[];

  /** University logo URL (for POI marker & detail card). */
  logoUrl?: string;

  // 鈹€鈹€ Nearby Amenities 鈹€鈹€
  nearby: UniversityNearby;
}


/** Aggregated university data for one city, used by the state -> city -> university drill-down. */
export interface CityAggregate {
  /** Stable city id: `${stateFips}-${citySlug}`. */
  id: string;
  /** English city name from university records. */
  name: string;
  /** Chinese display name when available; falls back to `name`. */
  nameZh: string;
  /** Two-digit state FIPS code. */
  stateFips: string;
  /** Two-letter state abbreviation. */
  stateAbbr: string;
  /** Average latitude of universities in this city. */
  latitude: number;
  /** Average longitude of universities in this city. */
  longitude: number;
  /** Number of universities represented by this city bubble. */
  universityCount: number;
  /** Universities in this city after the current data/filter transform. */
  universities: UniversityPOI[];
  /** Mean annual cost in RMB. */
  avgAnnualCostRmb: number;
  /** Mean safety score, 0-100. */
  avgSafetyScore: number;
  /** Mean recognition score, 0-100. */
  avgRecognitionScore: number;
  /** Mean admission rate percentage when available. */
  avgAdmissionRate?: number;
  /** Mean employment score, 0-100, when available. */
  avgEmploymentScore?: number;
  /** Dominant Chinese community level among universities in this city. */
  dominantChineseCommunity: ChineseCommunityLevel;
  /** Count of universities/cities with direct flights from China. */
  directFlightCount: number;
  /** Best ranking tier among universities in this city. */
  topRankingTier: RankingTier;
}

/** Amenities within walking / short鈥憈ransit distance of campus. */
export interface UniversityNearby {
  /** Number of subway / metro stations within 1 km. */
  subwayStations: number;

  /** Number of Chinese restaurants within 2 km. */
  chineseRestaurants: number;

  /** Number of Asian grocery stores within 3 km. */
  asianGroceries: number;

  /** Average monthly rent (RMB) for a 1鈥慴edroom near campus. */
  avgRentRmb: number;
}

/** A labelled photograph of a campus landmark. */
export interface CampusImage {
  /** URL to the image asset (CDN / S3). */
  url: string;

  /** Chinese label, e.g. "涓诲浘涔﹂". */
  label: string;

  /** Optional geotag for placing on the map. */
  latitude?: number;
  longitude?: number;
}

/**
 * A discrete point鈥憃f鈥慽nterest on a university campus.
 * Used for the campus鈥慸etail / street鈥憊iew drill鈥慽n experience.
 *
 * TODO: Connect to Supabase `campus_pois` table when available
 */
export interface CampusPOI {
  /** Unique POI identifier. */
  id: string;

  /** Owning university ID. */
  universityId: string;

  /** Chinese name, e.g. "宸ョ▼瀛﹂櫌". */
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

// 鈹€鈹€ News / Sidebar Types 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

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

  /** Two鈥憀ine Chinese summary. */
  summary: string;

  /** Publisher / source name, e.g. "US News", "EIC Education". */
  source: string;

  /** Canonical link to the full article. */
  url: string;

  /** ISO鈥?601 publication date. */
  publishedAt: string;

  /** Thumbnail / hero image URL. */
  imageUrl?: string;

  category: NewsCategory;
}

// 鈹€鈹€ Map View State 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

/**
 * Serializable snapshot of the map viewport.
 * Used to restore map state from URL search params, localStorage,
 * or shared links.  All fields are optional so partial updates
 * (e.g. zoom鈥憃nly) are supported.
 *
 * TODO: Persist view state in URL search params via nuqs or next-usequerystate
 */
export interface MapViewState {
  /** Longitude of map centre. */
  longitude?: number;

  /** Latitude of map centre. */
  latitude?: number;

  /** Zoom level (MapLibre: 0鈥?2). */
  zoom?: number;

  /** Bearing in degrees (0 = north鈥憉p). */
  bearing?: number;

  /** Pitch in degrees (0 = top鈥慸own). */
  pitch?: number;

  /** Active metric layer shown on the choropleth. */
  activeMetricId?: MetricId;

  /** Currently selected university POI ID (null = none). */
  selectedUniversityId?: string | null;

  /** Currently selected campus POI ID (null = none). */
  selectedCampusPoiId?: string | null;

  /** Active map mode: standard choropleth or street鈥憊iew immersive. */
  mode?: "map" | "streetview";

  /** Sidebar panel visibility. */
  panelOpen?: boolean;
}

// 鈹€鈹€ Map Interaction Types 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

/**
 * Transient tooltip payload computed on `mousemove` over a choropleth
 * region.  Displayed via `RegionTooltip` component.
 */
export interface MapTooltip {
  /** Pixel鈥憍 of the cursor relative to the map container. */
  x: number;

  /** Pixel鈥憏 of the cursor relative to the map container. */
  y: number;

  /** Human鈥憆eadable region name (Chinese when available). */
  regionName: string;

  /** Numeric metric value (null when data is missing). */
  metricValue: number | null;

  /** Pre鈥慺ormatted display string, e.g. "$85k", "32.5%". */
  displayValue: string;
}

/** Top鈥憀evel map display mode. */
export type MapViewMode = "map" | "streetview";

// 鈹€鈹€ Map Filter State 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

/**
 * User鈥慶ontrolled filters that narrow the POI set and data overlay.
 * Kept separate from `MapViewState` because filters do not represent
 * viewport state 鈥?they are application鈥憀evel UI state.
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

// 鈹€鈹€ POI Clustering (Phase 3) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

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

// 鈹€鈹€ Map Layer Config (MapLibre style helpers) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

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

// 鈹€鈹€ Street View / Campus Immersive (Phase 4) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

/**
 * Campus immersive view state used by the street鈥憊iew overlay
 * component.  Activated when the user clicks a campus POI or
 * toggles `MapViewMode` to `"streetview"`.
 *
 * TODO: Wire to Google Street View / MapLibre GL JS Street View API in Phase 4
 */
export interface StreetViewState {
  /** Whether the immersive panel is active. */
  active: boolean;

  /** Pano ID for the 360掳 view or street鈥憊iew widget. */
  panoId: string | null;

  /** University POI this immersive session is anchored to. */
  universityId: string | null;

  /** Campus POI currently in focus (null = general campus view). */
  campusPoiId: string | null;
}

// 鈹€鈹€ API Response Shapes (Phase 4+) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

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
  /** Campus landmarks for the drill鈥慽n view. */
  campusPois: CampusPOI[];
  /** Neighbouring universities within 50 km. */
  nearbyUniversities: UniversityPOI[];
  /** Regional metrics for the university's county / city. */
  regionMetrics: RegionMetric[];
}


