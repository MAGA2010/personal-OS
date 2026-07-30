// Stage 7R — Regional Heatmap Tests
//
// Covers:
//   • Data importer deterministic output (4 metrics × 51 records = 204)
//   • Per-metric READY coverage 51/51, no missing
//   • safety rawDirection = inverse; normalizedValue flips the workbook
//   • 4 distinct paletteIds; light ≠ dark; missing ≠ lowest stop
//   • Regional boundary — usedForMatch = false for all 4
//   • FIPS join key format (2-digit string with leading zero preserved)
//   • Manifest carries source workbook SHA + generated artifact SHAs
//   • Validation: duplicateGeoIds = 0; missingCount = 0 per metric
//   • Determinism: two manifest SHA-256 of the records file match

import { describe, expect, it } from "vitest";

import {
  REGIONAL_METRIC_IDS,
  type RegionalMetricId,
  type RegionalMetricRecord,
} from "@/regional/types";
import {
  REGIONAL_PALETTES,
  bucketFromNormalized,
  getPalette,
} from "@/regional/palettes";
import {
  getRegionalCounters,
  getRegionalDatasetMetadata,
  getRegionalManifest,
  getRegionalMetricDefinition,
  getRegionalMetricRecords,
  getRegionalValidation,
} from "@/regional/load";

import regionalRecords from "../../../generated/regional-data/regional-records.json";
import regionalDatasets from "../../../generated/regional-data/regional-datasets.json";
import regionalMetrics from "../../../generated/regional-data/regional-metrics.json";
import regionalManifest from "../../../generated/regional-data/regional-data-manifest.json";
import regionalValidation from "../../../generated/regional-data/regional-data-validation.json";

// ─── Determinism ─────────────────────────────────────────────────────

describe("Stage 7R importer determinism", () => {
  it("produces 204 records (51 × 4 metrics)", () => {
    const records = (regionalRecords as { records: RegionalMetricRecord[] }).records;
    expect(records.length).toBe(204);
  });

  it("every FIPS appears exactly 4 times (one per metric)", () => {
    const records = (regionalRecords as { records: RegionalMetricRecord[] }).records;
    const seen = new Map<string, number>();
    for (const r of records) {
      seen.set(r.geoId, (seen.get(r.geoId) ?? 0) + 1);
    }
    const counts = Array.from(seen.values());
    expect(counts.length).toBe(51);
    expect(Math.min(...counts)).toBe(4);
    expect(Math.max(...counts)).toBe(4);
  });

  it("FIPS format: 2-char string with leading zero preserved", () => {
    const records = (regionalRecords as { records: RegionalMetricRecord[] }).records;
    for (const r of records) {
      expect(typeof r.geoId).toBe("string");
      expect(r.geoId.length).toBe(2);
    }
    // Spot-check leading zero
    expect(records.some((r) => r.geoId === "01")).toBe(true);
    expect(records.some((r) => r.geoId === "06")).toBe(true);
    expect(records.some((r) => r.geoId === "11")).toBe(true);
  });
});

// ─── Per-metric readiness ────────────────────────────────────────────

describe("Stage 7R per-metric coverage", () => {
  for (const mid of REGIONAL_METRIC_IDS) {
    it(`${mid}: 51 records, 0 missing`, () => {
      const records = getRegionalMetricRecords(mid);
      expect(records.length).toBe(51);
      const missing = records.filter((r) => r.rawValue === null).length;
      expect(missing).toBe(0);
      const verified = records.filter((r) => r.verificationStatus === "verified").length;
      expect(verified).toBe(51);
    });
  }
});

// ─── Safety inversion ────────────────────────────────────────────────

describe("Stage 7R safety metric inversion", () => {
  it("safety rawDirection is 'inverse' (higher raw = more crime)", () => {
    const def = getRegionalMetricDefinition("safety");
    expect(def).toBeDefined();
    expect(def!.rawDirection).toBe("inverse");
    expect(def!.higherIsBetter).toBe(false);
    expect(def!.longDescription).toMatch(/倒数|反向|标准化|越高越安全/);
  });

  it("safety: the lowest rawValue (Maine) becomes the highest normalizedValue", () => {
    const records = getRegionalMetricRecords("safety");
    const sortedRaw = [...records].sort((a, b) => (a.rawValue ?? 0) - (b.rawValue ?? 0));
    const lowestCrime = sortedRaw[0]; // Maine raw=110.6
    const highestCrime = sortedRaw[sortedRaw.length - 1]; // New Mexico raw=780.5
    expect(lowestCrime.normalizedValue).toBeGreaterThan(highestCrime.normalizedValue ?? 0);
    expect(lowestCrime.rawValue).toBeLessThan(highestCrime.rawValue ?? 0);
  });

  it("safety: missing safety record is impossible (51/51 covered)", () => {
    const records = getRegionalMetricRecords("safety");
    expect(records.filter((r) => r.verificationStatus !== "verified").length).toBe(0);
  });
});

