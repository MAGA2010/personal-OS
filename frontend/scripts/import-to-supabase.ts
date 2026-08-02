/**
 * ETL: Stage 5 Preview Bundle JSON -> Supabase Postgres.
 *
 * Usage:
 *   DATABASE_URL=postgresql://... tsx scripts/import-to-supabase.ts
 *
 * Run after `npm run db:reset` (or after manually applying schema.sql in
 * the Supabase SQL Editor). Safe to re-run; uses UPSERT semantics.
 *
 * Windows note: 62 detail files use ":" in their filenames (e.g.
 * "candidate-v2:harvard-university.json"), which NTFS rejects. We
 * detect missing files and fall back to `git show HEAD:<path>` so the
 * script works locally on Windows. On Render / Linux the filesystem
 * path is used directly.
 */
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { Client } from "pg";

const DATABASE_URL = process.env.DATABASE_URL;
const BUNDLE_DIR = process.env.PATHOS_PREVIEW_BUNDLE_DIR ?? "./data/preview";
const REPO_ROOT = process.env.PATHOS_REPO_ROOT ?? path.resolve(BUNDLE_DIR, "../..");

if (!DATABASE_URL) {
  console.error("DATABASE_URL is required");
  process.exit(1);
}

interface UniversitySummary {
  id: string;
  name: string;
  chineseName?: string;
  city?: string;
  state?: string;
  region?: string;
  schoolType?: string;
  rankingBand?: string;
  rankingTier?: string;
  nationalRanking?: number | null;
  latitude?: number;
  longitude?: number;
  displayTier?: string;
  sourceStatus?: string;
  sourceCommit?: string;
  datasetVersion?: string;
  previewOnly?: boolean;
  aliases?: string[];
  topPrograms?: string[];
}

interface UniversityDetail {
  id?: string;
  allMajors?: Array<{ name?: string; displayName?: string }>;
  [k: string]: unknown;
}

interface RegionMetric {
  fipsCode: string;
  granularity: string;
  metricId: string;
  name?: string;
  nameEn?: string;
  value?: number | null;
  rawValue?: number | null;
  displayValue?: string;
  year?: number | null;
  source?: string;
}

async function readBundleFile(relPath: string): Promise<string> {
  const absPath = path.join(BUNDLE_DIR, relPath);
  if (existsSync(absPath)) {
    return readFile(absPath, "utf8");
  }
  if (process.platform === "win32") {
    const repoRel = path.relative(REPO_ROOT, absPath).replace(/\\/g, "/");
    try {
      const out = execFileSync("git", ["show", `HEAD:${repoRel}`], {
        cwd: REPO_ROOT,
        encoding: "utf8",
        stdio: ["ignore", "pipe", "pipe"],
        maxBuffer: 16 * 1024 * 1024,
      });
      return out;
    } catch (e) {
      throw new Error(`File not on disk and git fallback failed: ${repoRel}`);
    }
  }
  throw new Error(`File missing: ${absPath}`);
}

async function readJson<T>(relPath: string): Promise<T> {
  const text = await readBundleFile(relPath);
  return JSON.parse(text) as T;
}

function buildSearchText(summary: UniversitySummary, detail: UniversityDetail | null): string {
  const parts: (string | undefined)[] = [
    summary.name,
    summary.chineseName,
    summary.city,
    summary.state,
    summary.region,
    ...(summary.aliases ?? []),
    ...(summary.topPrograms ?? []),
  ];
  if (detail) {
    for (const m of detail.allMajors ?? []) {
      if (m.name) parts.push(m.name);
      if (m.displayName && m.displayName !== m.name) parts.push(m.displayName);
    }
  }
  return parts.filter(Boolean).join(" ");
}

