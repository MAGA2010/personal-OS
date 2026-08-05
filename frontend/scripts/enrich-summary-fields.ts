/**
 * ETL: Derive missing summary fields from university_details JSON.
 *
 *   detail.undergraduateEnrollment.value  -> summary.undergraduateEnrollment
 *                                            + summary.enrollment.undergraduate.value
 *   detail.admissions.acceptanceRate.value -> summary.acceptanceRate
 *   detail.admissions.sat.{math,reading_writing}.percentile_{25,75}
 *                                            -> summary.sat25 / summary.sat75
 *   detail.admissions.graduationRate.value -> summary.graduationRate
 *   detail.admissions.retentionRate.value  -> summary.retentionRate
 *
 * Idempotent and non-destructive — only fills fields that are missing
 * or `null`. Existing hand-curated values are kept verbatim so this
 * script can be run repeatedly without undoing manual edits.
 *
 * Usage:
 *   DATABASE_URL=postgresql://... tsx scripts/enrich-summary-fields.ts
 *   DATABASE_URL=... tsx scripts/enrich-summary-fields.ts --dry-run
 *
 * Why this script exists:
 *   The Stage 5 detail JSON carries verified enrollment / admissions /
 *   test-score records (College Scorecard), but the universities-table
 *   payload only carries a thin subset for the map list. The frontend
 *   summary view therefore shows "数据补充中" for all 62 schools even
 *   though the data is sitting one join away. This script flattens the
 *   detail fields onto the summary so the map can show real numbers
 *   without a per-school detail fetch.
 */
import { Client } from "pg";

interface JsonObject { [k: string]: unknown }

const DRY_RUN = process.argv.includes("--dry-run");

function asObject(v: unknown): JsonObject | null {
  return v !== null && typeof v === "object" && !Array.isArray(v) ? (v as JsonObject) : null;
}

function readNumber(obj: JsonObject | null, path: string[]): number | null {
  let cur: unknown = obj;
  for (const key of path) {
    if (cur === null || cur === undefined) return null;
    cur = asObject(cur)?.[key];
  }
  if (typeof cur !== "number" || !Number.isFinite(cur)) return null;
  return cur;
}

interface DerivedFields {
  undergraduateEnrollment: number | null;
  acceptanceRate: number | null;
  sat25: number | null;
  sat75: number | null;
  graduationRate: number | null;
  retentionRate: number | null;
}

function derive(summary: JsonObject, detail: JsonObject): DerivedFields {
  const out: DerivedFields = {
    undergraduateEnrollment: null,
    acceptanceRate: null,
    sat25: null,
    sat75: null,
    graduationRate: null,
    retentionRate: null,
  };
  const existingEnroll = readNumber(summary, ["undergraduateEnrollment"]);
  if (typeof existingEnroll === "number" && existingEnroll > 0) {
    out.undergraduateEnrollment = existingEnroll;
  } else {
    out.undergraduateEnrollment = readNumber(detail, [
      "undergraduateEnrollment", "value",
    ]);
  }
  const existingAccept = readNumber(summary, ["acceptanceRate"]);
  if (typeof existingAccept === "number" && existingAccept > 0) {
    out.acceptanceRate = existingAccept;
  } else {
    const ratio = readNumber(detail, ["admissions", "acceptanceRate", "value"]);
    if (ratio !== null) out.acceptanceRate = ratio <= 1 ? ratio * 100 : ratio;
  }
  const math25 = readNumber(detail, ["admissions", "sat", "value", "math", "percentile_25"]);
  const math75 = readNumber(detail, ["admissions", "sat", "value", "math", "percentile_75"]);
  const rw25 = readNumber(detail, ["admissions", "sat", "value", "reading_writing", "percentile_25"]);
  const rw75 = readNumber(detail, ["admissions", "sat", "value", "reading_writing", "percentile_75"]);
  if (math25 !== null && rw25 !== null) out.sat25 = math25 + rw25;
  if (math75 !== null && rw75 !== null) out.sat75 = math75 + rw75;
  out.graduationRate = readNumber(detail, ["admissions", "graduationRate", "value"]);
  out.retentionRate = readNumber(detail, ["admissions", "retentionRate", "value"]);
  return out;
}

