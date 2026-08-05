// POST /api/admin/enrich-summaries — triggers db:enrich logic via HTTP so the
// user does not need Render Shell. Guarded by PATHOS_ADMIN_TOKEN. See
// src/server/enrich-summary.ts for the actual work.

import { NextResponse } from "next/server";
import { Pool } from "pg";
import { enrichSummaries } from "@/server/enrich-summary";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

function deny(reason: string, code: string, status: number) {
  return NextResponse.json({ ok: false, code, message: reason }, { status });
}

export async function POST(req: Request): Promise<NextResponse> {
  const token = process.env.PATHOS_ADMIN_TOKEN;
  if (!token) return deny("PATHOS_ADMIN_TOKEN not configured", "ADMIN_TOKEN_NOT_SET", 503);
  if (req.headers.get("x-pathos-admin-token") !== token) return deny("invalid token", "UNAUTHORIZED", 401);
  const connStr = process.env.DATABASE_URL;
  if (!connStr) return deny("DATABASE_URL not set", "DATABASE_NOT_CONFIGURED", 503);

  const body = await req.json().catch(() => ({}));
  const dryRun = !!body && typeof body === "object" && (body as Record<string, unknown>).dryRun === true;

  const pool = new Pool({
    connectionString: connStr,
    ssl: connStr.includes("supabase") ? { rejectUnauthorized: false } : undefined,
    max: 2, idleTimeoutMillis: 10_000, connectionTimeoutMillis: 5_000,
  });
  try {
    const client = await pool.connect();
    try {
      return NextResponse.json({ ok: true, ...await enrichSummaries(client, { dryRun }), dryRun });
    } finally { client.release(); }
  } catch (e) {
    return deny(e instanceof Error ? e.message : String(e), "ENRICH_FAILED", 500);
  } finally { await pool.end(); }
}

export function GET() { return deny("POST with x-pathos-admin-token", "METHOD_NOT_ALLOWED", 405); }