async function main() {
  const client = new Client({ connectionString: DATABASE_URL });
  await client.connect();
  console.log("connected");

  await client.query("BEGIN");

  // 1. manifest (single row)
  const manifest = await readJson<Record<string, unknown>>("manifest.json");
  await client.query(
    `INSERT INTO manifest (id, payload) VALUES (1, $1)
     ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()`,
    [JSON.stringify(manifest)],
  );
  console.log("manifest");

  // 2. universities + university_details
  const universities = await readJson<UniversitySummary[]>("universities.json");
  let uniCount = 0;
  let detailCount = 0;
  for (const u of universities) {
    let detail: UniversityDetail | null = null;
    try {
      detail = await readJson<UniversityDetail>(`university-details/${u.id}.json`);
    } catch (e) {
      console.warn(`  skip detail for ${u.id}: ${(e as Error).message}`);
    }
    const searchText = buildSearchText(u, detail);
    await client.query(
      `INSERT INTO universities
        (id, name, chinese_name, city, state, region, school_type,
         ranking_band, ranking_tier, national_ranking, latitude, longitude,
         display_tier, source_status, source_commit, dataset_version,
         preview_only, payload, search_text)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,to_tsvector(''''simple'''', $19))
       ON CONFLICT (id) DO UPDATE SET
         name = EXCLUDED.name, chinese_name = EXCLUDED.chinese_name,
         city = EXCLUDED.city, state = EXCLUDED.state, region = EXCLUDED.region,
         school_type = EXCLUDED.school_type, ranking_band = EXCLUDED.ranking_band,
         ranking_tier = EXCLUDED.ranking_tier, national_ranking = EXCLUDED.national_ranking,
         latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude,
         display_tier = EXCLUDED.display_tier, source_status = EXCLUDED.source_status,
         source_commit = EXCLUDED.source_commit, dataset_version = EXCLUDED.dataset_version,
         preview_only = EXCLUDED.preview_only, payload = EXCLUDED.payload,
         search_text = EXCLUDED.search_text, updated_at = NOW()`,
      [
        u.id, u.name, u.chineseName ?? null, u.city ?? null, u.state ?? null,
        u.region ?? null, u.schoolType ?? null, u.rankingBand ?? null,
        u.rankingTier ?? null, u.nationalRanking ?? null, u.latitude ?? null,
        u.longitude ?? null, u.displayTier ?? null, u.sourceStatus ?? null,
        u.sourceCommit ?? null, u.datasetVersion ?? null, u.previewOnly ?? true,
        JSON.stringify(u), searchText,
      ],
    );
    uniCount++;
    if (detail) {
      await client.query(
        `INSERT INTO university_details (university_id, payload) VALUES ($1, $2)
         ON CONFLICT (university_id) DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()`,
        [u.id, JSON.stringify(detail)],
      );
      detailCount++;
    }
  }
  console.log(`universities: ${uniCount}, details: ${detailCount}`);

  // 3. region_envelope (single row, full envelope JSONB)
  const rmEnvelope = await readJson<Record<string, unknown>>("region-metrics.json");
  await client.query(
    `INSERT INTO region_envelope (id, payload) VALUES (1, $1)
     ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()`,
    [JSON.stringify(rmEnvelope)],
  );
  const recordCount = Array.isArray(rmEnvelope.records) ? (rmEnvelope.records as unknown[]).length : 0;
  console.log(`region_envelope: 1 row, ${recordCount} records in payload`);

  // 4. status_dictionary
  const sdRaw = await readJson<Record<string, unknown>>("status-dictionary.json");
  for (const [code, payload] of Object.entries(sdRaw)) {
    await client.query(
      `INSERT INTO status_dictionary (code, payload) VALUES ($1, $2)
       ON CONFLICT (code) DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()`,
      [code, JSON.stringify(payload)],
    );
  }
  console.log(`status_dictionary: ${Object.keys(sdRaw).length}`);

  // 5. source_index (single row)
  const siRaw = await readJson<{ sources?: unknown[] } & Record<string, unknown>>("source-index.json");
  await client.query(
    `INSERT INTO source_index (id, payload) VALUES (1, $1)
     ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()`,
    [JSON.stringify(siRaw)],
  );
  console.log(`source_index: ${(siRaw.sources ?? []).length} sources`);

  await client.query("COMMIT");
  await client.end();
  console.log("done");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
