// PathOS — region metric set wrapper.
//
// Wraps a list of `RegionMetricRecord` so that callers (MapCanvas, MapShell,
// sidebar region pickers, etc.) can do O(1) lookups by FIPS code instead of
// re-filtering on every render. Records are normalised to a 2-character FIPS
// string so callers don't need to worry about "6" vs "06" mismatches.

import type { RegionMetricRecord } from "./dataset";

export class RegionMetricSet {
  private readonly byMetricAndFips: Map<string, Map<string, RegionMetricRecord>> = new Map();
  private readonly fipsIndex: Map<string, Set<string>> = new Map();

  constructor(records: readonly RegionMetricRecord[]) {
    for (const r of records) {
      const fips = normalizeFips(r.fipsCode);
      const metric = String(r.metricId);
      if (!this.byMetricAndFips.has(metric)) this.byMetricAndFips.set(metric, new Map());
      this.byMetricAndFips.get(metric)!.set(fips, { ...r, fipsCode: fips });
      if (!this.fipsIndex.has(fips)) this.fipsIndex.set(fips, new Set());
      this.fipsIndex.get(fips)!.add(metric);
    }
  }

  /** Returns the record for (metricId, fipsCode) or undefined. */
  getForFips(fipsCode: string, metricId: string): RegionMetricRecord | undefined {
    return this.byMetricAndFips.get(metricId)?.get(normalizeFips(fipsCode));
  }

  /** Returns all records for a FIPS code regardless of metric. */
  recordsForFips(fipsCode: string): RegionMetricRecord[] {
    const fips = normalizeFips(fipsCode);
    const metrics = this.fipsIndex.get(fips);
    if (!metrics) return [];
    const out: RegionMetricRecord[] = [];
    metrics.forEach((metric) => {
      const r = this.byMetricAndFips.get(metric)?.get(fips);
      if (r) out.push(r);
    });
    return out;
  }

  /** All FIPS codes present in this set. */
  fipsCodes(): string[] {
    return Array.from(this.fipsIndex.keys());
  }

  /** Returns the raw underlying records (normalised FIPS strings). */
  toArray(): RegionMetricRecord[] {
    const out: RegionMetricRecord[] = [];
    this.byMetricAndFips.forEach((byFips) => {
      byFips.forEach((r) => out.push(r));
    });
    return out;
  }

  get size(): number {
    return this.toArray().length;
  }
}

function normalizeFips(fips: string): string {
  const trimmed = String(fips ?? "").trim();
  if (!trimmed) return "";
  return trimmed.padStart(2, "0").slice(-5);
}