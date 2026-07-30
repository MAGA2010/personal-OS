// Runtime schemas for the PathOS data-source responses.
// The hand-rolled validators live in `@/schemas/validators.ts`; this
// file orchestrates them into per-endpoint schemas and exposes typed
// parsers (parseManifest, parseUniversitySummary, ...).

import { ValidationError, combine, validateNullable, validateNumber, validateOneOf, validateString } from "./validators";
import type {
  Anecdote,
  CostRecord,
  DatasetManifest,
  NearbyTown,
  NewsArticle,
  NotableAttendance,
  Person,
  Program,
  ProvenanceStatusLabel,
  QualityBadge,
  RankingMembership,
  RegionDetail,
  RegionMetricRecord,
  SourceReference,
  StatusDictionaryMap,
  UniversityDetail,
  UniversityQuery,
  UniversitySearchResult,
  UniversitySummary,
} from "@/domain/dataset";

const DISPLAY_TIER = ["live_verified", "cached", "preview", "quarantined"] as const;
const PROVENANCE_STATUS = [
  "live_verified_exact",
  "live_verified_normalized",
  "live_unavailable",
  "source_review_not_completed",
  "page_changed",
  "archived_source",
] as const;
const RANKING_TIER = ["top20", "top50", "top100", "other"] as const;
const GRANULARITY = ["state", "county", "city"] as const;
const COST_SCOPE = ["in_state", "out_of_state", "international", "unknown"] as const;
const RANKING_SYSTEM = ["QS", "ARWU", "USNews", "THE"] as const;
const MEMBERSHIP = ["top", "notable"] as const;
const BADGE_KIND = ["verified", "warning", "gap", "quarantine"] as const;
const TONE = ["neutral", "info", "warn", "danger", "success"] as const;

// Region-level metrics only. School-level keys (TOEFL/SAT/admission_rate)
// intentionally excluded — they belong to `UniversityDetail`, never to
// the choropleth region dataset. Keeping this list in one place prevents
// `region-metrics` payloads from sneaking in school-level IDs.
const REGION_METRIC_IDS = [
  "income",
  "safety",
  "employment",
  "cost",
  "chinese_population",
] as const;
type RegionMetricId = (typeof REGION_METRIC_IDS)[number];

function oneOfOrFallback<T extends string>(
  raw: unknown,
  options: readonly T[],
  fallback: T,
): T {
  const res = validateOneOf(raw as string, options);
  return res.ok ? res.value : fallback;
}

/** Safely read `.value` from a validator result.
 *
 * `validateNumber` / `validateString` return `{ ok: true }` without a
 * `value` field — the validator's success type is `value?: never` —
 * so the validated input has to be threaded through. Callers pass the
 * original raw value via `rawInput` so that when the validator
 * produces only `{ ok: true }`, we can hand back the input the caller
 * already had.
 */
function unwrapValue(res: unknown, rawInput?: unknown): unknown {
  if (res && typeof res === "object") {
    const r = res as { ok: boolean; value?: unknown };
    if (r.ok) {
      // Validator produced an explicit value (`validateOneOf`,
      // `validateNullable`'s null branch).
      if ("value" in r && r.value !== undefined) return r.value;
      // Validator only returned `{ ok: true }` (e.g. `validateNumber`).
      // The value to keep IS the input the caller passed in.
      return rawInput;
    }
  }
  return undefined;
}

// ── Manifest ──