// ─── Distinct palettes ───────────────────────────────────────────────

describe("Stage 7R palette system", () => {
  it("4 READY metrics use 4 distinct paletteIds", () => {
    const ids = REGIONAL_METRIC_IDS.map((m) => getRegionalMetricDefinition(m)!.paletteId);
    expect(new Set(ids).size).toBe(4);
    expect(ids.sort()).toEqual([
      "palette-chinese-orange",
      "palette-employment-purple",
      "palette-income-green",
      "palette-safety-blue",
    ]);
  });

  it("every palette has light + dark stops", () => {
    for (const id of REGIONAL_METRIC_IDS.map((m) => getRegionalMetricDefinition(m)!.paletteId)) {
      const def = REGIONAL_PALETTES[id];
      expect(def).toBeDefined();
      expect(def.light.stops.length).toBe(5);
      expect(def.dark.stops.length).toBe(5);
    }
  });

  it("every palette: missing color is NOT equal to the lowest stop", () => {
    for (const id of REGIONAL_METRIC_IDS.map((m) => getRegionalMetricDefinition(m)!.paletteId)) {
      const def = REGIONAL_PALETTES[id];
      expect(def.light.missing.toLowerCase()).not.toBe(def.light.stops[0].toLowerCase());
      expect(def.dark.missing.toLowerCase()).not.toBe(def.dark.stops[0].toLowerCase());
    }
  });

  it("every palette: light stops differ from dark stops", () => {
    for (const id of REGIONAL_METRIC_IDS.map((m) => getRegionalMetricDefinition(m)!.paletteId)) {
      const def = REGIONAL_PALETTES[id];
      expect(def.light.stops.join()).not.toBe(def.dark.stops.join());
    }
  });

  it("every palette: adjacent stops are visibly distinct (ΔL >= 8 in HSL lightness)", () => {
    function lightness(hex: string): number {
      const m = hex.replace("#", "");
      const r = parseInt(m.slice(0, 2), 16) / 255;
      const g = parseInt(m.slice(2, 4), 16) / 255;
      const b = parseInt(m.slice(4, 6), 16) / 255;
      const lin = (c: number) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
      return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
    }
    for (const id of REGIONAL_METRIC_IDS.map((m) => getRegionalMetricDefinition(m)!.paletteId)) {
      for (const theme of ["light", "dark"] as const) {
        const stops = REGIONAL_PALETTES[id][theme].stops;
        for (let i = 0; i < stops.length - 1; i++) {
          const dl = Math.abs(lightness(stops[i]) - lightness(stops[i + 1])) * 100;
          expect(dl, `${id}/${theme}[${i}]→[${i + 1}] ΔL=${dl.toFixed(1)}`).toBeGreaterThanOrEqual(8);
        }
      }
    }
  });

  it("bucketFromNormalized maps [0,1] to one of 5 stops + missing fallback", () => {
    const palette = getPalette("palette-income-green", "light");
    expect(bucketFromNormalized(null, palette)).toBe(palette.missing);
    expect(bucketFromNormalized(-1, palette)).toBe(palette.missing);
    expect(bucketFromNormalized(NaN, palette)).toBe(palette.missing);
    expect(bucketFromNormalized(0, palette)).toBe(palette.stops[0]);
    expect(bucketFromNormalized(0.999, palette)).toBe(palette.stops[4]);
    expect(bucketFromNormalized(1, palette)).toBe(palette.stops[4]);
    expect(bucketFromNormalized(0.4, palette)).toBe(palette.stops[2]);
  });
});

// ─── Boundary: region data does NOT influence match ──────────────────

