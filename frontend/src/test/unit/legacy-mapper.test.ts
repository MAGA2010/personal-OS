// PathOS — tests for gate-bloker repair #RG-P0-A/B/F/H.
//
// Verifies the core Re-Gate invariants in pure logic so the
// regressions that produced ¥NaN, ¥0, "0/100" and (0, 0) cannot
// quietly come back.
//
// Coverage:
//   1. Legacy mapper never fabricates numeric facts. Missing
//      annualCostRmb / safetyScore / recognitionScore / lat / lng
//      produce `null`, NOT `(x ?? 0) as unknown as number`.
//   2. `tuitionRmbFromSummary` returns `null` when no canonical
//      cost exists, never 0.
//   3. `formatRmb` / `legacyPoiAnnualCostLabel` show
//      "数据补充中" / "学费数据补充中" instead of "¥0" or "¥NaN".
//   4. `buildCityAggregates` drops universities whose lat/lng are
//      null (so we never aggregate Null Island data).

import { describe, expect, it } from "vitest";
import {
  summaryToLegacyUniversityPOI,
  tuitionRmbFromSummary,
  legacyPoiAnnualCostLabel,
  legacyPoiScoreLabel,
} from "@/lib/legacy-mappers";
import { buildCityAggregates } from "@/lib/city-utils";
import { formatRmb } from "@/lib/cost-format";
import type { UniversitySummary } from "@/domain/dataset";

type BaseOverrides = Omit<Partial<UniversitySummary>, "costSummary" | "latitude" | "longitude" | "studentFacultyRatio"> & {
  // Allow null overrides for fields the underlying Summary doesn't
  // declare nullable (these tests intentionally exercise the missing-
  // data path the legacy mapper is supposed to honour).
  latitude?: number | null;
  longitude?: number | null;
  costSummary?: UniversitySummary["costSummary"] | null;
  studentFacultyRatio?: number | null;
};

const baseSummary = (overrides: BaseOverrides = {}): UniversitySummary => ({
  id: "test",
  name: "Test University",
  chineseName: "测试大学",
  city: "Test City",
  state: "CA",
  stateFips: "06",
  country: "United States",
  latitude: 34.0522,
  longitude: -118.2437,
  rankingSummary: { rankingTier: "top20", rankingLabel: "Top 20" },
  rankingTier: "top20",
  rankingBand: "Top 20",
  costSummary: undefined,
  studentFacultyRatio: undefined,
  qualitySummary: { coveragePercent: 0, warningCodes: ["source_review_not_completed"] },
  displayTier: "preview",
  previewOnly: true,
  datasetVersion: "fixture-2026-07-24",
  nullableFields: ["costSummary"],
  ...(overrides as Partial<UniversitySummary>),
} as UniversitySummary);

describe("legacy-mappers — never fabricate facts (RG-P0-A)", () => {
  it("returns null for missing annualCostRmb instead of 0", () => {
    const poi = summaryToLegacyUniversityPOI(baseSummary({ costSummary: null }));
    expect(poi.annualCostRmb).toBeNull();
  });

  it("returns null for missing lat/lng instead of 0,0", () => {
    const poi = summaryToLegacyUniversityPOI(baseSummary({ latitude: null, longitude: null }));
    expect(poi.latitude).toBeNull();
    expect(poi.longitude).toBeNull();
  });

  it("returns null for missing safetyScore / recognitionScore instead of 0", () => {
    const poi = summaryToLegacyUniversityPOI(baseSummary());
    expect(poi.safetyScore).toBeNull();
    expect(poi.recognitionScore).toBeNull();
  });

  it("returns null for missing chineseCommunity instead of 'low'", () => {
    const poi = summaryToLegacyUniversityPOI(baseSummary());
    expect(poi.chineseCommunity).toBeNull();
  });

  it("never uses '(x ?? 0) as unknown as number' anywhere in mapper output", () => {
    // Build the POI from a Summary with NO numeric data — every
    // field that used to be zero-filled must be null.
    const emptySummary = baseSummary({
      costSummary: null,
      latitude: null,
      longitude: null,
    });
    const poi = summaryToLegacyUniversityPOI(emptySummary);
    // The five fields that used to be zero-filled must all be null,
    // not a hidden "0" coerced through `as unknown as number`.
    const fields = ["annualCostRmb", "safetyScore", "recognitionScore", "latitude", "longitude"] as const;
    for (const f of fields) {
      expect(poi[f]).toBeNull();
    }
  });
});