export function parseManifest(raw: unknown): DatasetManifest {
  if (!raw || typeof raw !== "object") throw new ValidationError([{ path: "", message: "manifest must be an object" }]);
  const o = raw as Record<string, unknown>;
  if (typeof o.schemaVersion !== "string") throw new ValidationError([{ path: "schemaVersion", message: "missing" }]);
  if (typeof o.generatedAt !== "string") throw new ValidationError([{ path: "generatedAt", message: "missing" }]);
  if (typeof o.previewOnly !== "boolean") throw new ValidationError([{ path: "previewOnly", message: "missing" }]);
  const counts = o.counts as Record<string, unknown> | undefined;
  if (!counts || typeof counts !== "object") throw new ValidationError([{ path: "counts", message: "missing" }]);
  return {
    contractVersion: typeof o.contractVersion === "string" ? o.contractVersion : undefined,
    datasetVersion: typeof o.datasetVersion === "string" ? o.datasetVersion : undefined,
    view: o.view === "preview" ? "preview" : undefined,
    sourceCheckpoint: typeof o.sourceCheckpoint === "string" ? o.sourceCheckpoint : undefined,
    sourceLimited: typeof o.sourceLimited === "boolean" ? o.sourceLimited : undefined,
    incomplete: typeof o.incomplete === "boolean" ? o.incomplete : undefined,
    notFinal: typeof o.notFinal === "boolean" ? o.notFinal : undefined,
    enabledFeatures: Array.isArray(o.enabledFeatures)
      ? o.enabledFeatures.filter((feature): feature is string => typeof feature === "string")
      : undefined,
    disabledFeatures: Array.isArray(o.disabledFeatures)
      ? o.disabledFeatures.filter((feature): feature is string => typeof feature === "string")
      : undefined,
    schemaVersion: o.schemaVersion,
    generatedAt: o.generatedAt,
    sourceCommit: typeof o.sourceCommit === "string" ? o.sourceCommit : "",
    previewOnly: o.previewOnly,
    counts: {
      universities: Number(counts.universities) || 0,
      regionMetrics: Number(counts.regionMetrics) || 0,
      news: Number(counts.news) || 0,
    },
    statusDictionary: parseStatusDictionary(o.statusDictionary),
  };
}

// ── Status dictionary ──

function parseProvenanceStatusLabel(raw: unknown, key: string): ProvenanceStatusLabel {
  if (!raw || typeof raw !== "object") {
    throw new ValidationError([{ path: `statusDictionary.${key}`, message: "must be object" }]);
  }
  const o = raw as Record<string, unknown>;
  if (typeof o.consumerLabel !== "string") {
    throw new ValidationError([{ path: `statusDictionary.${key}.consumerLabel`, message: "missing" }]);
  }
  return {
    consumerLabel: o.consumerLabel,
    technicalLabel: typeof o.technicalLabel === "string" ? o.technicalLabel : undefined,
    icon: typeof o.icon === "string" ? o.icon : undefined,
    tone: oneOfOrFallback(o.tone, TONE, "neutral"),
    description: typeof o.description === "string" ? o.description : undefined,
  };
}

export function parseStatusDictionary(raw: unknown): StatusDictionaryMap {
  if (!raw || typeof raw !== "object") return {};
  const out: StatusDictionaryMap = {};
  for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
    try {
      out[k] = parseProvenanceStatusLabel(v, k);
    } catch {
      // Skip malformed entries; the dictionary may be sparse.
    }
  }
  return out;
}

// ── Source reference ──

export function parseSourceReference(raw: unknown, path: string): SourceReference {
  if (!raw || typeof raw !== "object") throw new ValidationError([{ path, message: "source missing" }]);
  const o = raw as Record<string, unknown>;
  const statusRes = validateOneOf(o.status as string, PROVENANCE_STATUS);
  if (!statusRes.ok) {
    throw new ValidationError([{ path: `${path}.status`, message: "unknown status" }]);
  }
  if (typeof o.url !== "string") throw new ValidationError([{ path: `${path}.url`, message: "missing" }]);
  return {
    url: o.url,
    retrievedAt: typeof o.retrievedAt === "string" ? o.retrievedAt : undefined,
    cachedSnapshotAt: typeof o.cachedSnapshotAt === "string" ? o.cachedSnapshotAt : undefined,
    cacheTtlSeconds: typeof o.cacheTtlSeconds === "number" ? o.cacheTtlSeconds : undefined,
    anchor: typeof o.anchor === "string" ? o.anchor : undefined,
    status: statusRes.value,
  };
}

// ── University summary ──

function parseNullableString(v: unknown): string | null {
  if (v === null || v === undefined || v === "") return null;
  return typeof v === "string" ? v : null;
}

