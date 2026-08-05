import type {
  PreviewField,
  PreviewMetadata,
  ProvenanceStatus,
  SourceReference,
  StatusDictionaryMap,
  UniversityDetail,
  UniversitySummary,
} from "@/domain/dataset";
import { FALLBACK_STATUS_DICTIONARY } from "@/config/status-dictionary";

export const STAGE5_CONTRACT_VERSION = "pathos-preview-v1";
const RMB_PER_USD = 7.2;

export interface Stage5Manifest {
  contractVersion: string;
  schemaVersion: string;
  datasetVersion: string;
  view: "preview";
  sourceCheckpoint: string;
  sourceCommit: string;
  generatedAt: string;
  schoolCount: number;
  summaryCount: number;
  detailCount: number;
  verifiedRecordCount: number;
  sourceLimited: true;
  incomplete: true;
  notFinal: true;
  previewOnly: true;
  counts: { universities: number; regionMetrics: number; news: number };
}

export interface Stage5RankingSummary {
  nationalRank: number | null;
  rankingTier: string;
  rankingLabel: string;
  status: string;
  filterBehavior: string;
  sourceIds: string[];
}

export interface Stage5Summary {
  id: string;
  name: string;
  nameZh: string;
  chineseName: string;
  aliases: string[];
  city: string;
  state: string;
  region: string;
  country: string;
  topPrograms: string[];
  latitude: number;
  longitude: number;
  schoolType: string;
  rankingSummary: Stage5RankingSummary;
  costSummary: {
    minimumUsd: number | null;
    maximumUsd: number | null;
    displayLabel: string;
    comparisonSafe: boolean;
  };
  studentFacultyRatio: number | null;
  qualitySummary: { warningCodes: string[] };
  /** Flat summary-level fields populated by db:enrich from university_details. */
  acceptanceRate?: number | null;
  sat25?: number | null;
  sat75?: number | null;
  graduationRate?: number | null;
  retentionRate?: number | null;
  /**
   * Compact enrollment snapshot used by the summary list view (map,
   * calculator, search). Mirrors Stage5Detail.previewMetadata.enrollment
   * but is populated from the universities-table payload so it does not
   * require a per-school detail fetch.
   */
  enrollment: {
    undergraduate: PreviewField<number>;
    graduate: PreviewField<number>;
    total: PreviewField<number>;
  };
  warningSummary: { count: number; codes: string[]; hasWarnings: boolean };
  displayTier: "preview";
  previewOnly: true;
  datasetVersion: string;
  sourceCommit: string;
}

export interface Stage5Detail extends Stage5Summary {
  programs: Array<{
    id: string;
    name: string;
    rank: number | null;
    sourceIds: string[];
  }>;
  allMajors: Array<{
    name: string;
    displayName: string;
    degreeType: string | null;
    listType: string | null;
    sourceIds: string[];
    status: string;
    warnings: string[];
  }>;
  allMajorsStatus: {
    status: "source_limited" | "not_reported";
    nullReason: string | null;
  };
  enrollment: PreviewMetadata["enrollment"];
  admissions: PreviewMetadata["admissions"];
  geography: PreviewMetadata["geography"];
  programPeopleGaps: PreviewMetadata["programPeopleGaps"];
  history: { value: string | null; status: string; sourceIds: string[] };
  anecdotes: Array<{ text: string; type?: string; sourceIds: string[] }>;
  notableAttendance: Array<{
    personName: string;
    relationship?: string;
    program?: string;
    sourceIds: string[];
  }>;
  people: Array<{
    id: string;
    name: string;
    relationshipType?: string;
    verificationStatus: string;
    sourceIds: string[];
    displayTier: string;
    quarantined: boolean;
  }>;
  nearbyTowns: Array<{ name: string; distance?: number }>;
  rawCostRecords: Array<{
    amountUsd: number;
    currency: "USD";
    scope: string;
    academicYear: string;
    sourceIds: string[];
  }>;
}

export interface Stage5SourceIndex {
  sources: Array<{
    sourceId: string;
    publisher: string;
    sourceType: string;
    url: string | null;
    status: string;
  }>;
}

function object(raw: unknown, path: string): Record<string, unknown> {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error(`${path} must be an object`);
  }
  return raw as Record<string, unknown>;
}

