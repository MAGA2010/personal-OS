/**
 * Drop and recreate all PathOS Preview tables. DESTRUCTIVE.
 *
 * Usage:
 *   DATABASE_URL=postgresql://... tsx scripts/reset-schema.ts
 */
import { readFile } from "node:fs/promises";
import path from "node:path";
import { Client } from "pg";

const DATABASE_URL = process.env.DATABASE_URL;
const SCHEMA_PATH = process.env.PATHOS_SCHEMA_PATH ?? path.resolve("./db/schema.sql");

if (!DATABASE_URL) { console.error("DATABASE_URL is required"); process.exit(1); }

async function main() {
  const client = new Client({ connectionString: DATABASE_URL });
  await client.connect();
  await client.query(`
    DROP TABLE IF EXISTS university_details CASCADE;
    DROP TABLE IF EXISTS universities CASCADE;
    DROP TABLE IF EXISTS region_envelope CASCADE;
    DROP TABLE IF EXISTS status_dictionary CASCADE;
    DROP TABLE IF EXISTS source_index CASCADE;
    DROP TABLE IF EXISTS manifest CASCADE;
  `);
  console.log("dropped");
  const sql = await readFile(SCHEMA_PATH, "utf8");
  await client.query(sql);
  console.log("applied schema.sql");
  await client.end();
}
main().catch((e) => { console.error(e); process.exit(1); });
