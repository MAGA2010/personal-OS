/**
 * ETL: flatten detail.undergraduateEnrollment / admissions.* onto summary.
 * Usage:
 *   DATABASE_URL=postgresql://... npx tsx scripts/enrich-summary-fields.ts
 *   DATABASE_URL=... npx tsx scripts/enrich-summary-fields.ts --dry-run
 * See src/server/enrich-summary.ts for the shared core.
 */
import { enrichSummaries, withClient } from "../src/server/enrich-summary";

async function loadEnv(): Promise<void> {
  if (process.env.DATABASE_URL) return;
  const fs = await import("node:fs/promises");
  const path = await import("node:path");
  const text = await fs.readFile(path.join(process.cwd(), ".env.local"), "utf8");
  for (const line of text.split(/\r?\n/)) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m && process.env[m[1]] === undefined) process.env[m[1]] = m[2];
  }
}

async function main(): Promise<void> {
  await loadEnv();
  const url = process.env.DATABASE_URL;
  if (!url) { console.error("DATABASE_URL is required"); process.exit(1); }
  const dryRun = process.argv.includes("--dry-run");
  console.log(`connected to ${new URL(url).host}${dryRun ? " (DRY RUN)" : ""}`);
  const report = await withClient(url, (c) => enrichSummaries(c, { dryRun }));
  console.log("\n=== summary ===");
  console.log(`rows scanned:  ${report.rowsScanned}`);
  console.log(`rows touched:  ${report.rowsTouched}${dryRun ? " (would be)" : ""}`);
  console.log(`fields filled:`);
  for (const [k, v] of Object.entries(report.fieldsFilled)) console.log(`  ${k}: ${v}`);
}

main().catch((e) => { console.error(e); process.exit(1); });

