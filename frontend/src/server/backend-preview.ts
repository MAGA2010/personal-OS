// PathOS BFF — backend (Postgres) mode.
//
// Every artifact (manifest, universities, university details, region
// envelope, status dictionary, source index) is now a Postgres row
// instead of a JSON file. The legacy filesystem reader has been
// removed; this route handler is the single point of truth for the
// preview API.

import { NextResponse } from "next/server";

import {
  normalizeStage5Detail,
  normalizeStage5StatusDictionary,
  normalizeStage5Summary,
  parseStage5Detail,
  parseStage5Manifest,
  parseStage5RegionEnvelope,
  parseStage5SourceIndex,
  parseStage5Summaries,
} from "@/schemas/stage5-preview.schema";

import { DatabaseNotConfiguredError, getPool } from "@/server/db";

export class PreviewBundleError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
    public readonly retryable: boolean,
    public readonly featureStatus = "unavailable",
  ) {
    super(message);
  }
}

function respond(body: unknown, status = 200): NextResponse {
  return NextResponse.json(body, {
    status,
    headers: {
      "Cache-Control": "no-store",
      "X-PathOS-BFF": "preview-bundle",
      "X-PathOS-Data-Mode": "backend",
    },
  });
}

function decodeUniversityId(raw: string): string {
  try { return decodeURIComponent(raw); }
  catch {
    throw new PreviewBundleError(
      "INVALID_UNIVERSITY_ID",
      "University ID contains invalid percent encoding",
      400, false,
    );
  }
}

export function previewErrorResponse(
  error: unknown,
  endpoint: string,
): NextResponse {
  const known =
    error instanceof PreviewBundleError
      ? error
      : error instanceof DatabaseNotConfiguredError
        ? error
        : new PreviewBundleError(
            "BUNDLE_SCHEMA_INVALID",
            error instanceof Error ? error.message : "Preview bundle validation failed",
            503, false,
          );
  return respond(
    {
      error: "preview_backend_error",
      code: known.code,
      message: known.message,
      featureStatus: known.featureStatus,
      retryable: known.retryable,
      requestContext: { endpoint },
    },
    known.status,
  );
}

// ---- DB-backed artifact readers ---------------------------------------

async function readManifest(): Promise<unknown> {
  const r = await getPool().query("SELECT payload FROM manifest WHERE id = 1");
  if (!r.rows[0]) {
    throw new PreviewBundleError(
      "BUNDLE_ARTIFACT_MISSING",
      "manifest row not loaded. Run npm run db:import.",
      503, false,
    );
  }
  return r.rows[0].payload;
}

async function readRegionEnvelope(): Promise<unknown> {
  const r = await getPool().query("SELECT payload FROM region_envelope WHERE id = 1");
  if (!r.rows[0]) {
    throw new PreviewBundleError(
      "BUNDLE_ARTIFACT_MISSING",
      "region_envelope row not loaded. Run npm run db:import.",
      503, false,
    );
  }
  return r.rows[0].payload;
}

async function readStatusDictionary(): Promise<unknown> {
  const r = await getPool().query("SELECT code, payload FROM status_dictionary");
  return { statuses: Object.fromEntries(r.rows.map((row) => [row.code, row.payload])) };
}

async function readSourceIndex(): Promise<unknown> {
  const r = await getPool().query("SELECT payload FROM source_index WHERE id = 1");
  if (!r.rows[0]) {
    throw new PreviewBundleError(
      "BUNDLE_ARTIFACT_MISSING",
      "source_index row not loaded. Run npm run db:import.",
      503, false,
    );
  }
  return r.rows[0].payload;
}

async function readUniversityDetail(id: string): Promise<unknown> {
  const r = await getPool().query(
    "SELECT payload FROM university_details WHERE university_id = $1",
    [id],
  );
  if (!r.rows[0]) {
    throw new PreviewBundleError(
      "UNIVERSITY_NOT_FOUND",
      `University not found: ${id}`,
      404, false,
    );
  }
  return r.rows[0].payload;
}

// ---- Query builders ---------------------------------------------------

interface SummaryFilters {
  states: string[];
  tiers: string[];
  search: string;
  maxCostRmb: number;
}

