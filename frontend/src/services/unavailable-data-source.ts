// Unavailable data source — every call resolves to a clean, typed error.
// Used when the backend is offline / not yet provisioned. Surfaces the
// "数据服务暂不可用" state in the UI rather than fabricating data.

import type { PathOSDataSource } from "./pathos-data-source";
import type {
  DatasetManifest,
  NewsArticle,
  RegionDetail,
  RegionMetricQuery,
  RegionMetricRecord,
  SourceReference,
  StatusDictionaryMap,
  UniversityDetail,
  UniversityQuery,
  UniversitySearchResult,
  UniversitySummary,
} from "@/domain/dataset";

function unavailable<T>(): Promise<T> {
  return Promise.reject(Object.assign(new Error("数据服务暂不可用"), { code: "BACKEND_OFFLINE" }));
}

export class UnavailableDataSource implements PathOSDataSource {
  constructor(private readonly reason: string = "数据服务暂不可用") {}

  getManifest(): Promise<DatasetManifest> {
    return unavailable();
  }
  getUniversitySummaries(_query?: UniversityQuery): Promise<UniversitySummary[]> {
    return unavailable();
  }
  getUniversityDetail(_id: string): Promise<UniversityDetail> {
    return unavailable();
  }
  getRegionMetrics(_query: RegionMetricQuery): Promise<RegionMetricRecord[]> {
    return unavailable();
  }
  getRegionDetail(_fipsCode: string): Promise<RegionDetail | null> {
    return unavailable();
  }
  searchUniversities(_query: string): Promise<UniversitySearchResult[]> {
    return unavailable();
  }
  getStatusDictionary(): Promise<StatusDictionaryMap> {
    return unavailable();
  }
  getNews(_category?: string): Promise<NewsArticle[]> {
    return unavailable();
  }
  resolveSourceReference(_source: SourceReference): Promise<{ url: string; cachedSnapshotAt?: string; anchor?: string }> {
    return unavailable();
  }

  /** Public-facing reason string used in UI banners. */
  describe(): string {
    return this.reason;
  }
}
