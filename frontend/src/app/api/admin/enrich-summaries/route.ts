// One-shot admin endpoint: enrich summary fields from university_details.
//
// Triggered manually when the user wants to re-run the enricher without
// paying for Render Shell. Guarded by PATHOS_ADMIN_TOKEN so a casual
// visitor cannot re-trigger it.
//
// POST /api/admin/enrich-summaries
// Headers:
//   x-pathos-admin-token: <PATHOS_ADMIN_TOKEN>
// Body (optional): { "dryRun": true }
// Response: { rowsScanned, rowsTouched, fieldsFilled, dryRun }
//
// The work it does is exactly what `npm run db:enrich` does locally:
// flatten detail.{undergraduateEnrollment, admissions.{acceptanceRate,
// sat.{math,reading_writing}.percentile_{25,75}, graduationRate,
// retentionRate}} onto summary so the BFF exposes real numbers instead
// of æ°æ®è¡¥åä¸­.

import { NextResponse } from "next/server";
import { Pool } from "pg";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

interface JsonObject { [k: string]: unknown }

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
    out.undergraduateEnrollment = readNumber(detail, ["undergraduateEnrollment", "value"]);
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

export async function POST(req: Request): Promise<NextResponse> {
  const expected = process.env.PATHOS_ADMIN_TOKEN;
  if (!expected) {
    return NextResponse.json(
      { ok: false, code: "ADMIN_TOKEN_NOT_SET", message: "PATHOS_ADMIN_TOKEN is not configured on the server." },
      { status: 503 },
    );
  }
  const provided = req.headers.get("x-pathos-admin-token") ?? "";
  if (provided !== expected) {
    return NextResponse.json(
      { ok: false, code: "UNAUTHORIZED", message: "Invalid or missing x-pathos-admin-token header." },
      { status: 401 },
    );
  }

  let dryRun = false;
  try {
    const body = await req.json().catch(() => ({}));
    if (body && typeof body === "object" && (body as Record<string, unknown>).dryRun === true) {
      dryRun = true;
    }
  } catch {
    // empty body is fine
  }

  const connStr = process.env.DATABASE_URL;
  if (!connStr) {
    return NextResponse.json(
      { ok: false, code: "DATABASE_NOT_CONFIGURED", message: "DATABASE_URL is not set." },
      { status: 503 },
    );
  }

  const client = new Pool({
    connectionString: connStr,
    ssl: connStr.includes("supabase") || connStr.includes("sslmode=require")
      ? { rejectUnauthorized: false }
      : undefined,
    max: 2,
    idleTimeoutMillis: 10_000,
    connectionTimeoutMillis: 5_000,
  });
  try {
    const r = await client.query<{ id: string; payload: JsonObject; detail: JsonObject | null }>(
      `SELECT u.id,
              u.payload AS payload,
              d.payload AS detail
         FROM universities u
         LEFT JOIN university_details d ON d.university_id = u.id
         ORDER BY u.name`,
    );
    let touched = 0;
    const fieldsFilled: Record<string, number> = {};
    for (const row of r.rows) {
      if (!row.detail) continue;
      const derived = derive(row.payload, row.detail);
      const merged = mergePayload(row.payload, derived);
      const changed: string[] = [];
      for (const key of Object.keys(merged)) {
        if (JSON.stringify(row.payload[key]) !== JSON.stringify(merged[key])) {
          changed.push(key);
        }
      }
      for (const key of Object.keys(row.payload)) {
        if (!(key in merged)) {
          changed.push(key);
        }
      }
      if (changed.length === 0) continue;
      for (const key of changed) {
        fieldsFilled[key] = (fieldsFilled[key] ?? 0) + 1;
      }
      if (!dryRun) {
        await client.query(
          `UPDATE universities
              SET payload = $1::jsonb,
                  updated_at = NOW()
            WHERE id = $2`,
          [JSON.stringify(merged), row.id],
        );
      }
      touched++;
    }
    return NextResponse.json({
      ok: true,
      dryRun,
      rowsScanned: r.rows.length,
      rowsTouched: touched,
      fieldsFilled,
    });
  } catch (error: unknown) {
    return NextResponse.json(
      {
        ok: false,
        code: "ENRICH_FAILED",
        message: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    );
  } finally {
    await client.end();
  }
}

export async function GET(): Promise<NextResponse> {
  return NextResponse.json(
    {
      ok: false,
      code: "METHOD_NOT_ALLOWED",
      message: "POST with x-pathos-admin-token header to trigger enrichment.",
    },
    { status: 405 },
  );
}