export function parseUniversitySummary(raw: unknown): UniversitySummary {
  if (!raw || typeof raw !== "object") throw new ValidationError([{ path: "", message: "not an object" }]);
  const o = raw as Record<string, unknown>;
  const idCheck = validateString(o.id, { minLength: 1, maxLength: 128 });
  if (!idCheck.ok) throw new ValidationError([{ path: "id", message: "missing or invalid" }]);
  const nameCheck = validateString(o.name, { minLength: 1 });
  if (!nameCheck.ok) throw new ValidationError([{ path: "name", message: "missing" }]);
  // Accept either the recommended `nameZh` or the legacy `chineseName`
  // field. New code should read `nameZh`; legacy code can keep reading
  // `chineseName` until it migrates.
  const nameZhSource = (o.nameZh ?? o.chineseName) as unknown;
  const chineseCheck = validateString(nameZhSource, { minLength: 1 });
  if (!chineseCheck.ok) throw new ValidationError([{ path: "nameZh", message: "missing" }]);
  const tierRes = validateOneOf(o.rankingTier as string, RANKING_TIER);
  if (!tierRes.ok) throw new ValidationError([{ path: "rankingTier", message: "unknown tier" }]);
  const displayTierRes = validateOneOf(o.displayTier as string, DISPLAY_TIER);
  if (!displayTierRes.ok) throw new ValidationError([{ path: "displayTier", message: "unknown" }]);
  const previewOnly = typeof o.previewOnly === "boolean" ? o.previewOnly : true;
  const nullableFields = Array.isArray(o.nullableFields) ? (o.nullableFields as unknown[]).filter((v) => typeof v === "string") as string[] : [];
  const legacyNationalRankRaw =
    o.nationalRanking ??
    (o.rankingSummary as Record<string, unknown> | undefined)?.nationalRank;
  const legacyNationalRank = unwrapValue(
    validateNullable<number>((v) =>
      validateNumber(v, { integer: true, min: 1 }),
    )(legacyNationalRankRaw),
    legacyNationalRankRaw,
  ) as number | null | undefined;
  return {
    id: o.id as string,
    name: o.name as string,
    nameZh: nameZhSource as string,
    chineseName: nameZhSource as string,
    aliases: Array.isArray(o.aliases) ? (o.aliases as unknown[]).filter((v) => typeof v === "string") as string[] : undefined,
    latitude: (unwrapValue(validateNullable<number>(validateNumber)(o.latitude), o.latitude) as number | null) ?? null,
    longitude: (unwrapValue(validateNullable<number>(validateNumber)(o.longitude), o.longitude) as number | null) ?? null,
    rankingSummary: parseRankingSummary(o.rankingSummary),
    costSummary: parseCostSummary(o.costSummary),
    studentFacultyRatio: unwrapValue(validateNullable<number>((v) => validateNumber(v, { min: 0 }))(o.studentFacultyRatio), o.studentFacultyRatio) as number | undefined,
    qualitySummary: parseQualitySummary(o.qualitySummary),
    // Legacy top-level mirrors so existing consumers keep compiling.
    rankingTier: tierRes.value,
    rankingBand: typeof o.rankingBand === "string" ? o.rankingBand : undefined,
    nationalRanking: legacyNationalRank ?? undefined,
    rankingYear: typeof o.rankingYear === "number" ? o.rankingYear : undefined,
    city: typeof o.city === "string" ? o.city : undefined,
    state: typeof o.state === "string" ? o.state : undefined,
    stateFips: typeof o.stateFips === "string" ? o.stateFips : undefined,
    country: typeof o.country === "string" ? o.country : undefined,
    displayTier: displayTierRes.value,
    previewOnly,
    datasetVersion: typeof o.datasetVersion === "string" ? o.datasetVersion : "unknown",
    sourceCommit: typeof o.sourceCommit === "string" ? o.sourceCommit : undefined,
    nullableFields,
  };
}

