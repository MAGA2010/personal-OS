// Shared core for db:enrich: flattens detail.{undergraduateEnrollment,
// admissions.{acceptanceRate, sat.*.{math,reading_writing}.percentile_{25,75},
// graduationRate, retentionRate}} onto summary. Idempotent: only fills fields
// that are missing or 0.

export type JsonObject = Record<string, unknown>;

function asObject(v: unknown): JsonObject | null {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as JsonObject) : null;
}

function readNum(obj: JsonObject | null, path: string[]): number | null {
  let cur: unknown = obj;
  for (const k of path) cur = asObject(cur)?.[k];
  return typeof cur === "number" && Number.isFinite(cur) ? cur : null;
}

type SummaryField = "undergraduateEnrollment" | "acceptanceRate" | "sat25" | "sat75" | "graduationRate" | "retentionRate";
type Derived = Record<SummaryField, number | null>;

function pickFlat(summary: JsonObject, detail: JsonObject, key: SummaryField, detailPath: string[], asPercent = false): number | null {
  const raw = readNum(summary, [key]) ?? readNum(detail, detailPath);
  if (raw === null || raw <= 0) return null;
  return asPercent && raw <= 1 ? raw * 100 : raw;
}

function pickSat(detail: JsonObject, which: 25 | 75): number | null {
  const k = which === 25 ? "percentile_25" : "percentile_75";
  const m = readNum(detail, ["admissions", "sat", "value", "math", k]);
  const r = readNum(detail, ["admissions", "sat", "value", "reading_writing", k]);
  return m !== null && r !== null ? m + r : null;
}

export function derive(summary: JsonObject, detail: JsonObject): Derived {
  return {
    undergraduateEnrollment: pickFlat(summary, detail, "undergraduateEnrollment", ["undergraduateEnrollment", "value"]),
    acceptanceRate: pickFlat(summary, detail, "acceptanceRate", ["admissions", "acceptanceRate", "value"], true),
    sat25: pickSat(detail, 25),
    sat75: pickSat(detail, 75),
    graduationRate: pickFlat(summary, detail, "graduationRate", ["admissions", "graduationRate", "value"]),
    retentionRate: pickFlat(summary, detail, "retentionRate", ["admissions", "retentionRate", "value"]),
  };
}

const SIMPLE_KEYS: SummaryField[] = ["acceptanceRate", "sat25", "sat75", "graduationRate", "retentionRate"];

export function merge(summary: JsonObject, d: Derived): JsonObject {
  const out: JsonObject = { ...summary };
  if (d.undergraduateEnrollment !== null) {
    out.undergraduateEnrollment = d.undergraduateEnrollment;
    const enr = asObject(out.enrollment) ?? {};
    enr.undergraduate = { ...asObject(enr.undergraduate), value: d.undergraduateEnrollment, status: "verified", unit: null };
    out.enrollment = enr;
  }
  for (const k of SIMPLE_KEYS) if (d[k] !== null) out[k] = d[k];
  return out;
}

function diffKeys(oldP: JsonObject, newP: JsonObject): string[] {
  const out: string[] = [];
  for (const k of Object.keys(newP)) if (JSON.stringify(oldP[k]) !== JSON.stringify(newP[k])) out.push(k);
  for (const k of Object.keys(oldP)) if (!(k in newP)) out.push(k);
  return out;
}

export interface EnrichReport {
  rowsScanned: number;
  rowsTouched: number;
  fieldsFilled: Record<string, number>;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function enrichSummaries(
  client: { query: (...args: any[]) => Promise<{ rows: any[] }> },
  opts: { dryRun: boolean },
): Promise<EnrichReport> {
  const r = await (client.query as any)(
    `SELECT u.id, u.payload AS payload, d.payload AS detail
       FROM universities u
       LEFT JOIN university_details d ON d.university_id = u.id
       ORDER BY u.name`,
  );
  let touched = 0;
  const fieldsFilled: Record<string, number> = {};
  for (const row of r.rows as Array<{ id: string; payload: JsonObject; detail: JsonObject | null }>) {
    if (!row.detail) continue;
    const merged = merge(row.payload, derive(row.payload, row.detail));
    const keys = diffKeys(row.payload, merged);
    if (keys.length === 0) continue;
    for (const k of keys) fieldsFilled[k] = (fieldsFilled[k] ?? 0) + 1;
    if (!opts.dryRun) {
      await (client.query as any)(
        `UPDATE universities SET payload = $1::jsonb, updated_at = NOW() WHERE id = $2`,
        [JSON.stringify(merged), row.id],
      );
    }
    touched++;
  }
  return { rowsScanned: r.rows.length, rowsTouched: touched, fieldsFilled };
}

import { Client } from "pg";

export async function withClient<T>(connStr: string, fn: (c: Client) => Promise<T>): Promise<T> {
  const c = new Client({
    connectionString: connStr,
    ssl: connStr.includes("supabase") || connStr.includes("sslmode=require") ? { rejectUnauthorized: false } : undefined,
  });
  await c.connect();
  try { return await fn(c); } finally { await c.end(); }
}

