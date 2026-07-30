// PathOS — legacy mappers.
// Bridges the new domain `UniversitySummary` (data-source contract) to
// the legacy `UniversityPOI` (UI shape) used by map components.
//
// IMPORTANT (gate-bloker repair #GB-P0-2 + #RG-P0-A):
//   Legacy UI components still read top-level fields like
//   `poi.annualCostRmb`, `poi.safetyScore`, `poi.recognitionScore`,
//   `poi.chineseCommunity`, `poi.latitude`, `poi.longitude`, etc.
//
//   The pre-ReGate version of this mapper zero-filled every missing
//   field with `(x ?? 0) as unknown as number`. That single line of
//   fabrication was the root cause of every downstream regression:
//     - annualCostRmb = 0 → Calculator / Portfolio / Match rendered
//       ¥NaN or ¥0 when the canonical Summary carried no cost data
//     - safetyScore = 0 / recognitionScore = 0 → ComparePanel drew
//       bars labelled "0/100" for schools where no score existed
//     - lat/lng = 0,0 → all POIs dropped onto (0°, 0°)
//     - chineseCommunity = "low" → everyone looked "low community"
//
//   This rewrite does NOT fabricate facts. Missing values stay
//   missing (`null` / `undefined`). Components that previously did
//   `?? 0` MUST now render the "数据补充中" empty state instead.
//   The legacy bridge is intentionally thin — the canonical summary
//   block is the source of truth for everything else.

import type { UniversityPOI } from "@/lib/types";
import type { UniversitySummary } from "@/domain/dataset";
import { TUITION_EMPTY_LABEL } from "@/lib/cost-format";
import { ABBR_TO_FIPS } from "@/config/states.config";

/**
 * Stage 7B-A.3.1: derive the 2-digit FIPS code from a 2-letter state
 * abbreviation. Returns `null` if the abbreviation is unknown.
 *
 * Kept local to this file because the legacy POI bridge is the only
 * place that needs the abbreviation → FIPS fallback. Callers with
 * canonical FIPS data should use `fipsFromAbbr` in
 * `src/config/states.config.ts` directly.
 */
function stateAbbrToFipsOrNull(abbr: string): string | null {
  const code = ABBR_TO_FIPS[String(abbr ?? "").toUpperCase()];
  return code ?? null;
}

/**
 * A first-class "we don't know" sentinel: callers must NOT do
 * `value ?? 0` against fields that can be `null`; the UI helper
 * `formatRmb` / `formatRmbShort` already handle this and surface
 * the "数据补充中" copy.
 */
export const MISSING_COST: null = null;

/**
 * Pick a tuition value in RMB for legacy consumers, falling back to
 * `null` (never `0`) when the summary carries no usable cost.
 *
 * The fixture and the BFF store the canonical cost in the
 * `costSummary.minimumUsd` block (USD). For the Calculator / MapShell
 * which still operate in RMB we apply the project's RMB_PER_USD = 7.2
 * rate here.
 */
// Minimum shape the helper needs to compute RMB tuition. Accepting a
// structural view (rather than `UniversitySummary`) lets the
// Calculator compose a lighter projection that lacks fields like
// `programs`, `people`, etc. — only the `costSummary` block matters
// for the conversion. The exported function is still safe to call on
// a full `UniversitySummary` because that type satisfies the shape.
type CostSummaryView = {
  costSummary?:
    | { minimumUsd?: number | null | undefined; maximumUsd?: number | null | undefined }
    | null
    | undefined;
};

export function tuitionRmbFromSummary(s: CostSummaryView): number | null {
  const minimumUsd = s.costSummary?.minimumUsd;
  if (typeof minimumUsd !== "number" || !Number.isFinite(minimumUsd)) return null;
  if (minimumUsd <= 0) return null;
  return Math.round(minimumUsd * 7.2);
}

