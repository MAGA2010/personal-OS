// PathOS constrained-preview BFF route.
//
// Until the production backend exposes its preview endpoints, this
// handler is the *single* entry point read by `PreviewApiDataSource`.
// It reads from `src/test/fixtures/*.fixture.json`, treats every
// record as `previewOnly: true`, and surfaces the exact manifest
// version. When the production backend is up, this whole module
// should be replaced with `process.env.NEXT_PUBLIC_PATHOS_API_BASE_URL`
// pointing at `/api/v1/preview/*`.
//
// IMPORTANT: Do not import this file from production components
// directly. The preview API data source in
// `@/services/preview-api-data-source.ts` owns the HTTP surface.

import { NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import path from "node:path";

const FIXTURE_ROOT = path.join(process.cwd(), "src", "test", "fixtures");

// Region-level metric IDs (gate-bloker repair #GB-P0-5). Anything not
// in this list is a school-level field and is dropped from the
// region-metrics endpoint so we never serve an illegal choropleth key.
const ALLOWED_REGION_METRICS = new Set([
  "income",
  "safety",
  "employment",
  "cost",
  "chinese_population",
]);

const ALLOWED_RANKING_TIERS = new Set(["top20", "top50", "top100", "other"]);
type AllowedRankingTier = "top20" | "top50" | "top100" | "other";
type Granularity = "state" | "county" | "city";
const ALLOWED_GRANULARITIES = new Set<Granularity>(["state", "county", "city"]);

/**
 * Infer the region granularity from the FIPS code length when the
 * caller didn't pass an explicit one. 2-digit → state, 5-digit →
 * county, anything longer (7+) → city. Returns `null` when the code
 * is empty so we can reject the request rather than guess.
 */
function inferGranularity(fips: string, requested: string | null): Granularity | null {
  if (requested && ALLOWED_GRANULARITIES.has(requested as Granularity)) {
    return requested as Granularity;
  }
  if (!fips) return null;
  const digits = fips.replace(/[^0-9]/g, "");
  if (digits.length <= 2) return "state";
  if (digits.length === 5) return "county";
  return "city";
}

async function loadFixture<T>(name: string): Promise<T> {
  const file = path.join(FIXTURE_ROOT, name);
  const buf = await readFile(file, "utf8");
  return JSON.parse(buf) as T;
}

export async function loadUniversities(): Promise<RawUniversityRecord[]> {
  const raw = await loadFixture<{ universities: RawUniversityRecord[] }>("universities.fixture.json");
  return raw.universities ?? [];
}

interface RawUniversityRecord {
  id: string;
  name: string;
  chineseName: string;
  city: string;
  state: string;
  stateFips?: string;
  country: string;
  latitude: number;
  longitude: number;
  rankingBand: string;
  rankingTier: "top20" | "top50" | "top100" | "other";
  annualCostRmb?: number;
  safetyScore?: number;
  recognitionScore?: number;
  chineseCommunity?: "low" | "medium" | "high";
  programs?: string[];
  parentHighlights?: string[];
  studentHighlights?: string[];
  historySummary?: string;
  numericRank?: number;
  sourceCount?: number;
  verifiedAt?: string;
  studentFacultyRatio?: number;
  [k: string]: unknown;
}

const RMB_PER_USD = 7.2;

function toSummary(u: RawUniversityRecord) {
  // Cost is mandatory data for the Calculator / Compare flows. We
  // refuse to fabricate `0` placeholders — if the fixture row lacks an
  // `annualCostRmb`, the resulting `costSummary` is null and consumers
  // are expected to render the empty state instead of ¥0. Capture the
  // raw value into a local first so TypeScript can narrow it past the
  // `hasTuition` guard.
  const rawAnnualCost = u.annualCostRmb;
  const hasTuition = typeof rawAnnualCost === "number" && rawAnnualCost > 0;
  const minimumUsd = hasTuition ? Math.round((rawAnnualCost as number) / RMB_PER_USD) : null;
  const nullable: string[] = [];
  if (!hasTuition) nullable.push("costSummary");
  const sfr = typeof u.studentFacultyRatio === "number" && u.studentFacultyRatio > 0 ? u.studentFacultyRatio : undefined;
  if (sfr === undefined) nullable.push("studentFacultyRatio");
  const rankingTier = u.rankingTier;
  const rankingLabel = u.rankingBand;
  const nationalRank = typeof u.numericRank === "number" ? u.numericRank : undefined;
  return {
    id: u.id,
    name: u.name,
    nameZh: u.chineseName,
    chineseName: u.chineseName,
    city: u.city,
    state: u.state,
    stateFips: u.stateFips,
    country: u.country,
    latitude: typeof u.latitude === "number" ? u.latitude : null,
    longitude: typeof u.longitude === "number" ? u.longitude : null,
    rankingSummary: {
      nationalRank,
      rankingTier,
      rankingLabel,
    },
    // Legacy mirrors so existing code paths that still read top-level
    // fields don't crash; new code should consume rankingSummary{}.
    rankingTier,
    rankingBand: rankingLabel,
    nationalRanking: nationalRank,
    rankingYear: undefined,
    costSummary: hasTuition
      ? {
          minimumUsd,
          maximumUsd: minimumUsd,
          displayLabel: `$${minimumUsd}`,
          comparisonSafe: false,
        }
      : null,
    studentFacultyRatio: sfr,
    qualitySummary: { coveragePercent: 0, warningCodes: ["source_review_not_completed"] },
    displayTier: "preview",
    previewOnly: true,
    datasetVersion: "fixture-2026-07-24",
    nullableFields: nullable,
  };
}

function toDetail(u: RawUniversityRecord) {
  return {
    ...toSummary(u),
    programs: (u.programs ?? []).map((p, i) => ({
      id: `${u.id}-prog-${i}`,
      name: p,
      membership: i < 5 ? "top" : undefined,
      displayTier: "preview",
    })),
    topProgramIds: (u.programs ?? []).slice(0, 5).map((p, i) => `${u.id}-prog-${i}`),
    ranking: [],
    cost:
      typeof u.annualCostRmb === "number"
        ? [
            {
              amount: u.annualCostRmb,
              currency: "RMB" as const,
              scope: "unknown",
              year: 2025,
              components: { tuition: true },
              status: "source_review_not_completed" as const,
            },
          ]
        : [],
    history: typeof u.historySummary === "string" && u.historySummary.trim() ? u.historySummary : null,
    anecdotes: [],
    notableAttendance: [],
    people: [],
    nearbyTowns: [],
    sources: u.sourceCount
      ? [
          {
            url: "about:blank",
            status: "source_review_not_completed",
            anchor: "fixture-source",
          },
        ]
      : [],
    warnings: [],
    qualityBadges: [],
    studentFacultyRatio: null,
  };
}

async function loadRegionMetricRecords() {
  const raw = await loadFixture<{ records: unknown[] }>("region-metrics.fixture.json");
  return raw.records ?? [];
}

async function loadNews(): Promise<Array<{ id?: string; title?: string; titleEn?: string; summary?: string; source?: string; url?: string; publishedAt?: string; category?: string; [k: string]: unknown }>> {
  const raw = await loadFixture<{ articles?: unknown[] }>("news.fixture.json");
  return Array.isArray(raw.articles) ? (raw.articles as Array<{ id?: string; title?: string; titleEn?: string; summary?: string; source?: string; url?: string; publishedAt?: string; category?: string; [k: string]: unknown }>) : [];
}

async function loadCityBoundaries(): Promise<unknown> {
  return loadFixture("city-boundaries.fixture.json");
}

async function loadRankingData(): Promise<unknown[]> {
  const r = await loadFixture<unknown>("university-rankings.fixture.json");
  return Array.isArray(r) ? (r as unknown[]) : [];
}

function csvRespond(body: unknown, status = 200) {
  return NextResponse.json(body, {
    status,
    headers: { "Cache-Control": "no-store", "X-PathOS-BFF": "preview-fixture" },
  });
}

export async function handleFixturePreviewRoute(req: Request): Promise<NextResponse> {
  const url = new URL(req.url);
  // Two URL shapes:
  //   /api/pathos/preview?endpoint=manifest
  //   /api/pathos/preview?endpoint=universities&state=CA  (universities list)
  //   /api/pathos/preview?endpoint=universities&id=foo  (single detail)
  const endpoint = (url.searchParams.get("endpoint") ?? "").trim();
  if (!endpoint) {
    return NextResponse.json({ error: "missing_endpoint" }, { status: 400 });
  }

  try {
    if (endpoint === "manifest") {
      return csvRespond({
        schemaVersion: "pathos-preview-1",
        generatedAt: new Date().toISOString(),
        sourceCommit: "fixture",
        previewOnly: true,
        counts: {
          universities: (await loadUniversities()).length,
          regionMetrics: (await loadRegionMetricRecords()).length,
          news: (await loadNews()).length,
        },
        statusDictionary: {},
      });
    }

    const detailId = url.searchParams.get("id");
    if (endpoint === "university" && detailId) {
      const uni = (await loadUniversities()).find((u) => u.id === detailId);
      if (!uni) {
        return NextResponse.json({ error: "not_found" }, { status: 404 });
      }
      return csvRespond(toDetail(uni));
    }

    if (endpoint === "universities") {
      const list = (await loadUniversities()).map(toSummary);
      // Repeated `?state=CA&state=NY` and `?tier=top20&tier=top50` form
      // (gate-bloker repair #GB-P0-4). Both query sources use `getAll`
      // so multi-value filters round-trip without ambiguity.
      const states = url.searchParams.getAll("state");
      const tiers = url.searchParams
        .getAll("tier")
        .filter((t) => ALLOWED_RANKING_TIERS.has(t as AllowedRankingTier));
      const filtered = list.filter((u) => {
        if (states.length > 0) {
          const fips = String(u.stateFips ?? "").padStart(2, "0").slice(-2);
          const matches = states.some((s) => {
            const candidate = String(s ?? "").padStart(2, "0").slice(-2);
            return candidate === fips || u.state === s;
          });
          if (!matches) return false;
        }
        if (tiers.length > 0 && !tiers.includes(u.rankingTier as string)) return false;
        return true;
      });
      return csvRespond(filtered);
    }

    const detailMatch = /universities\/(.+)/.exec(url.pathname);
    if (detailMatch) {
      const id = decodeURIComponent(detailMatch[1]);
      const uni = (await loadUniversities()).find((u) => u.id === id);
      if (!uni) {
        return NextResponse.json({ error: "not_found" }, { status: 404 });
      }
      return csvRespond(toDetail(uni));
    }

    if (endpoint === "region-metrics") {
      const records = await loadRegionMetricRecords();
      // Match the original RegionMetricRecord shape (fipsCode/granularity/metricId/value/year/etc.)
      const mapped = records
        .filter((r) => {
          const m = (r as Record<string, unknown>).metricId;
          return typeof m === "string" && ALLOWED_REGION_METRICS.has(m);
        })
        .map((r) => {
        const record = r as Record<string, unknown>;
        return {
          fipsCode: String(record.fipsCode ?? record.stateFips ?? ""),
          granularity: record.granularity ?? "state",
          metricId: record.metricId,
          value: typeof record.value === "number" ? record.value : 0,
          rawValue: record.rawValue ?? record.value ?? null,
          displayValue: record.displayValue ?? "",
          year: typeof record.year === "number" ? record.year : new Date().getFullYear(),
          source: record.source,
          previewOnly: true,
          nullableFields: [],
        };
      });
      return csvRespond(mapped);
    }

    if (endpoint === "region-detail") {
      const fips = url.searchParams.get("fipsCode") ?? "";
      if (!fips) return NextResponse.json({ error: "missing_fipsCode" }, { status: 400 });
      // Granularity must come from the request OR from the FIPS code
      // shape. We never default to "state" when the caller asked for a
      // county or city, and we never label a county as a state just
      // because the fixture was sparse (gate-bloker repair #GB-P1-6).
      const requested = url.searchParams.get("granularity");
      const granularity = inferGranularity(fips, requested);
      if (!granularity) {
        return NextResponse.json(
          { error: "unrecognised_fips", fipsCode: fips },
          { status: 400 },
        );
      }
      const records = await loadRegionMetricRecords();
      const list = records as Array<{
        fipsCode: string;
        granularity: string;
        metricId: string;
        value: number;
        rawValue?: number;
        displayValue: string;
        year: number;
        source?: string;
        name?: string;
        nameEn?: string;
        [k: string]: unknown;
      }>;
      const normalisedFips = fips.padStart(2, "0").slice(-2);
      const filtered = list.filter(
        (m) =>
          String(m.fipsCode ?? "").padStart(2, "0").slice(-2) === normalisedFips &&
          (m.granularity ?? "state") === granularity,
      );
      const unis = await loadUniversities();
      const unisHere = unis.filter(
        (u) => (u.stateFips ?? "").padStart(2, "0").slice(-2) === normalisedFips,
      ).map(toSummary);
      const top = unisHere.slice(0, 5);
      // Resolve a name from the canonical state-name config when we
      // know it's a state; otherwise fall back to the FIPS code so
      // callers can still render *something* but the data clearly
      // labels the granularity for users.
      const lookupKey = granularity === "state" ? normalisedFips : fips;
      return csvRespond({
        fipsCode: fips,
        granularity,
        name: top[0]?.state ?? lookupKey,
        nameEn: undefined,
        metrics: filtered.map((r) => ({
          fipsCode: r.fipsCode,
          granularity: (r.granularity ?? granularity) as "state" | "county" | "city",
          metricId: r.metricId,
          value: r.value,
          rawValue: r.rawValue ?? r.value,
          displayValue: r.displayValue ?? `${r.value}`,
          year: r.year,
          source: r.source,
          previewOnly: true,
          nullableFields: [],
        })),
        universityCount: unisHere.length,
        topUniversities: top,
        displayTier: "preview",
        previewOnly: true,
        warnings: [],
      });
    }
    if (endpoint === "regions") {
      return NextResponse.json({ error: "not_found" }, { status: 404 });
    }

    if (endpoint === "search") {
      const q = (url.searchParams.get("q") ?? "").trim().toLowerCase();
      const limit = Number(url.searchParams.get("limit") ?? "20");
      if (q.length < 2) return csvRespond([]);
      const list = await loadUniversities();
      const matched = list
        .filter((u) =>
          [u.name, u.chineseName, u.city, u.state]
            .filter(Boolean)
            .some((s) => String(s).toLowerCase().includes(q)),
        )
        .slice(0, limit)
        .map((u) => ({
          university: toSummary(u),
          matchedField: "name" as const,
        }));
      return csvRespond(matched);
    }

    if (endpoint === "news") {
      const category = url.searchParams.get("category");
      const all = await loadNews();
      const filtered = category ? all.filter((n: { category?: string }) => n.category === category) : all;
      const mapped = filtered.map((a: { [k: string]: unknown }) => ({
        id: String(a.id),
        title: String(a.title),
        titleEn: typeof a.titleEn === "string" ? a.titleEn : undefined,
        summary: typeof a.summary === "string" ? a.summary : undefined,
        source: typeof a.source === "string" ? a.source : "",
        url: typeof a.url === "string" ? a.url : "#",
        publishedAt: typeof a.publishedAt === "string" ? a.publishedAt : new Date(0).toISOString(),
        category: typeof a.category === "string" ? a.category : "admissions",
        displayTier: "preview",
      }));
      return csvRespond(mapped);
    }

    if (endpoint === "status-dictionary") {
      return csvRespond({
        source_review_not_completed: {
          consumerLabel: "数据补充中",
          icon: "hourglass",
          tone: "neutral",
        },
        live_verified_exact: {
          consumerLabel: "来源已实时验证",
          icon: "check",
          tone: "success",
        },
        live_verified_normalized: {
          consumerLabel: "来源已验证并规范化",
          icon: "check",
          tone: "info",
        },
        live_unavailable: {
          consumerLabel: "实时来源暂不可用",
          icon: "alert",
          tone: "warn",
        },
        page_changed: {
          consumerLabel: "来源页面已发生变化",
          icon: "alert",
          tone: "warn",
        },
        archived_source: {
          consumerLabel: "使用归档来源",
          icon: "archive",
          tone: "neutral",
        },
      });
    }

    if (endpoint === "source-index") {
      // Lightweight directory for citation popovers.
      const list = await loadUniversities();
      const news = await loadNews();
      const rankings = await loadRankingData();
      return csvRespond({
        universities: list.map((u) => ({ id: u.id, display: u.chineseName })),
        rankings: Array.isArray(rankings)
          ? rankings.map((r: unknown) => {
              const x = r as { id?: string; chineseName?: string };
              const id = typeof x.id === "string" ? x.id : "";
              return { id, display: x.chineseName ?? id };
            })
          : [],
        news: news.slice(0, 5),
      });
    }

    if (endpoint === "city-boundaries") {
      // Gate-bloker repair #GB-P1-7: serve the national city boundary
      // GeoJSON from the shared fixture instead of letting production
      // components inline a California-only polygon blob. The dataset
      // ships in `src/test/fixtures/city-boundaries.fixture.json`; the
      // boundary component fetches it the same way it would fetch from
      // a future backend endpoint, so the swap is one URL change.
      const data = await loadCityBoundaries();
      return csvRespond(data);
    }

    return NextResponse.json({ error: "unknown_endpoint" }, { status: 404 });
  } catch (e) {
    const err = e as Error;
    return NextResponse.json({ error: err.message ?? "preview_route_error" }, { status: 500 });
  }
}
