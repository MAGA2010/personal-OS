// PathOS — domain types for the data layer.
// These describe records the backend data source is expected to provide.
// The legacy `frontend/src/lib/types.ts` types (legacy UI shapes) are kept
// for backward compatibility in components that still depend on them; new
// code should import from this file instead.

export type DisplayTier = "live_verified" | "cached" | "preview" | "quarantined";

export type ProvenanceStatus =
  | "live_verified_exact"
  | "live_verified_normalized"
  | "live_unavailable"
  | "source_review_not_completed"
  | "page_changed"
  | "archived_source";

export interface DatasetManifest {
  contractVersion?: string;
  datasetVersion?: string;
  view?: "preview";
  sourceCheckpoint?: string;
  sourceLimited?: boolean;
  incomplete?: boolean;
  notFinal?: boolean;
  enabledFeatures?: string[];
  disabledFeatures?: string[];
  schemaVersion: string;
  generatedAt: string;
  sourceCommit: string;
  previewOnly: boolean;
  counts: {
    universities: number;
    regionMetrics: number;
    news: number;
  };
  statusDictionary?: Record<string, ProvenanceStatusLabel>;
}

export interface ProvenanceStatusLabel {
  consumerLabel: string;
  technicalLabel?: string;
  icon?: string;
  tone?: "neutral" | "info" | "warn" | "danger" | "success";
  description?: string;
}

export interface SourceReference {
  url: string;
  retrievedAt?: string;
  cachedSnapshotAt?: string;
  cacheTtlSeconds?: number;
  anchor?: string;
  status: ProvenanceStatus;
}

/**
 * `UniversitySummary` is the small, list-safe shape that the map, the
 * calculator, the compare panel, and search all consume. Region-only
 * attributes (safety / Chinese-community / employment / cost-of-living)
 * are NOT here — those come from `RegionMetricRecord`. Cost here is the
 * school's own published tuition band; everything else is region-scoped.
 *
 * The `rankingSummary` / `costSummary` / `qualitySummary` blocks are the
 * recommended contract shape; the legacy top-level fields (`city`,
 * `state`, `rankingTier`, `rankingBand`, etc.) remain on the type only
 * as a transition aid for code paths that haven't migrated yet. New
 * components MUST consume the nested blocks, not the legacy ones.
 *
 * `nullableFields` is a manifest of which fields are missing for this
 * row so the UI can decide whether to render an empty-state ("数据补充中")
 * or skip the row entirely (e.g. exclude from Calculator totals).
 */
export interface UniversitySummary {
  id: string;
  name: string;
  /** Recommended-shape Chinese name (preferred). */
  nameZh: string;
  /** Legacy alias of `nameZh`. Kept so existing consumers compile. */
  chineseName: string;
  aliases?: string[];

  // ── Recommended-shape blocks (preferred) ────────────────────────
  latitude: number | null;
  longitude: number | null;
  rankingSummary?: {
    nationalRank?: number | null;
    rankingTier?: "top20" | "top50" | "top100" | "other";
    rankingLabel?: string;
  };
  costSummary?: {
    minimumUsd?: number | null;
    maximumUsd?: number | null;
    displayLabel?: string;
    comparisonSafe?: boolean;
  };
  /** Compact enrollment snapshot for list view (map, calculator, search). */
  enrollmentSummary?: {
    undergraduate?: number | null;
    graduate?: number | null;
    total?: number | null;
    referenceYear?: number | null;
  };
  studentFacultyRatio?: number;
  qualitySummary?: {
    coveragePercent?: number;
    warningCodes?: string[];
  };

  // ── Legacy fields (transition aid only) ──────────────────────────
  /** @deprecated Use `rankingSummary.rankingTier`. */
  rankingTier?: "top20" | "top50" | "top100" | "other";
  /** @deprecated Use `rankingSummary.rankingLabel`. */
  rankingBand?: string;
  /** @deprecated Use `rankingSummary.nationalRank`. */
  nationalRanking?: number | null;
  /** @deprecated Use `rankingSummary.nationalRank`'s year context. */
  rankingYear?: number;
  /** @deprecated Region-scoped data; fetch via RegionMetricRecord. */
  city?: string;
  /** @deprecated Region-scoped data; fetch via RegionMetricRecord. */
  state?: string;
  /** @deprecated Region-scoped data; fetch via RegionMetricRecord. */
  stateFips?: string;
  /** @deprecated Region-scoped data; fetch via RegionMetricRecord. */
  country?: string;

  displayTier: DisplayTier;
  previewOnly: boolean;
  datasetVersion: string;
  sourceCommit?: string;
  nullableFields: string[];
}

export interface UniversityDetail extends UniversitySummary {
  programs: Program[];
  topProgramIds: string[];
  ranking: RankingMembership[];
  cost: CostRecord[];
  studentFacultyRatio?: number;
  history?: string;
  anecdotes?: Anecdote[];
  notableAttendance?: NotableAttendance[];
  people: Person[];
  nearbyTowns: NearbyTown[];
  sources: SourceReference[];
  warnings: string[];
  qualityBadges: QualityBadge[];
  previewMetadata?: PreviewMetadata;
}