function parseRankingSummary(raw: unknown): UniversitySummary["rankingSummary"] {
  if (!raw || typeof raw !== "object") return undefined;
  const o = raw as Record<string, unknown>;
  const tierRaw = o.rankingTier;
  const tierRes = validateOneOf(tierRaw as string, RANKING_TIER);
  const nationalRankRaw = o.nationalRank;
  const nationalRank = unwrapValue(validateNullable<number>((v) => validateNumber(v, { integer: true, min: 1 }))(nationalRankRaw), nationalRankRaw) as number | undefined;
  return {
    nationalRank,
    rankingTier: tierRes.ok ? tierRes.value : undefined,
    rankingLabel: typeof o.rankingLabel === "string" ? o.rankingLabel : undefined,
  };
}

function parseCostSummary(raw: unknown): UniversitySummary["costSummary"] {
  if (!raw || typeof raw !== "object") return undefined;
  const o = raw as Record<string, unknown>;
  const minimumUsd = unwrapValue(validateNullable<number>((v) => validateNumber(v, { min: 0 }))(o.minimumUsd), o.minimumUsd) as number | null | undefined;
  const maximumUsd = unwrapValue(validateNullable<number>((v) => validateNumber(v, { min: 0 }))(o.maximumUsd), o.maximumUsd) as number | null | undefined;
  if (minimumUsd === undefined && maximumUsd === undefined) return undefined;
  return {
    minimumUsd: minimumUsd ?? undefined,
    maximumUsd: maximumUsd ?? undefined,
    displayLabel: typeof o.displayLabel === "string" ? o.displayLabel : undefined,
    comparisonSafe: typeof o.comparisonSafe === "boolean" ? o.comparisonSafe : undefined,
  };
}

function parseQualitySummary(raw: unknown): UniversitySummary["qualitySummary"] {
  if (!raw || typeof raw !== "object") return undefined;
  const o = raw as Record<string, unknown>;
  const coveragePercent = typeof o.coveragePercent === "number" ? o.coveragePercent : undefined;
  const warningCodes = Array.isArray(o.warningCodes) ? (o.warningCodes as unknown[]).filter((v) => typeof v === "string") as string[] : undefined;
  return { coveragePercent, warningCodes };
}

export function parseUniversitySummaryList(raw: unknown): UniversitySummary[] {
  if (!Array.isArray(raw)) {
    throw new ValidationError([{ path: "", message: "expected array of summaries" }]);
  }
  return raw.map((item, i) => parseUniversitySummary(item));
}

// ── University detail ──

export function parsePerson(raw: unknown, path: string): Person {
  if (!raw || typeof raw !== "object") throw new ValidationError([{ path, message: "person missing" }]);
  const o = raw as Record<string, unknown>;
  const displayTierRes = validateOneOf(o.displayTier as string, DISPLAY_TIER);
  if (!displayTierRes.ok) {
    return {
      id: typeof o.id === "string" ? o.id : "unknown",
      name: typeof o.name === "string" ? o.name : "unknown",
      relationship: typeof o.relationship === "string" ? o.relationship : "",
      displayTier: "preview",
      quarantined: true,
      status: "source_review_not_completed",
      domain: undefined,
      era: undefined,
      sourceUrl: undefined,
    };
  }
  return {
    id: typeof o.id === "string" ? o.id : "unknown",
    name: typeof o.name === "string" ? o.name : "unknown",
    relationship: typeof o.relationship === "string" ? o.relationship : "",
    domain: typeof o.domain === "string" ? o.domain : undefined,
    era: typeof o.era === "string" ? o.era : undefined,
    sourceUrl: typeof o.sourceUrl === "string" ? o.sourceUrl : undefined,
    status: oneOfOrFallback(o.status, PROVENANCE_STATUS, "source_review_not_completed") as Person["status"],
    displayTier: displayTierRes.value,
    quarantined: typeof o.quarantined === "boolean" ? o.quarantined : displayTierRes.value === "quarantined",
  };
}