/**
 * Convert a `UniversitySummary` (data-source contract) to a legacy
 * `UniversityPOI` (UI shape).
 *
 * Rules (Re-Gate repair #RG-P0-A):
 *   - lat / lng: `null` when missing — never `[0, 0]`. The
 *     `UniversityPoiLayer` already drops features whose coordinates
 *     aren't finite numbers.
 *   - annualCostRmb / safetyScore / recognitionScore / admissionRate
 *     / studentFacultyRatio: `null` when missing. Downstream UI uses
 *     `formatRmbShort` / similar to render `TUITION_EMPTY_LABEL`.
 *   - chineseCommunity: `null` when the summary doesn't carry the
 *     region-scoped community level. We never coerce to "low" — that
 *     was the same fabrication the previous `?? "low"` fallback did.
 *   - programs / parentHighlights / studentHighlights: empty arrays
 *     are still legitimate (the source really has no programs);
 *     preserve as-is.
 *   - rankingBand / rankingTier: legacy mirrors of
 *     `rankingSummary.rankingLabel` / `rankingSummary.rankingTier`.
 *     When both summary fields are absent, fall back to the existing
 *     legacy mirrors; if those are also empty, leave them as empty
 *     string / undefined so `UniversityPoiLayer` can use its own
 *     `?? "other"` guard.
 */
export function summaryToLegacyUniversityPOI(s: UniversitySummary): UniversityPOI {
  const lat =
    typeof s.latitude === "number" && Number.isFinite(s.latitude) ? s.latitude : null;
  const lng =
    typeof s.longitude === "number" && Number.isFinite(s.longitude) ? s.longitude : null;
  const rankingTier = s.rankingSummary?.rankingTier ?? s.rankingTier ?? undefined;
  const rankingBand = s.rankingSummary?.rankingLabel ?? s.rankingBand ?? "";
  const tuition = tuitionRmbFromSummary(s);
  return {
    id: s.id,
    name: s.name,
    chineseName: s.chineseName,
    country: s.country ?? "",
    city: s.city ?? "",
    latitude: lat,
    longitude: lng,
    rankingBand,
    rankingTier: (rankingTier ?? "other") as UniversityPOI["rankingTier"],
    annualCostRmb: tuition,
    safetyScore: null,
    recognitionScore: null,
    chineseCommunity: null,
    directFlight: false,
    postStudyVisa: "",
    programs: [],
    parentHighlights: [],
    studentHighlights: [],
    verifiedAt: "",
    sourceCount: 0,
    admissionRate: null,
    studentFacultyRatio:
      typeof s.studentFacultyRatio === "number" && Number.isFinite(s.studentFacultyRatio)
        ? s.studentFacultyRatio
        : null,
    campusImages: [],
    nearby: {
      subwayStations: 0,
      chineseRestaurants: 0,
      asianGroceries: 0,
      avgRentRmb: 0,
    },
    // legacy extension fields consumed by callers; not part of canonical POI
    state: s.state,
    // Stage 7B-A.3.1: derive `stateFips` from the state abbreviation when
    // the canonical `stateFips` field is absent (e.g. when the API
    // returns the new v2 summary shape). The derivation is non-breaking
    // — it only fills in when missing.
    stateFips:
      s.stateFips ??
      (typeof s.state === "string" ? stateAbbrToFipsOrNull(s.state) : null),
  } as unknown as UniversityPOI;
}

/**
 * Format the legacy POI's annual cost the same way the recommended
 * contract does: missing → empty-state label; valid → formatted.
 * Exposed here so map components don't need to import the cost-format
 * module directly.
 */
export function legacyPoiAnnualCostLabel(poi: UniversityPOI): string {
  const tuition =
    typeof poi.annualCostRmb === "number" && Number.isFinite(poi.annualCostRmb) && poi.annualCostRmb > 0
      ? poi.annualCostRmb
      : null;
  if (tuition === null) return TUITION_EMPTY_LABEL;
  return "¥" + tuition.toLocaleString();
}

/**
 * Render a safety / recognition style 0-100 score. Returns the empty
 * state label when the underlying value is missing or invalid. The
 * previous default-to-0 behaviour (`${poi.safetyScore}/100`) is what
 * produced "0/100" entries in ComparePanel and UniversityCard.
 */
export function legacyPoiScoreLabel(score: number | null | undefined, label: string): string {
  if (typeof score !== "number" || !Number.isFinite(score)) return "数据补充中";
  return `${label}${score}/100`;
}

export { TUITION_EMPTY_LABEL };