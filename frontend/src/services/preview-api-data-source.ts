// Preview API data source.
// Hits our Next.js BFF (`/api/pathos/preview/*`) which in turn talks
// to the backend preview export. Failures surface as exceptions that
// the caller turns into ResourceState:error — no silent mock.

import type { PathOSDataSource } from "./pathos-data-source";
import {
  parseManifest,
  parseNewsArticleList,
  parseRegionDetail,
  parseRegionMetricRecordList,
  parseSourceReference,
  parseStatusDictionary,
  parseUniversityDetail,
  parseUniversitySearchResultList,
  parseUniversitySummaryList,
} from "@/schemas/dataset.schema";
import { ValidationError } from "@/schemas/validators";
import type { NewsArticle, RegionMetricQuery, SourceReference, StatusDictionaryMap, UniversityQuery } from "@/domain/dataset";

// Allowed values for the `tier` query parameter (gate-bloker repair
// #GB-P0-4). Mirrors `RANKING_TIER` in `@/schemas/dataset.schema.ts`;
// kept locally to avoid a schema import cycle.
const ALLOWED_TIERS = new Set(["top20", "top50", "top100", "other"]);

/** Sanitize a `rankingTiers` array — drop unknown values silently
 *  rather than 400-ing the whole request. Empty arrays are valid
 *  (means "no tier filter"). */
function sanitizeTiers(input: readonly unknown[] | undefined): string[] | undefined {
  if (!input) return undefined;
  const out: string[] = [];
  const seen = new Set<string>();
  for (const v of input) {
    if (typeof v !== "string") continue;
    if (!ALLOWED_TIERS.has(v)) continue;
    if (seen.has(v)) continue;
    seen.add(v);
    out.push(v);
  }
  return out.length > 0 ? out : undefined;
}

const DEFAULT_TIMEOUT_MS = 8_000;

export async function fetchPreviewJson<T>(path: string, parse: (raw: unknown) => T, signal?: AbortSignal, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const externalController = new AbortController();
  if (signal) {
    if (signal.aborted) externalController.abort();
    else signal.addEventListener("abort", () => externalController.abort(), { once: true });
  }
  const timeoutController = new AbortController();
  const linkedSignal = mergeSignals(externalController.signal, timeoutController.signal);
  const timer = setTimeout(() => timeoutController.abort(), timeoutMs);
  let resp: Response;
  try {
    resp = await fetch(path, { signal: linkedSignal, headers: { Accept: "application/json" } });
  } catch (e) {
    clearTimeout(timer);
    const err = new Error(`Preview fetch failed: ${(e as Error).message}`) as Error & { code: string };
    err.code = timeoutController.signal.aborted
      ? "TIMEOUT"
      : externalController.signal.aborted
        ? "ABORTED"
        : "BACKEND_UNAVAILABLE";
    throw err;
  }
  clearTimeout(timer);
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    let backendCode: string | undefined;
    try {
      const payload = JSON.parse(text) as { code?: unknown };
      if (typeof payload.code === "string") backendCode = payload.code;
    } catch {
      // Non-JSON failure bodies are intentionally not exposed to the UI.
    }
    const err = new Error(`Preview request failed (${resp.status})`) as Error & {
      code: string;
    };
    err.code =
      backendCode ??
      (resp.status === 0 || resp.status >= 500
        ? "BACKEND_UNAVAILABLE"
        : "HTTP_ERROR");
    throw err;
  }
  let json: unknown;
  try {
    json = await resp.json();
  } catch (e) {
    const err = new Error(`Preview returned invalid JSON: ${(e as Error).message}`) as Error & { code: string };
    err.code = "INVALID_JSON";
    throw err;
  }
  try {
    return parse(json);
  } catch (e) {
    if (e instanceof ValidationError) {
      const err = new Error(`Validation failed: ${e.message}`) as Error & { code: string };
      err.code = "INVALID_RESPONSE";
      throw err;
    }
    throw e;
  }
}

function mergeSignals(...signals: AbortSignal[]): AbortSignal {
  if (signals.length === 1) return signals[0];
  const ac = new AbortController();
  for (const s of signals) {
    if (s.aborted) { ac.abort(); break; }
    s.addEventListener("abort", () => ac.abort(), { once: true });
  }
  return ac.signal;
}

function buildUrl(baseUrl: string, endpoint: string, query?: Record<string, unknown>, idParam = false): string {
  const usp = new URLSearchParams();
  usp.set("endpoint", idParam ? "university" : endpoint);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v === undefined || v === null) continue;
      if (Array.isArray(v)) {
        for (const item of v) usp.append(k, String(item));
      } else {
        usp.set(k, String(v));
      }
    }
  }
  return `${baseUrl}?${usp.toString()}`;
}