function string(raw: unknown, path: string): string {
  if (typeof raw !== "string" || raw.length === 0) throw new Error(`${path} must be a string`);
  return raw;
}

function number(raw: unknown, path: string): number {
  if (typeof raw !== "number" || !Number.isFinite(raw)) throw new Error(`${path} must be a number`);
  return raw;
}

function stringArray(raw: unknown, path: string): string[] {
  if (!Array.isArray(raw) || raw.some((item) => typeof item !== "string")) {
    throw new Error(`${path} must be a string array`);
  }
  return raw as string[];
}

export function parseStage5Manifest(raw: unknown): Stage5Manifest {
  const value = object(raw, "manifest");
  if (value.contractVersion !== STAGE5_CONTRACT_VERSION) {
    throw new Error(`manifest.contractVersion unsupported: ${String(value.contractVersion)}`);
  }
  if (value.view !== "preview") throw new Error("manifest.view must be preview");
  if (value.schoolCount !== 62 || value.summaryCount !== 62 || value.detailCount !== 62) {
    throw new Error("manifest counts must be 62/62/62");
  }
  if (value.verifiedRecordCount !== 904) throw new Error("manifest verifiedRecordCount must be 904");
  if (value.sourceLimited !== true || value.incomplete !== true || value.notFinal !== true) {
    throw new Error("manifest preview limitations missing");
  }
  return value as unknown as Stage5Manifest;
}

function parseEnrollmentFieldFromString(raw: unknown, path: string): PreviewField<number> {
  if (raw === null || raw === undefined) {
    return { unit: null, scope: null, value: null, status: "not_reported", warnings: [], sourceIds: [], nullReason: "missing", referenceYear: null };
  }
  if (typeof raw === "string") {
    if (raw === "" || raw === "null") {
      return { unit: null, scope: null, value: null, status: "not_reported", warnings: [], sourceIds: [], nullReason: "missing", referenceYear: null };
    }
    try { raw = JSON.parse(raw); } catch (e) { throw new Error(`${path} not parseable: ${raw}`); }
  }
  return parseField<number>(raw, path);
}

export function parseStage5Summary(raw: unknown): Stage5Summary {
  const value = object(raw, "summary");
  const id = string(value.id, "summary.id");
  const latitude = number(value.latitude, `${id}.latitude`);
  const longitude = number(value.longitude, `${id}.longitude`);
  if (latitude < -90 || latitude > 90) throw new Error(`${id}.latitude out of range`);
  if (longitude < -180 || longitude > 180) throw new Error(`${id}.longitude out of range`);
  if (latitude === 0 && longitude === 0) throw new Error(`${id} has forbidden 0,0 coordinates`);
  const ranking = object(value.rankingSummary, `${id}.rankingSummary`);
  if (
    ranking.nationalRank !== null &&
    (typeof ranking.nationalRank !== "number" || ranking.nationalRank < 1)
  ) {
    throw new Error(`${id}.rankingSummary.nationalRank invalid`);
  }
  if (ranking.nationalRank === null && ranking.filterBehavior !== "exclude_from_numeric_range") {
    throw new Error(`${id}.rankingSummary null behavior invalid`);
  }
  string(value.name, `${id}.name`);
  string(value.nameZh, `${id}.nameZh`);
  string(value.city, `${id}.city`);
  string(value.state, `${id}.state`);
  string(value.region, `${id}.region`);
  stringArray(value.aliases, `${id}.aliases`);
  stringArray(value.topPrograms, `${id}.topPrograms`);
  // Enrollment fields arrive as JSON-encoded strings in the universities
  // payload (vs parsed objects in university_details). Coerce to PreviewField.
  const enrollment = {
    undergraduate: parseEnrollmentFieldFromString(value.undergraduateEnrollment, `${id}.enrollment.undergraduate`),
    graduate: parseEnrollmentFieldFromString(value.graduateEnrollment, `${id}.enrollment.graduate`),
    total: parseEnrollmentFieldFromString(value.totalEnrollment, `${id}.enrollment.total`),
  };
  // Flat summary-level fields populated by db:enrich (raw numbers) or
  // legacy artifact (wrapper object with .value). Accept both forms.
  const flatNumber = (raw: unknown): number | null => {
    if (typeof raw === "number" && Number.isFinite(raw)) return raw;
    if (raw !== null && typeof raw === "object") {
      const v = (raw as { value?: unknown }).value;
      if (typeof v === "number" && Number.isFinite(v)) return v;
    }
    return null;
  };
  const acceptanceRate = flatNumber(value.acceptanceRate);
  const sat25 = flatNumber(value.sat25);
  const sat75 = flatNumber(value.sat75);
  const graduationRate = flatNumber(value.graduationRate);
  const retentionRate = flatNumber(value.retentionRate);
  return { ...(value as Record<string, unknown>), enrollment, acceptanceRate, sat25, sat75, graduationRate, retentionRate } as unknown as Stage5Summary;
}

