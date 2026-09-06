/** Import source-preserving IECG guide JSON into Supabase/Postgres.
 *
 * Usage:
 *   DATABASE_URL=... tsx scripts/import-iecg-guides.ts
 *
 * The script keeps unmatched profiles with a null university_id so source
 * material is not silently discarded. The UI only exposes linked profiles
 * from a selected PathOS university.
 */
import { readFile } from "node:fs/promises";
import path from "node:path";
import { Client } from "pg";

const DATABASE_URL = process.env.DATABASE_URL;
const INPUT_PATH = process.env.PATHOS_IECG_GUIDES_JSON ?? path.resolve("./data/college-guides/iecg-2025.json");

if (!DATABASE_URL) {
  console.error("DATABASE_URL is required");
  process.exit(1);
}

type Profile = {
  id: string;
  sourceFile: string;
  sourceSnapshotYear: number;
  schoolNameRaw?: string;
  sections: unknown[];
  structured: Record<string, unknown>;
  rawText: string;
  displayTier?: string;
  sourceStatus?: string;
};

type Bundle = { profiles: Profile[] };
type University = { id: string; name: string; chinese_name: string | null };

function normalize(value: string | null | undefined): string {
  return (value ?? "")
    .toLocaleLowerCase()
    .replace(/[\s\-—–_.,'’()（）/\\:&]+/g, "")
    .replace(/university|college|institute|of|the/g, "");
}

function resolveUniversity(profile: Profile, universities: University[]): University | null {
  const target = normalize(profile.schoolNameRaw);
  if (!target) return null;
  const exact = universities.find((row) => normalize(row.name) === target || normalize(row.chinese_name) === target);
  if (exact) return exact;
  return universities.find((row) => {
    const name = normalize(row.name);
    const chinese = normalize(row.chinese_name);
    return target.length >= 6 && (name.includes(target) || target.includes(name) || chinese.includes(target) || target.includes(chinese));
  }) ?? null;
}

async function main() {
  const bundle = JSON.parse(await readFile(INPUT_PATH, "utf8")) as Bundle;
  if (!Array.isArray(bundle.profiles)) throw new Error("profiles must be an array");
  const client = new Client({ connectionString: DATABASE_URL });
  await client.connect();
  try {
    const universities = (await client.query<University>("SELECT id, name, chinese_name FROM universities")).rows;
    await client.query("BEGIN");
    let linked = 0;
    let unmatched = 0;
    for (const profile of bundle.profiles) {
      const university = resolveUniversity(profile, universities);
      if (university) linked++;
      else unmatched++;
      await client.query(
        `INSERT INTO college_guides
          (id, university_id, source_file, source_snapshot_year, school_name_raw,
           source_url, sections, structured, raw_text, display_tier, source_status)
         VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,$9,$10,$11)
         ON CONFLICT (id) DO UPDATE SET
           university_id = EXCLUDED.university_id,
           source_file = EXCLUDED.source_file,
           source_snapshot_year = EXCLUDED.source_snapshot_year,
           school_name_raw = EXCLUDED.school_name_raw,
           source_url = EXCLUDED.source_url,
           sections = EXCLUDED.sections,
           structured = EXCLUDED.structured,
           raw_text = EXCLUDED.raw_text,
           display_tier = EXCLUDED.display_tier,
           source_status = EXCLUDED.source_status,
           updated_at = NOW()`,
        [
          profile.id,
          university?.id ?? null,
          profile.sourceFile,
          profile.sourceSnapshotYear,
          profile.schoolNameRaw ?? null,
          typeof profile.structured.officialWebsite === "string" ? profile.structured.officialWebsite : null,
          JSON.stringify(profile.sections ?? []),
          JSON.stringify(profile.structured ?? {}),
          profile.rawText,
          profile.displayTier ?? "preview",
          profile.sourceStatus ?? "archived_source",
        ],
      );
    }
    await client.query("COMMIT");
    console.log(`college guides: ${bundle.profiles.length}; linked: ${linked}; unmatched: ${unmatched}`);
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});