export interface PreviewField<T = unknown> {
  value: T | null;
  status: string;
  referenceYear: number | string | null;
  scope: string | null;
  unit: string | null;
  sourceIds: string[];
  warnings: string[];
  nullReason?: string | null;
}

export interface PreviewMetadata {
  allMajors?: Array<{
    name: string;
    displayName: string;
    degreeType: string | null;
    listType: string | null;
    sourceIds: string[];
    status: string;
    warnings: string[];
  }>;
  allMajorsStatus?: {
    status: "source_limited" | "not_reported";
    nullReason: string | null;
  };
  enrollment: {
    undergraduate: PreviewField<number>;
    graduate: PreviewField<number>;
    total: PreviewField<number>;
  };
  admissions: {
    acceptanceRate: PreviewField<number>;
    graduationRate: PreviewField<number>;
    retentionRate: PreviewField<number>;
    sat: PreviewField<unknown>;
    act: PreviewField<unknown>;
    testPolicy: PreviewField<unknown>;
    englishPolicy: PreviewField<unknown>;
  };
  geography: {
    geographyScope: "place" | "county";
    place: PreviewField<string>;
    county: PreviewField<string>;
    cbsa?: unknown;
  };
  programPeopleGaps: Array<{
    slotId: string;
    programName: string;
    status: "source_review_not_completed";
    displayLabel: string;
    displayAsNone: false;
  }>;
}

export interface Program {
  id: string;
  name: string;
  category?: string;
  rank?: number;
  membership?: "top" | "notable";
  displayTier: DisplayTier;
}

export interface RankingMembership {
  system: "QS" | "ARWU" | "USNews" | "THE";
  year: number;
  position: number | string;
  scope?: "global" | "national";
  sourceUrl?: string;
  displayTier: DisplayTier;
}

export interface CostRecord {
  amount: number;
  currency: "RMB";
  scope: "in_state" | "out_of_state" | "international" | "unknown";
  year: number;
  components: {
    tuition?: boolean;
    roomBoard?: boolean;
    mandatoryFees?: boolean;
  };
  sourceUrl?: string;
  status: ProvenanceStatus;
}

export interface Anecdote {
  text: string;
  sourceUrl?: string;
  status: ProvenanceStatus;
}

export interface NearbyTown {
  name: string;
  nameZh?: string;
  distanceKm?: number;
}

export interface NotableAttendance {
  type: "notable_attendance";
  year?: number;
  context?: string;
  sourceUrl?: string;
  status: ProvenanceStatus;
}

export interface Person {
  id: string;
  name: string;
  relationship: string;
  domain?: string;
  era?: string;
  sourceUrl?: string;
  status: ProvenanceStatus;
  displayTier: DisplayTier;
  quarantined: boolean;
}

export interface QualityBadge {
  kind: "verified" | "warning" | "gap" | "quarantine";
  label: string;
  detail?: string;
}

export interface RegionMetricRecord {
  fipsCode: string;
  granularity: "state" | "county" | "city";
  metricId: string;
  value: number;
  rawValue: number;
  displayValue: string;
  year: number;
  source?: string;
  status?: ProvenanceStatus;
  previewOnly: boolean;
  nullableFields: string[];
}

export interface NewsArticle {
  id: string;
  title: string;
  titleEn?: string;
  summary?: string;
  source: string;
  url: string;
  publishedAt: string;
  category: string;
  displayTier: DisplayTier;
}

export interface RegionDetail {
  fipsCode: string;
  granularity: "state" | "county" | "city";
  name: string;
  nameEn?: string;
  metrics: RegionMetricRecord[];
  universityCount: number;
  topUniversities: UniversitySummary[];
  displayTier: DisplayTier;
  previewOnly: boolean;
  warnings: string[];
}

export interface UniversityQuery {
  search?: string;
  rankingTiers?: string[];
  states?: string[];
  maxCostRmb?: number;
  minSafetyScore?: number;
  minDisplayTier?: DisplayTier;
  excludeQuarantined?: boolean;
}

export interface RegionMetricQuery {
  metricId: string;
  granularity?: "state" | "county" | "city";
}

export interface UniversitySearchResult {
  university: UniversitySummary;
  matchedField: "name" | "chineseName" | "city" | "state" | "program";
}

export interface DataSourceUnavailable extends Error {
  code:
    | "BACKEND_OFFLINE"
    | "TIMEOUT"
    | "ABORTED"
    | "HTTP_ERROR"
    | "INVALID_RESPONSE"
    | "INVALID_JSON"
    | "BACKEND_UNAVAILABLE"
    | "UNSUPPORTED_CONTRACT_VERSION"
    | "PREVIEW_NOT_YET_AVAILABLE";
}

export type ResourceState<T> =
  | { status: "idle" }
  | { status: "loading"; signal?: AbortSignal }
  | { status: "ready"; data: T }
  | { status: "error"; message: string; code?: string };

export interface StatusDictionaryMap {
  [key: string]: ProvenanceStatusLabel;
}

export { RegionMetricSet } from "./region-metric-set";