function buildUniversitiesWhere(filters: SummaryFilters): { sql: string; params: unknown[] } {
  const where: string[] = [];
  const params: unknown[] = [];
  if (filters.states.length) {
    params.push(filters.states);
    where.push(`state = ANY($${params.length}::text[])`);
  }
  if (filters.tiers.length) {
    params.push(filters.tiers);
    where.push(`ranking_tier = ANY($${params.length}::text[])`);
  }
  if (filters.search) {
    params.push(filters.search);
    where.push(`search_text @@ plainto_tsquery('simple', $${params.length})`);
  }
  if (Number.isFinite(filters.maxCostRmb) && filters.maxCostRmb > 0) {
    params.push(filters.maxCostRmb);
    where.push(`(payload->'costSummary'->>'minimumUsd') IS NOT NULL`);
    where.push(
      `((payload->'costSummary'->>'minimumUsd')::numeric * 7.2) <= $${params.length}`,
    );
  }
  return {
    sql: where.length ? `WHERE ${where.join(" AND ")}` : "",
    params,
  };
}

function parseFiltersFromUrl(url: URL): SummaryFilters {
  return {
    states: url.searchParams.getAll("state"),
    tiers: url.searchParams.getAll("tier"),
    search: (url.searchParams.get("search") ?? "").trim(),
    maxCostRmb: Number(url.searchParams.get("maxCostRmb")),
  };
}

async function queryUniversities(filters: SummaryFilters): Promise<unknown[]> {
  const { sql, params } = buildUniversitiesWhere(filters);
  const r = await getPool().query(
    `SELECT payload FROM universities ${sql} ORDER BY name`,
    params,
  );
  return r.rows.map((row) => row.payload);
}

// ---- Main handler -----------------------------------------------------

export async function handleBackendPreviewRoute(
  req: Request,
  _env: NodeJS.ProcessEnv,
): Promise<NextResponse> {
  const url = new URL(req.url);
  const endpoint = (url.searchParams.get("endpoint") ?? "").trim();
  if (!endpoint) {
    return previewErrorResponse(
      new PreviewBundleError("MISSING_ENDPOINT", "endpoint is required", 400, false),
      endpoint,
    );
  }
  try {
    if (endpoint === "manifest") {
      const manifest = parseStage5Manifest(await readManifest());
      const dictionary = normalizeStage5StatusDictionary(await readStatusDictionary());
      return respond({ ...manifest, statusDictionary: dictionary });
    }

    if (endpoint === "universities") {
      const filters = parseFiltersFromUrl(url);
      const rows = await queryUniversities(filters);
      const summaries = parseStage5Summaries(rows);
      return respond(summaries.map((s) => normalizeStage5Summary(s)));
    }

    if (endpoint === "university") {
      const id = decodeUniversityId((url.searchParams.get("id") ?? "").trim());
      if (!id) {
        throw new PreviewBundleError(
          "MISSING_UNIVERSITY_ID",
          "University ID is required",
          400, false,
        );
      }
      const raw = parseStage5Detail(await readUniversityDetail(id));
      if (raw.id !== id) {
        throw new PreviewBundleError(
          "SUMMARY_DETAIL_ID_MISMATCH",
          "Detail ID does not match request",
          503, false,
        );
      }
      const sourceIndex = parseStage5SourceIndex(await readSourceIndex());
      return respond(normalizeStage5Detail(raw, sourceIndex));
    }

    if (endpoint === "region-metrics") {
      const region = parseStage5RegionEnvelope(await readRegionEnvelope());
      return respond(region);
    }

    if (endpoint === "status-dictionary") {
      return respond(normalizeStage5StatusDictionary(await readStatusDictionary()));
    }

    if (endpoint === "source-index") {
      return respond(parseStage5SourceIndex(await readSourceIndex()));
    }

    if (endpoint === "search") {
      const query = (url.searchParams.get("q") ?? "").trim();
      const limit = Math.max(0, Math.min(50, Number(url.searchParams.get("limit") ?? 20)));
      if (query.length < 2) return respond([]);
      const r = await getPool().query(
        `SELECT payload,
                ts_rank(search_text, plainto_tsquery('simple', $1)) AS rank
         FROM universities
         WHERE search_text @@ plainto_tsquery('simple', $1)
         ORDER BY rank DESC
         LIMIT $2`,
        [query, limit],
      );
      const rows = r.rows.map((row) => ({
        university: normalizeStage5Summary(row.payload),
        matchedField: "name" as const,
      }));
      return respond(rows);
    }

    if (endpoint === "news") return respond([]);

    if (endpoint === "region-detail") {
      throw new PreviewBundleError(
        "REGION_METRICS_BLOCKED",
        "Region metrics are blocked for this Preview checkpoint",
        404, false,
        "blocked",
      );
    }

    throw new PreviewBundleError(
      "UNKNOWN_ENDPOINT",
      `Unknown Preview endpoint: ${endpoint}`,
      404, false,
    );
  } catch (error) {
    return previewErrorResponse(error, endpoint);
  }
}