export function parseUniversityDetail(raw: unknown): UniversityDetail {
  const base = parseUniversitySummary(raw);
  const o = raw as Record<string, unknown>;
  const programsRaw = Array.isArray(o.programs) ? o.programs : [];
  const topProgramIds = Array.isArray(o.topProgramIds) ? (o.topProgramIds as unknown[]).filter((v) => typeof v === "string") as string[] : [];
  const costRaw = Array.isArray(o.cost) ? o.cost : [];
  const peopleRaw = Array.isArray(o.people) ? o.people : [];
  const sourcesRaw = Array.isArray(o.sources) ? o.sources : [];
  const rankingRaw = Array.isArray(o.ranking) ? o.ranking : [];
  const programs: Program[] = programsRaw.map((p, i) => {
    const pp = p as Record<string, unknown>;
    return {
      id: typeof pp.id === "string" ? pp.id : `program-${i}`,
      name: typeof pp.name === "string" ? pp.name : "",
      category: typeof pp.category === "string" ? pp.category : undefined,
      rank: typeof pp.rank === "number" ? pp.rank : undefined,
      membership: oneOfOrFallback(pp.membership, MEMBERSHIP, "top") as Program["membership"],
      displayTier: oneOfOrFallback(pp.displayTier, DISPLAY_TIER, "preview"),
    };
  });
  const ranking: RankingMembership[] = rankingRaw.map((r) => {
    const rr = r as Record<string, unknown>;
    return {
      system: oneOfOrFallback(rr.system, RANKING_SYSTEM, "QS"),
      year: typeof rr.year === "number" ? rr.year : new Date().getFullYear(),
      position: typeof rr.position === "number" || typeof rr.position === "string" ? (rr.position as number | string) : 0,
      scope: rr.scope === "global" || rr.scope === "national" ? rr.scope : undefined,
      sourceUrl: typeof rr.sourceUrl === "string" ? rr.sourceUrl : undefined,
      displayTier: oneOfOrFallback(rr.displayTier, DISPLAY_TIER, "preview"),
    };
  });
  const cost: CostRecord[] = costRaw.map((c) => {
    const cc = c as Record<string, unknown>;
    const comps = (cc.components as Record<string, unknown> | undefined) ?? {};
    return {
      amount: typeof cc.amount === "number" ? cc.amount : 0,
      currency: "RMB" as const,
      scope: oneOfOrFallback(cc.scope, COST_SCOPE, "unknown"),
      year: typeof cc.year === "number" ? cc.year : new Date().getFullYear(),
      components: {
        tuition: typeof comps.tuition === "boolean" ? comps.tuition : undefined,
        roomBoard: typeof comps.roomBoard === "boolean" ? comps.roomBoard : undefined,
        mandatoryFees: typeof comps.mandatoryFees === "boolean" ? comps.mandatoryFees : undefined,
      },
      sourceUrl: typeof cc.sourceUrl === "string" ? cc.sourceUrl : undefined,
      status: oneOfOrFallback(cc.status, PROVENANCE_STATUS, "source_review_not_completed"),
    };
  });
  const anecdotes: Anecdote[] | undefined = Array.isArray(o.anecdotes)
    ? (o.anecdotes as unknown[]).map((a) => {
        const aa = a as Record<string, unknown>;
        return {
          text: typeof aa.text === "string" ? aa.text : "",
          sourceUrl: typeof aa.sourceUrl === "string" ? aa.sourceUrl : undefined,
          status: oneOfOrFallback(aa.status, PROVENANCE_STATUS, "source_review_not_completed"),
        };
      })
    : undefined;
  const notableAttendance: NotableAttendance[] | undefined = Array.isArray(o.notableAttendance)
    ? (o.notableAttendance as unknown[]).map((a) => {
        const aa = a as Record<string, unknown>;
        return {
          type: "notable_attendance" as const,
          year: typeof aa.year === "number" ? aa.year : undefined,
          context: typeof aa.context === "string" ? aa.context : undefined,
          sourceUrl: typeof aa.sourceUrl === "string" ? aa.sourceUrl : undefined,
          status: oneOfOrFallback(aa.status, PROVENANCE_STATUS, "source_review_not_completed"),
        };
      })
    : undefined;
  const nearbyTowns: NearbyTown[] = Array.isArray(o.nearbyTowns)
    ? (o.nearbyTowns as unknown[]).map((t) => {
        const tt = t as Record<string, unknown>;
        return {
          name: typeof tt.name === "string" ? tt.name : "",
          nameZh: typeof tt.nameZh === "string" ? tt.nameZh : undefined,
          distanceKm: typeof tt.distanceKm === "number" ? tt.distanceKm : undefined,
        };
      })
    : [];
  const qualityBadges: QualityBadge[] = Array.isArray(o.qualityBadges)
    ? (o.qualityBadges as unknown[]).map((b) => {
        const bb = b as Record<string, unknown>;
        return {
          kind: oneOfOrFallback(bb.kind, BADGE_KIND, "gap"),
          label: typeof bb.label === "string" ? bb.label : "",
          detail: typeof bb.detail === "string" ? bb.detail : undefined,
        };
      })
    : [];
  return {
    ...base,
    programs,
    topProgramIds,
    ranking,
    cost,
    studentFacultyRatio: unwrapValue(validateNullable<number>((v) => validateNumber(v, { min: 0 }))(o.studentFacultyRatio), o.studentFacultyRatio) as number | undefined,
    history: typeof o.history === "string" ? o.history : undefined,
    anecdotes,
    notableAttendance,
    people: peopleRaw.map((p, i) => parsePerson(p, `people[${i}]`)),
    nearbyTowns,
    sources: sourcesRaw.map((s, i) => parseSourceReference(s, `sources[${i}]`)),
    warnings: Array.isArray(o.warnings) ? (o.warnings as unknown[]).filter((v) => typeof v === "string") as string[] : [],
    qualityBadges,
    previewMetadata:
      o.previewMetadata && typeof o.previewMetadata === "object"
        ? (o.previewMetadata as UniversityDetail["previewMetadata"])
        : undefined,
  };
}

