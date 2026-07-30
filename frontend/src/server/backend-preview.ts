import { readFile } from "node:fs/promises";
import path from "node:path";
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
import type { Stage5Summary } from "@/schemas/stage5-preview.schema";

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

function bundleRoot(env: NodeJS.ProcessEnv): string {
  const configured = env.PATHOS_PREVIEW_BUNDLE_DIR?.trim();
  if (!configured) {
    throw new PreviewBundleError(
      "BACKEND_CONFIG_MISSING",
      "PATHOS_PREVIEW_BUNDLE_DIR is required in backend mode",
      503,
      false,
    );
  }
  return path.resolve(configured);
}

async function readArtifact(
  env: NodeJS.ProcessEnv,
  relativePath: string,
): Promise<unknown> {
  const root = bundleRoot(env);
  const resolved = path.resolve(root, relativePath);
  if (resolved !== root && !resolved.startsWith(`${root}${path.sep}`)) {
    throw new PreviewBundleError(
      "INVALID_ARTIFACT_PATH",
      "Preview artifact path escaped the configured bundle",
      400,
      false,
    );
  }
  let text: string;
  try {
    text = await readFile(resolved, "utf8");
  } catch {
    throw new PreviewBundleError(
      "BUNDLE_ARTIFACT_MISSING",
      `Required Preview artifact is missing: ${relativePath}`,
      503,
      false,
    );
  }
  if (!text.trim()) {
    throw new PreviewBundleError(
      "BUNDLE_EMPTY_BODY",
      `Preview artifact is empty: ${relativePath}`,
      503,
      false,
    );
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new PreviewBundleError(
      "BUNDLE_INVALID_JSON",
      `Preview artifact is invalid JSON: ${relativePath}`,
      503,
      false,
    );
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
  try {
    return decodeURIComponent(raw);
  } catch {
    throw new PreviewBundleError(
      "INVALID_UNIVERSITY_ID",
      "University ID contains invalid percent encoding",
      400,
      false,
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
      : new PreviewBundleError(
          "BUNDLE_SCHEMA_INVALID",
          error instanceof Error ? error.message : "Preview bundle validation failed",
          503,
          false,
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

function applySummaryQuery(
  rows: Stage5Summary[],
  url: URL,
) {
  const states = url.searchParams.getAll("state");
  const tiers = url.searchParams.getAll("tier");
  const search = (url.searchParams.get("search") ?? "").trim().toLowerCase();
  const maxCostRmb = Number(url.searchParams.get("maxCostRmb"));
  return rows.filter((raw) => {
    const row = normalizeStage5Summary(raw);
    if (states.length && !states.includes(row.state ?? "")) return false;
    if (tiers.length && !tiers.includes(row.rankingTier ?? "other")) return false;
    if (
      search &&
      ![
        row.name,
        row.chineseName,
        row.city,
        row.state,
        raw.region,
        ...(raw.aliases ?? []),
        ...(raw.topPrograms ?? []),
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(search))
    ) {
      return false;
    }
    if (
      Number.isFinite(maxCostRmb) &&
      maxCostRmb > 0 &&
      typeof row.costSummary?.minimumUsd === "number" &&
      row.costSummary.minimumUsd * 7.2 > maxCostRmb
    ) {
      return false;
    }
    return true;
  }).map(normalizeStage5Summary);
}

export async function handleBackendPreviewRoute(
  req: Request,
  env: NodeJS.ProcessEnv,
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
    const manifest = parseStage5Manifest(await readArtifact(env, "manifest.json"));
    if (endpoint === "manifest") {
      const dictionary = normalizeStage5StatusDictionary(
        await readArtifact(env, "status-dictionary.json"),
      );
      return respond({
        ...manifest,
        statusDictionary: dictionary,
      });
    }

    if (endpoint === "universities") {
      const rows = parseStage5Summaries(await readArtifact(env, "universities.json"));
      return respond(applySummaryQuery(rows, url));
    }

    if (endpoint === "university") {
      const id = decodeUniversityId((url.searchParams.get("id") ?? "").trim());
      if (!id) {
        throw new PreviewBundleError(
          "MISSING_UNIVERSITY_ID",
          "University ID is required",
          400,
          false,
        );
      }
      let raw: ReturnType<typeof parseStage5Detail>;
      try {
        raw = parseStage5Detail(
          await readArtifact(env, `university-details/${id}.json`),
        );
      } catch (error) {
        if (
          error instanceof PreviewBundleError &&
          error.code === "BUNDLE_ARTIFACT_MISSING"
        ) {
          throw new PreviewBundleError(
            "UNIVERSITY_NOT_FOUND",
            `University not found: ${id}`,
            404,
            false,
          );
        }
        throw error;
      }
      if (raw.id !== id) {
        throw new PreviewBundleError(
          "SUMMARY_DETAIL_ID_MISMATCH",
          "Detail ID does not match request",
          503,
          false,
        );
      }
      const sourceIndex = parseStage5SourceIndex(
        await readArtifact(env, "source-index.json"),
      );
      return respond(normalizeStage5Detail(raw, sourceIndex));
    }

    if (endpoint === "region-metrics") {
      const region = parseStage5RegionEnvelope(
        await readArtifact(env, "region-metrics.json"),
      );
      return respond(region);
    }

    if (endpoint === "status-dictionary") {
      return respond(
        normalizeStage5StatusDictionary(
          await readArtifact(env, "status-dictionary.json"),
        ),
      );
    }

    if (endpoint === "source-index") {
      return respond(
        parseStage5SourceIndex(await readArtifact(env, "source-index.json")),
      );
    }

    if (endpoint === "search") {
      const query = (url.searchParams.get("q") ?? "").trim().toLowerCase();
      const limit = Math.max(0, Math.min(50, Number(url.searchParams.get("limit") ?? 20)));
      if (query.length < 2) return respond([]);
      const summaries = parseStage5Summaries(
        await readArtifact(env, "universities.json"),
      );
      const summaryMatches = summaries.filter((row) =>
          [
            row.name,
            row.chineseName,
            row.city,
            row.state,
            row.region,
            ...(row.aliases ?? []),
            ...(row.topPrograms ?? []),
          ]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(query)),
        );
      const matchedIds = new Set(summaryMatches.map((row) => row.id));
      const majorMatches = (
        await Promise.all(
          summaries
            .filter((row) => !matchedIds.has(row.id))
            .map(async (row) => {
              const detail = parseStage5Detail(
                await readArtifact(env, `university-details/${row.id}.json`),
              );
              return detail.allMajors.some((major) =>
                [major.name, major.displayName]
                  .filter(Boolean)
                  .some((value) => value.toLowerCase().includes(query)),
              )
                ? row
                : null;
            }),
        )
      ).filter((row): row is Stage5Summary => row !== null);
      const rows = [...summaryMatches, ...majorMatches]
        .slice(0, limit)
        .map(normalizeStage5Summary)
        .map((university) => ({ university, matchedField: "name" }));
      return respond(rows);
    }

    if (endpoint === "news") return respond([]);
    if (endpoint === "region-detail") {
      throw new PreviewBundleError(
        "REGION_METRICS_BLOCKED",
        "Region metrics are blocked for this Preview checkpoint",
        404,
        false,
        "blocked",
      );
    }
    throw new PreviewBundleError(
      "UNKNOWN_ENDPOINT",
      `Unknown Preview endpoint: ${endpoint}`,
      404,
      false,
    );
  } catch (error) {
    return previewErrorResponse(error, endpoint);
  }
}