export function parseStage5Summaries(raw: unknown): Stage5Summary[] {
  if (!Array.isArray(raw)) throw new Error("summaries must be an array");
  const rows = raw.map(parseStage5Summary);
  const ids = rows.map((row) => row.id);
  if (new Set(ids).size !== ids.length) throw new Error("duplicate university ID");
  return rows;
}

function parseField<T>(raw: unknown, path: string): PreviewField<T> {
  const value = object(raw, path);
  string(value.status, `${path}.status`);
  if (!Array.isArray(value.warnings)) throw new Error(`${path}.warnings must be an array`);
  return value as unknown as PreviewField<T>;
}

const KNOWN_DETAIL_STATUSES = new Set([
  "verified",
  "verified_derived_same_scope",
  "verified_middle_50",
  "verified_place",
  "ranked_in_selected_national_family",
  "not_in_current_national_scope",
  "not_reported",
  "ai_assisted",
  "partial",
  "pending_external_access",
  "county_only_valid",
  "source_review_not_completed",
  "source_limited",
  "live_verified_exact",
  "live_verified_normalized",
  "warning",
]);

function validateStatuses(raw: unknown, path: string): void {
  if (Array.isArray(raw)) {
    raw.forEach((value, index) => validateStatuses(value, `${path}[${index}]`));
    return;
  }
  if (!raw || typeof raw !== "object") return;
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    if (key === "status" || key === "verificationStatus") {
      if (typeof value !== "string" || !KNOWN_DETAIL_STATUSES.has(value)) {
        throw new Error(`${path}.${key} has unknown status: ${String(value)}`);
      }
    } else {
      validateStatuses(value, `${path}.${key}`);
    }
  }
}

export function parseStage5Detail(raw: unknown): Stage5Detail {
  const summary = parseStage5Summary(raw);
  const value = object(raw, "detail");
  const enrollment = object(value.enrollment, `${summary.id}.enrollment`);
  for (const scope of ["undergraduate", "graduate", "total"]) {
    const field = parseField(enrollment[scope], `${summary.id}.enrollment.${scope}`);
    if (field.referenceYear !== 2019 || !field.warnings.includes("stale_reference_year")) {
      throw new Error(`${summary.id}.enrollment.${scope} stale-year contract missing`);
    }
  }
  const admissions = object(value.admissions, `${summary.id}.admissions`);
  for (const policy of ["testPolicy", "englishPolicy"]) {
    const field = parseField(admissions[policy], `${summary.id}.admissions.${policy}`);
    if (field.value !== null || field.status !== "pending_external_access") {
      throw new Error(`${summary.id}.${policy} pending contract invalid`);
    }
  }
  const people = Array.isArray(value.people) ? value.people : [];
  if (people.some((person) => object(person, "person").quarantined === true)) {
    throw new Error(`${summary.id} exposes quarantined people`);
  }
  if (!Array.isArray(value.allMajors)) {
    throw new Error(`${summary.id}.allMajors must be an array`);
  }
  validateStatuses(value, summary.id);
  return value as unknown as Stage5Detail;
}