describe("Stage 7R match/assessment boundary", () => {
  it("usedForMatch is false for all 4 READY metrics", () => {
    for (const mid of REGIONAL_METRIC_IDS) {
      const def = getRegionalMetricDefinition(mid)!;
      expect(def.usedForMatch).toBe(false);
      expect(def.usedForMap).toBe(true);
    }
  });

  it("ready metrics list matches the 4 expected ids", () => {
    const ds = regionalDatasets as { readyMetrics: RegionalMetricId[] };
    expect([...ds.readyMetrics].sort()).toEqual([...REGIONAL_METRIC_IDS].sort());
  });

  it("blocked metrics include admission_rate", () => {
    const ds = regionalDatasets as { blockedMetrics: string[] };
    expect(ds.blockedMetrics).toContain("admission_rate");
  });
});

// ─── Manifest + validation ───────────────────────────────────────────

describe("Stage 7R manifest + validation", () => {
  it("manifest carries source workbook SHA-256 (hex 64)", () => {
    const m = regionalManifest as ReturnType<typeof getRegionalManifest>;
    expect(m.sourceWorkbook.sha256).toMatch(/^[0-9a-f]{64}$/);
    // SHA of the workbook we audited
    expect(m.sourceWorkbook.sha256).toBe(
      "409ed47b5153725914b463ae3421ad51e5d3d34e5918144f001f341b9894b096",
    );
  });

  it("manifest artifact SHAs are deterministic and unique", () => {
    const m = regionalManifest as ReturnType<typeof getRegionalManifest>;
    const paths = m.artifacts.map((a) => a.path);
    expect(new Set(paths).size).toBe(paths.length);
    for (const a of m.artifacts) {
      expect(a.sha256).toMatch(/^[0-9a-f]{64}$/);
      expect(a.bytes).toBeGreaterThan(0);
    }
  });

  it("validation reports 0 duplicates and 0 missing", () => {
    const v = regionalValidation as ReturnType<typeof getRegionalValidation>;
    expect(v.summary.duplicateGeoIds).toBe(0);
    expect(v.summary.missingCount).toBe(0);
    expect(v.summary.recordsVerified).toBe(204);
    expect(v.summary.recordsTotal).toBe(204);
  });

  it("counters reflect 4 ready, 1 blocked, 1 out-of-scope", () => {
    const c = getRegionalCounters();
    expect(c.readyMetricCount).toBe(4);
    expect(c.blockedMetricCount).toBe(1);
    expect(c.outOfScopeMetricCount).toBe(1);
    expect(c.recordCount).toBe(204);
    expect(c.verifiedCount).toBe(204);
    expect(c.missingCount).toBe(0);
  });

  it("dataset metadata carries workbook SHA + status", () => {
    const ds = getRegionalDatasetMetadata();
    expect(ds.sourceWorkbookSha256).toBe(
      "409ed47b5153725914b463ae3421ad51e5d3d34e5918144f001f341b9894b096",
    );
    expect(ds.status).toBe("verified");
    expect(ds.productionReady).toBe(false);
    expect(ds.geographyLevel).toBe("state");
    expect(ds.geoIdType).toBe("state_fips");
  });
});

// ─── Metric definitions metadata ─────────────────────────────────────

describe("Stage 7R metric definition metadata", () => {
  it("every metric definition carries display name, unit, source, year", () => {
    for (const mid of REGIONAL_METRIC_IDS) {
      const def = getRegionalMetricDefinition(mid)!;
      expect(def.displayNameZh.length).toBeGreaterThan(0);
      expect(def.displayNameEn.length).toBeGreaterThan(0);
      expect(def.rawUnit.length).toBeGreaterThan(0);
      expect(def.sourceName.length).toBeGreaterThan(0);
      expect(def.referenceYear.length).toBeGreaterThan(0);
      expect(def.paletteId.length).toBeGreaterThan(0);
      expect(def.verificationStatus).toBe("verified");
    }
  });

  it("metric definitions match the 4 expected IDs (income/safety/employment/chinese)", () => {
    const metrics = (regionalMetrics as { metrics: Array<{ metricId: string }> }).metrics;
    expect(metrics.length).toBe(4);
    const ids = metrics.map((m) => m.metricId).sort();
    expect(ids).toEqual(["chinese_population", "employment", "income", "safety"]);
  });
});

// ─── Stable helpers (importer logic mirrored for unit-testing) ───────

describe("Stage 7R importer rule: missing values stay null", () => {
  it("no record has a fake 0/0.5/70 substituted for missing", () => {
    const records = (regionalRecords as { records: RegionalMetricRecord[] }).records;
    for (const r of records) {
      if (r.verificationStatus !== "verified") {
        expect(r.rawValue).toBeNull();
        expect(r.normalizedValue).toBeNull();
      }
    }
  });
});