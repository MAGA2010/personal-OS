// PathOS data-source contract.
// All components MUST read from a `PathOSDataSource`; the source can be
// fulfilled by the preview API, a future production backend, or an
// unavailable stub. Components MUST NOT import static JSON.

import type {
  DatasetManifest,
  NewsArticle,
  RegionDetail,
  RegionMetricQuery,
  RegionMetricRecord,
  ResourceState,
  SourceReference,
  StatusDictionaryMap,
  UniversityDetail,
  UniversityQuery,
  UniversitySearchResult,
  UniversitySummary,
} from "@/domain/dataset";

export interface PathOSDataSource {
  /** Manifest describing the dataset behind this source. */
  getManifest(signal?: AbortSignal): Promise<DatasetManifest>;

  /** List summaries of universities (always cheap, no narrative / people). */
  getUniversitySummaries(query?: UniversityQuery, signal?: AbortSignal): Promise<UniversitySummary[]>;

  /** Full detail (programs / people / sources). Lazy-loaded per click. */
  getUniversityDetail(universityId: string, signal?: AbortSignal): Promise<UniversityDetail>;

  /** Choropleth region metric values for the requested metric. */
  getRegionMetrics(query: RegionMetricQuery, signal?: AbortSignal): Promise<RegionMetricRecord[]>;

  /** Sidebar / hover detail for a single region (state / city / county). */
  getRegionDetail(fipsCode: string, signal?: AbortSignal): Promise<RegionDetail | null>;

  /** Search across name / alias / city / state / program. */
  searchUniversities(query: string, limit?: number, signal?: AbortSignal): Promise<UniversitySearchResult[]>;

  /** News sidebar (unrelated to a specific university). */
  getNews(category?: string, signal?: AbortSignal): Promise<NewsArticle[]>;

  /** Provenance status dictionary (icons / labels / tones). */
  getStatusDictionary(signal?: AbortSignal): Promise<StatusDictionaryMap>;

  /** Resolves a cached URL for citation popovers. */
  resolveSourceReference(source: SourceReference, signal?: AbortSignal): Promise<{ url: string; cachedSnapshotAt?: string; anchor?: string }>;
}

export type { ResourceState };