export function parseStage5SourceIndex(raw: unknown): Stage5SourceIndex {
  const value = object(raw, "source-index");
  if (!Array.isArray(value.sources)) throw new Error("source-index.sources must be an array");
  const sources = value.sources.map((rawSource, index) => {
    const source = object(rawSource, `sources[${index}]`);
    string(source.sourceId, `sources[${index}].sourceId`);
    string(source.publisher, `sources[${index}].publisher`);
    string(source.sourceType, `sources[${index}].sourceType`);
    string(source.status, `sources[${index}].status`);
    if (!Array.isArray(source.scope) && typeof source.scope !== "string") {
      throw new Error(`sources[${index}].scope invalid`);
    }
    if (
      source.referenceYear !== null &&
      source.referenceYear !== undefined &&
      typeof source.referenceYear !== "string" &&
      typeof source.referenceYear !== "number"
    ) {
      throw new Error(`sources[${index}].referenceYear invalid`);
    }
    if (source.url !== null && typeof source.url !== "string") {
      throw new Error(`sources[${index}].url invalid`);
    }
    return source;
  });
  if (new Set(sources.map((source) => source.sourceId)).size !== sources.length) {
    throw new Error("duplicate source ID");
  }
  return value as unknown as Stage5SourceIndex;
}

export interface Stage5RegionEnvelope {
  status: string;
  records: unknown[];
  choroplethEnabled: boolean;
  disabledReason: string;
  metricMetadata: Array<{
    metricId: string;
    status: "deferred";
    unit: null;
  }>;
}

export function parseStage5RegionEnvelope(raw: unknown): Stage5RegionEnvelope {
  const value = object(raw, "region-metrics");
  if (value.status !== "blocked" || value.choroplethEnabled !== false) {
    throw new Error("region metrics must remain blocked");
  }
  if (!Array.isArray(value.records) || value.records.length !== 0) {
    throw new Error("blocked region metrics must have no records");
  }
  if (typeof value.disabledReason !== "string" || !value.disabledReason) {
    throw new Error("blocked region metrics require a disabled reason");
  }
  if (!Array.isArray(value.metricMetadata) || value.metricMetadata.length === 0) {
    throw new Error("blocked region metrics require metric metadata");
  }
  return value as unknown as Stage5RegionEnvelope;
}

function rankingTier(rank: number | null): "top20" | "top50" | "top100" | "other" {
  if (rank === null) return "other";
  if (rank <= 20) return "top20";
  if (rank <= 50) return "top50";
  if (rank <= 100) return "top100";
  return "other";
}

export function normalizeStage5Summary(raw: Stage5Summary): UniversitySummary {
  const rank = raw.rankingSummary.nationalRank;
  const tier = rankingTier(rank);
  const nullableFields = [
    ...(rank === null ? ["rankingSummary.nationalRank"] : []),
    ...(raw.studentFacultyRatio === null ? ["studentFacultyRatio"] : []),
  ];
  return {
    id: raw.id,
    name: raw.name,
    nameZh: raw.nameZh,
    chineseName: raw.nameZh,
    aliases: raw.aliases,
    latitude: raw.latitude,
    longitude: raw.longitude,
    rankingSummary: {
      nationalRank: rank,
      rankingTier: tier,
      rankingLabel: raw.rankingSummary.rankingLabel,
    },
    costSummary: raw.costSummary,
    studentFacultyRatio: raw.studentFacultyRatio ?? undefined,
    enrollmentSummary: {
      undergraduate: raw.enrollment?.undergraduate?.value ?? null,
      graduate: raw.enrollment?.graduate?.value ?? null,
      total: raw.enrollment?.total?.value ?? null,
      referenceYear: typeof raw.enrollment?.undergraduate?.referenceYear === "number" ? raw.enrollment.undergraduate.referenceYear : null,
    },
    qualitySummary: { warningCodes: raw.qualitySummary.warningCodes },
    acceptanceRate: raw.acceptanceRate ?? null,
    sat25: raw.sat25 ?? null,
    sat75: raw.sat75 ?? null,
    graduationRate: raw.graduationRate ?? null,
    retentionRate: raw.retentionRate ?? null,
    rankingTier: tier,
    rankingBand: raw.rankingSummary.rankingLabel,
    nationalRanking: rank ?? undefined,
    city: raw.city,
    state: raw.state,
    country: raw.country,
    displayTier: "preview",
    previewOnly: true,
    datasetVersion: raw.datasetVersion,
    sourceCommit: raw.sourceCommit,
    nullableFields,
  };
}