function parseRegionMetricsResponse(raw: unknown) {
  if (Array.isArray(raw)) return parseRegionMetricRecordList(raw);
  if (!raw || typeof raw !== "object") {
    throw new ValidationError([
      { path: "region-metrics", message: "response must be an array or envelope" },
    ]);
  }
  const envelope = raw as Record<string, unknown>;
  if (
    envelope.status !== "blocked" ||
    envelope.choroplethEnabled !== false ||
    typeof envelope.disabledReason !== "string" ||
    !Array.isArray(envelope.metricMetadata)
  ) {
    throw new ValidationError([
      { path: "region-metrics", message: "blocked envelope is invalid" },
    ]);
  }
  return parseRegionMetricRecordList(envelope.records);
}

export class PreviewApiDataSource implements PathOSDataSource {
  constructor(
    private readonly baseUrl = "/api/pathos/preview",
    private readonly timeoutMs = DEFAULT_TIMEOUT_MS,
  ) {}

  getManifest(signal?: AbortSignal) {
    return fetchPreviewJson(buildUrl(this.baseUrl, "manifest"), parseManifest, signal, this.timeoutMs);
  }
  getUniversitySummaries(query?: UniversityQuery, signal?: AbortSignal) {
    const flat: Record<string, unknown> = {};
    if (query) {
      if (query.search) flat.search = query.search;
      // Repeated query params (`?state=CA&state=NY`) for arrays — keeps
      // the protocol uniform with `tier` below and avoids comma-joining
      // which would force callers to escape state codes that contain
      // commas (gate-bloker repair #GB-P0-4).
      if (query.states && query.states.length > 0) flat.state = query.states;
      const sanitizedTiers = sanitizeTiers(query.rankingTiers);
      if (sanitizedTiers) flat.tier = sanitizedTiers;
      if (query.maxCostRmb !== undefined) flat.maxCostRmb = query.maxCostRmb;
    }
    return fetchPreviewJson(buildUrl(this.baseUrl, "universities", flat), parseUniversitySummaryList, signal, this.timeoutMs);
  }
  getUniversityDetail(id: string, signal?: AbortSignal) {
    return fetchPreviewJson(buildUrl(this.baseUrl, "universities", { id }, true), parseUniversityDetail, signal, this.timeoutMs);
  }
  getRegionMetrics(query: RegionMetricQuery, signal?: AbortSignal) {
    return fetchPreviewJson(buildUrl(this.baseUrl, "region-metrics", query as unknown as Record<string, unknown>), parseRegionMetricsResponse, signal, this.timeoutMs);
  }
  async getRegionDetail(fipsCode: string, signal?: AbortSignal) {
    try {
      return await fetchPreviewJson(
        `${this.baseUrl}?endpoint=region-detail&fipsCode=${encodeURIComponent(fipsCode)}`,
        parseRegionDetail,
        signal,
        this.timeoutMs,
      );
    } catch (e) {
      const err = e as Error & { code?: string };
      if (err.code === "HTTP_ERROR") return null;
      throw e;
    }
  }
  searchUniversities(query: string, limit = 20, signal?: AbortSignal) {
    const qs = new URLSearchParams({ endpoint: "search", q: query, limit: String(limit) }).toString();
    return fetchPreviewJson(`${this.baseUrl}?${qs}`, parseUniversitySearchResultList, signal, this.timeoutMs);
  }
  getNews(category: string | undefined, signal?: AbortSignal) {
    const qs = new URLSearchParams({ endpoint: "news", ...(category ? { category } : {}) }).toString();
    return fetchPreviewJson(`${this.baseUrl}?${qs}`, parseNewsArticleList, signal as AbortSignal, this.timeoutMs) as Promise<NewsArticle[]>;
  }
  getStatusDictionary(signal?: AbortSignal): Promise<StatusDictionaryMap> {
    return fetchPreviewJson(`${this.baseUrl}?endpoint=status-dictionary`, parseStatusDictionary, signal, this.timeoutMs);
  }
  async resolveSourceReference(source: SourceReference, _signal?: AbortSignal) {
    return { url: source.url, cachedSnapshotAt: source.cachedSnapshotAt, anchor: source.anchor };
  }
}

function encodeQuery(obj?: Record<string, unknown>): string {
  if (!obj) return "";
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(obj)) {
    if (v === undefined || v === null) continue;
    if (Array.isArray(v)) {
      for (const item of v) usp.append(k, String(item));
    } else {
      usp.set(k, String(v));
    }
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

// Exported for testing.
export { parseSourceReference };