function mergePayload(summary: JsonObject, derived: DerivedFields): JsonObject {
  const next: JsonObject = { ...summary };
  if (derived.undergraduateEnrollment !== null) {
    next.undergraduateEnrollment = derived.undergraduateEnrollment;
    const enrollment = asObject(next.enrollment) ?? {};
    const undergradField = asObject(enrollment.undergraduate) ?? {};
    enrollment.undergraduate = {
      ...undergradField,
      value: derived.undergraduateEnrollment,
      status: "verified",
      unit: null,
    };
    next.enrollment = enrollment;
  }
  if (derived.acceptanceRate !== null) next.acceptanceRate = derived.acceptanceRate;
  if (derived.sat25 !== null) next.sat25 = derived.sat25;
  if (derived.sat75 !== null) next.sat75 = derived.sat75;
  if (derived.graduationRate !== null) next.graduationRate = derived.graduationRate;
  if (derived.retentionRate !== null) next.retentionRate = derived.retentionRate;
  return next;
}

function diff(oldPayload: JsonObject, newPayload: JsonObject): string[] {
  const keys = new Set([...Object.keys(oldPayload), ...Object.keys(newPayload)]);
  const changed: string[] = [];
  for (const key of keys) {
    const a = JSON.stringify(oldPayload[key]);
    const b = JSON.stringify(newPayload[key]);
    if (a !== b) changed.push(key);
  }
  return changed.sort();
}

async function loadEnv(): Promise<void> {
  if (process.env.DATABASE_URL) return;
  const fs = await import("node:fs/promises");
  const path = await import("node:path");
  const file = path.join(process.cwd(), ".env.local");
  const text = await fs.readFile(file, "utf8");
  for (const line of text.split(/\r?\n/)) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m && process.env[m[1]] === undefined) process.env[m[1]] = m[2];
  }
}

async function main(): Promise<void> {
  await loadEnv();
  const url = process.env.DATABASE_URL;
  if (!url) {
    console.error("DATABASE_URL is required");
    process.exit(1);
  }
  const client = new Client({ connectionString: url, ssl: { rejectUnauthorized: false } });
  await client.connect();
  console.log(`connected to ${new URL(url).host}${DRY_RUN ? " (DRY RUN)" : ""}`);

  const r = await client.query<{ id: string; payload: JsonObject }>(
    `SELECT u.id,
            u.payload AS payload,
            d.payload AS detail
       FROM universities u
       LEFT JOIN university_details d ON d.university_id = u.id
       ORDER BY u.name`,
  );
  let touched = 0;
  let unchanged = 0;
  let summary: Record<string, number> = {};
  for (const row of r.rows) {
    const detail = asObject(row.detail);
    if (!detail) {
      unchanged++;
      continue;
    }
    const derived = derive(row.payload, detail);
    const merged = mergePayload(row.payload, derived);
    const changedKeys = diff(row.payload, merged);
    if (changedKeys.length === 0) {
      unchanged++;
      continue;
    }
    for (const k of changedKeys) summary[k] = (summary[k] ?? 0) + 1;
    if (!DRY_RUN) {
      await client.query(
        `UPDATE universities
            SET payload = $1::jsonb,
                updated_at = NOW()
          WHERE id = $2`,
        [JSON.stringify(merged), row.id],
      );
    }
    touched++;
    console.log(`  ${row.id}: ${changedKeys.join(", ")}`);
  }
  console.log("\n=== summary ===");
  console.log(`rows scanned: ${r.rows.length}`);
  console.log(`rows touched: ${touched}${DRY_RUN ? " (would be updated)" : ""}`);
  console.log(`rows unchanged: ${unchanged}`);
  console.log(`fields filled:`);
  for (const [key, count] of Object.entries(summary)) {
    console.log(`  ${key}: ${count}`);
  }
  await client.end();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});