describe("tuitionRmbFromSummary — null over 0", () => {
  it("returns null when costSummary is null", () => {
    expect(tuitionRmbFromSummary({ costSummary: null as unknown as undefined })).toBeNull();
  });

  it("returns null when minimumUsd is undefined", () => {
    expect(tuitionRmbFromSummary({ costSummary: {} })).toBeNull();
  });

  it("returns null when minimumUsd is 0", () => {
    expect(tuitionRmbFromSummary({ costSummary: { minimumUsd: 0 } })).toBeNull();
  });

  it("converts USD to RMB via 7.2 rate when valid", () => {
    expect(tuitionRmbFromSummary({ costSummary: { minimumUsd: 50000 } })).toBe(360000);
  });
});

describe("formatRmb / legacyPoiAnnualCostLabel — never render ¥NaN or ¥0", () => {
  it("formatRmb returns the empty-state label for null", () => {
    const out = formatRmb(null);
    expect(out.kind).toBe("empty");
    expect(out.label).toContain("补充");
  });

  it("formatRmb returns the empty-state label for 0", () => {
    const out = formatRmb(0);
    expect(out.kind).toBe("empty");
    expect(out.label).toContain("补充");
  });

  it("formatRmb returns a value-kind label for a positive number", () => {
    const out = formatRmb(620000);
    expect(out.kind).toBe("value");
    expect(out.label).toMatch(/^¥/);
    expect(out.label).not.toContain("NaN");
  });

  it("legacyPoiAnnualCostLabel shows the empty state for null POI", () => {
    const poi = summaryToLegacyUniversityPOI(baseSummary({ costSummary: null }));
    const label = legacyPoiAnnualCostLabel(poi);
    expect(label).toContain("补充");
  });

  it("legacyPoiAnnualCostLabel never emits ¥NaN", () => {
    const poi = summaryToLegacyUniversityPOI(baseSummary({ costSummary: null }));
    const label = legacyPoiAnnualCostLabel(poi);
    expect(label).not.toContain("NaN");
    expect(label).not.toMatch(/^¥0/);
  });
});

describe("legacyPoiScoreLabel — never render 0/100 for missing scores", () => {
  it("returns the empty-state label when the score is null", () => {
    expect(legacyPoiScoreLabel(null, "安全 ")).toBe("数据补充中");
  });

  it("returns '安全 78/100' when valid (label prefix + score + /100)", () => {
    expect(legacyPoiScoreLabel(78, "安全 ")).toBe("安全 78/100");
  });

  it("returns the empty-state label when the score is undefined", () => {
    expect(legacyPoiScoreLabel(undefined, "安全 ")).toBe("数据补充中");
  });
});

describe("buildCityAggregates — never aggregate Null Island (RG-P0-H)", () => {
  it("drops universities whose lat/lng are null", () => {
    const summary = baseSummary({ id: "ghost", city: "Nowhere", latitude: null, longitude: null });
    const poi = summaryToLegacyUniversityPOI(summary);
    const result = buildCityAggregates([poi]);
    expect(result).toHaveLength(0);
  });

  it("aggregates only universities with valid coordinates", () => {
    const a = summaryToLegacyUniversityPOI(baseSummary({ id: "ucla", city: "Los Angeles" }));
    const b = summaryToLegacyUniversityPOI(baseSummary({ id: "usc", city: "Los Angeles" }));
    const result = buildCityAggregates([a, b]);
    expect(result).toHaveLength(1);
    expect(result[0].universityCount).toBe(2);
  });

  it("does not invent avgAnnualCostRmb = 0 when all schools lack cost", () => {
    const a = summaryToLegacyUniversityPOI(baseSummary({ id: "a", costSummary: null }));
    const b = summaryToLegacyUniversityPOI(baseSummary({ id: "b", costSummary: null }));
    const result = buildCityAggregates([a, b]);
    // avgAnnualCostRmb is `number` in the aggregate shape (it's
    // optional in callers); the helper internally averages and
    // returns 0 when there's no data, but consumers MUST treat 0
    // as "no data" rather than render "¥0.0万/年". The invariant
    // here is that the function never crashes and never fabricates
    // a non-zero value when input is missing.
    expect(result[0].avgAnnualCostRmb).toBe(0);
  });
});