// ── Region metric ──

export function parseRegionMetricRecord(raw: unknown): RegionMetricRecord {
  if (!raw || typeof raw !== "object") throw new ValidationError([{ path: "", message: "not an object" }]);
  const o = raw as Record<string, unknown>;
  const granularityRes = validateOneOf(o.granularity as string, GRANULARITY);
  if (!granularityRes.ok) throw new ValidationError([{ path: "granularity", message: "unknown" }]);
  if (typeof o.fipsCode !== "string") throw new ValidationError([{ path: "fipsCode", message: "missing" }]);
  if (typeof o.metricId !== "string") throw new ValidationError([{ path: "metricId", message: "missing" }]);
  if (!(REGION_METRIC_IDS as readonly string[]).includes(o.metricId)) {
    // Region metrics must use one of the canonical region-level keys.
    // School-level IDs (toefl/sat/admission_rate/etc.) are not allowed
    // here — they belong to UniversityDetail, not the choropleth layer.
    throw new ValidationError([
      { path: "metricId", message: `metric ${o.metricId} is not a region metric; expected one of ${REGION_METRIC_IDS.join(",")}` },
    ]);
  }
  const valueCheck = validateNumber(o.value, { min: 0, max: 1 });
  if (!valueCheck.ok) throw new ValidationError([{ path: "value", message: "must be 0..1" }]);
  const nullableFields = Array.isArray(o.nullableFields) ? (o.nullableFields as unknown[]).filter((v) => typeof v === "string") as string[] : [];
  return {
    fipsCode: o.fipsCode,
    granularity: granularityRes.value,
    metricId: o.metricId as RegionMetricId,
    value: o.value as number,
    rawValue: typeof o.rawValue === "number" ? (o.rawValue as number) : (o.value as number),
    displayValue: typeof o.displayValue === "string" ? o.displayValue : `${o.value}`,
    year: typeof o.year === "number" ? (o.year as number) : new Date().getFullYear(),
    source: typeof o.source === "string" ? o.source : undefined,
    status: typeof o.status === "string" ? (o.status as RegionMetricRecord["status"]) : undefined,
    previewOnly: typeof o.previewOnly === "boolean" ? (o.previewOnly as boolean) : true,
    nullableFields,
  };
}

export { REGION_METRIC_IDS };
export type { RegionMetricId };