function collectSourceIds(raw: unknown, output = new Set<string>()): Set<string> {
  if (Array.isArray(raw)) raw.forEach((item) => collectSourceIds(item, output));
  else if (raw && typeof raw === "object") {
    for (const [key, child] of Object.entries(raw as Record<string, unknown>)) {
      if (key === "sourceIds" && Array.isArray(child)) {
        child.forEach((sourceId) => typeof sourceId === "string" && output.add(sourceId));
      } else collectSourceIds(child, output);
    }
  }
  return output;
}

function provenanceStatus(raw: string): ProvenanceStatus {
  if (
    raw === "verified" ||
    raw === "official" ||
    raw === "official_institutional" ||
    raw === "high" ||
    raw === "live_verified_exact"
  ) {
    return "live_verified_exact";
  }
  if (
    raw === "source_limited" ||
    raw === "secondary_user_provided" ||
    raw === "live_verified_normalized" ||
    raw === "ai_assisted"
  ) {
    return "live_verified_normalized";
  }
  throw new Error(`Unknown source provenance status: ${raw}`);
}

export function normalizeStage5Detail(
  raw: Stage5Detail,
  sourceIndex: Stage5SourceIndex,
): UniversityDetail {
  const base = normalizeStage5Summary(raw);
  const sourceIds = collectSourceIds(raw);
  const sources: SourceReference[] = sourceIndex.sources
    .filter((source) => sourceIds.has(source.sourceId) && source.url)
    .map((source) => ({
      url: source.url as string,
      status: provenanceStatus(source.status),
      anchor: source.sourceId,
    }));
  const programs = raw.programs.map((program) => ({
    id: program.id,
    name: program.name,
    rank: program.rank ?? undefined,
    membership: "top" as const,
    displayTier: "preview" as const,
  }));
  const cost = raw.rawCostRecords
    .filter((record) => record.amountUsd > 0)
    .map((record) => ({
      amount: Math.round(record.amountUsd * RMB_PER_USD),
      currency: "RMB" as const,
      scope: ["in_state", "out_of_state", "international"].includes(record.scope)
        ? (record.scope as "in_state" | "out_of_state" | "international")
        : ("unknown" as const),
      year: Number(record.academicYear.slice(0, 4)),
      components: { tuition: true },
      status: "live_verified_exact" as const,
    }));
  const previewMetadata: PreviewMetadata = {
    allMajors: raw.allMajors,
    allMajorsStatus: raw.allMajorsStatus,
    enrollment: raw.enrollment,
    admissions: raw.admissions,
    geography: raw.geography,
    programPeopleGaps: raw.programPeopleGaps,
  };
  return {
    ...base,
    programs,
    topProgramIds: programs.map((program) => program.id),
    ranking: [],
    cost,
    history: raw.history.value ?? undefined,
    anecdotes: raw.anecdotes.map((row) => ({
      text: row.text,
      status: "live_verified_exact",
    })),
    notableAttendance: raw.notableAttendance.map((row) => ({
      type: "notable_attendance",
      context: [row.personName, row.program].filter(Boolean).join(" · "),
      status: "live_verified_exact",
    })),
    people: raw.people
      .filter((person) => !person.quarantined && person.displayTier !== "quarantined")
      .map((person) => ({
        id: person.id,
        name: person.name,
        relationship: person.relationshipType ?? "",
        status: provenanceStatus(person.verificationStatus),
        displayTier: "preview",
        quarantined: false,
      })),
    nearbyTowns: raw.nearbyTowns.map((town) => ({
      name: town.name,
      distanceKm: town.distance,
    })),
    sources,
    warnings: raw.warningSummary.codes,
    qualityBadges: raw.warningSummary.codes.map((code) => ({
      kind: "warning" as const,
      label: code,
    })),
    previewMetadata,
  };
}

export function normalizeStage5StatusDictionary(raw: unknown): StatusDictionaryMap {
  const value = object(raw, "status-dictionary");
  const statuses =
    value.statuses && typeof value.statuses === "object"
      ? (value.statuses as Record<string, unknown>)
      : {};
  const output: StatusDictionaryMap = { ...FALLBACK_STATUS_DICTIONARY };
  for (const key of Object.keys(statuses)) {
    output[key] = output[key] ?? {
      consumerLabel: "数据补充中",
      technicalLabel: key,
      icon: "hourglass",
      tone: "neutral",
    };
  }
  return output;
}

// test write