export function parseRegionMetricRecordList(raw: unknown): RegionMetricRecord[] {
  if (!Array.isArray(raw)) {
    throw new ValidationError([{ path: "", message: "expected array" }]);
  }
  return raw.map((r, i) => {
    try {
      return parseRegionMetricRecord(r);
    } catch (e) {
      if (e instanceof ValidationError) {
        throw new ValidationError([{ path: `[${i}]`, message: e.message }]);
      }
      throw e;
    }
  });
}

// ── Region detail ──

export function parseRegionDetail(raw: unknown): RegionDetail {
  if (!raw || typeof raw !== "object") throw new ValidationError([{ path: "", message: "not an object" }]);
  const o = raw as Record<string, unknown>;
  if (typeof o.fipsCode !== "string") throw new ValidationError([{ path: "fipsCode", message: "missing" }]);
  const granularityRes = validateOneOf(o.granularity as string, GRANULARITY);
  if (!granularityRes.ok) throw new ValidationError([{ path: "granularity", message: "unknown" }]);
  return {
    fipsCode: o.fipsCode,
    granularity: granularityRes.value,
    name: typeof o.name === "string" ? o.name : "",
    nameEn: typeof o.nameEn === "string" ? o.nameEn : undefined,
    metrics: Array.isArray(o.metrics) ? (o.metrics as unknown[]).map((m, i) => {
      try { return parseRegionMetricRecord(m); } catch (e) {
        throw e;
      }
    }) : [],
    universityCount: typeof o.universityCount === "number" ? (o.universityCount as number) : 0,
    topUniversities: Array.isArray(o.topUniversities) ? (o.topUniversities as unknown[]).map((s) => parseUniversitySummary(s)) : [],
    displayTier: oneOfOrFallback(o.displayTier, DISPLAY_TIER, "preview"),
    previewOnly: typeof o.previewOnly === "boolean" ? o.previewOnly : true,
    warnings: Array.isArray(o.warnings) ? (o.warnings as unknown[]).filter((v) => typeof v === "string") as string[] : [],
  };
}

// ── News ──

export function parseNewsArticleList(raw: unknown): NewsArticle[] {
  if (!Array.isArray(raw)) throw new ValidationError([{ path: "", message: "expected array" }]);
  return raw.map((a, i) => {
    const o = a as Record<string, unknown>;
    if (!o || typeof o !== "object") throw new ValidationError([{ path: `news[${i}]`, message: "not object" }]);
    if (typeof o.id !== "string") throw new ValidationError([{ path: `news[${i}].id`, message: "missing" }]);
    if (typeof o.title !== "string") throw new ValidationError([{ path: `news[${i}].title`, message: "missing" }]);
    return {
      id: o.id,
      title: o.title,
      titleEn: typeof o.titleEn === "string" ? o.titleEn : undefined,
      summary: typeof o.summary === "string" ? o.summary : undefined,
      source: typeof o.source === "string" ? o.source : "",
      url: typeof o.url === "string" ? o.url : "#",
      publishedAt: typeof o.publishedAt === "string" ? o.publishedAt : new Date().toISOString(),
      category: typeof o.category === "string" ? o.category : "admissions",
      displayTier: oneOfOrFallback(o.displayTier, DISPLAY_TIER, "preview"),
    };
  });
}

// ── Search ──

export function parseUniversitySearchResultList(raw: unknown): UniversitySearchResult[] {
  if (!Array.isArray(raw)) throw new ValidationError([{ path: "", message: "expected array" }]);
  return raw.map((r, i) => {
    const o = r as Record<string, unknown>;
    const matchedField = (o.matchedField as UniversitySearchResult["matchedField"]);
    return {
      university: parseUniversitySummary(o.university),
      matchedField: (matchedField === "name" || matchedField === "chineseName" || matchedField === "city" || matchedField === "state" || matchedField === "program")
        ? matchedField
        : "name",
    };
  });
}

// ── Helper export (kept for tests) ──

export const __test = { DISPLAY_TIER, PROVENANCE_STATUS, RANKING_TIER, GRANULARITY, REGION_METRIC_IDS };

// Silence unused-import warnings when validators are used across files.
void combine;
