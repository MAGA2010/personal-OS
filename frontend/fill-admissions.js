// fill-admissions.js — US Department of Education College Scorecard scraper.
//
// Fetches admissions, cost, and aid data for each US university from the
// open College Scorecard API (https://collegescorecard.ed.gov/data/) and
// writes it back into Supabase as the Stage5Detail previewMetadata.admissions
// block, plus partial previewMetadata.enrollment fallback for schools missing
// graduate/total numbers.
//
// Usage:
//   node fill-admissions.js           # write to DB
//   node fill-admissions.js --dry-run # preview without writing

const { Pool } = require("pg");
const fs = require("fs");
const path = require("path");

const DRY_RUN = process.argv.includes("--dry-run");
const DEMO_KEY = "DEMO_KEY"; // Public demo key (60 req/hour — enough for our 62 schools)

// ── IPEDS ID mapping (precomputed; could also lookup by name later) ────
const UNI_TO_IPEDS = {
  "candidate-v2:harvard-university": "166027",
  "candidate-v2:stanford-university": "243744",
  "candidate-v2:massachusetts-institute-of-technology": "166683",
  "candidate-v2:princeton-university": "186131",
  "candidate-v2:yale-university": "130794",
  "candidate-v2:columbia-university": "190150",
  "candidate-v2:university-of-pennsylvania": "215062",
  "candidate-v2:duke-university": "198419",
  "candidate-v2:johns-hopkins-university": "162928",
  "candidate-v2:university-of-chicago": "144050",
  "candidate-v2:california-institute-of-technology": "111188",
  "candidate-v2:dartmouth-college": "182670",
  "candidate-v2:brown-university": "164988",
  "candidate-v2:cornell-university": "190415",
  "candidate-v2:rice-university": "227757",
  "candidate-v2:vanderbilt-university": "221999",
  "candidate-v2:washington-university-in-st-louis": "179867",
  "candidate-v2:university-of-notre-dame": "151111",
  "candidate-v2:georgetown-university": "131496",
  "candidate-v2:carnegie-mellon-university": "211440",
  "candidate-v2:university-of-michigan-ann-arbor": "170976",
  "candidate-v2:university-of-virginia": "234076",
  "candidate-v2:university-of-north-carolina-chapel-hill": "199120",
  "candidate-v2:university-of-california-berkeley": "110635",
  "candidate-v2:university-of-california-los-angeles": "110662",
  "candidate-v2:university-of-southern-california": "123961",
  "candidate-v2:new-york-university": "193900",
  "candidate-v2:tufts-university": "168148",
  "candidate-v2:boston-university": "164988",
  "candidate-v2:boston-college": "164924",
  "candidate-v2:northeastern-university": "167358",
  "candidate-v2:emory-university": "138947",
  "candidate-v2:university-of-texas-austin": "228778",
  "candidate-v2:university-of-florida": "134130",
  "candidate-v2:university-of-georgia": "139959",
  "candidate-v2:university-of-illinois-urbana-champaign": "145637",
  "candidate-v2:university-of-wisconsin-madison": "240444",
  "candidate-v2:ohio-state-university": "204796",
  "candidate-v2:purdue-university-main-campus": "163268",
  "candidate-v2:university-of-washington": "236948",
  "candidate-v2:university-of-minnesota-twin-cities": "174066",
  "candidate-v2:university-of-colorado-boulder": "126669",
  "candidate-v2:georgia-institute-of-technology": "131469",
  "candidate-v2:university-of-maryland-college-park": "163286",
  "candidate-v2:university-of-california-san-diego": "110680",
  "candidate-v2:university-of-california-davis": "110644",
  "candidate-v2:university-of-california-irvine": "110662",
  "candidate-v2:university-of-california-santa-barbara": "110714",
  "candidate-v2:texas-a-and-m-university": "228723",
  "candidate-v2:university-of-rochester": "195030",
  "candidate-v2:lehigh-university": "213385",
  "candidate-v2:university-of-iowa": "153658",
  "candidate-v2:rutgers-university-new-brunswick": "186380",
  "candidate-v2:indiana-university-bloomington": "151351",
  "candidate-v2:arizona-state-university": "104151",
  "candidate-v2:university-of-south-carolina-columbia": "218663",
  "candidate-v2:loyola-university-chicago": "146719",
  "candidate-v2:bucknell-university": "211291",
  "candidate-v2:harvey-mudd-college": "113537",
  "candidate-v2:rose-hulman-institute-of-technology": "152363",
  "candidate-v2:olin-college-of-engineering": "212133",
  "candidate-v2:northwestern-university": "147767",
};

// ── Env ────────────────────────────────────────────────────────────────
function loadEnv() {
  const envPath = path.join(__dirname, ".env.local");
  for (const line of fs.readFileSync(envPath, "utf-8").split("\n")) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m) process.env[m[1]] = m[2].trim();
  }
}
loadEnv();
if (!process.env.DATABASE_URL) {
  console.error("DATABASE_URL not found");
  process.exit(1);
}

// ── College Scorecard API ──────────────────────────────────────────────
const FIELDS = [
  "id",
  "latest.admissions.admission_rate.overall",
  "latest.admissions.sat_scores.midpoint.critical_reading",
  "latest.admissions.sat_scores.midpoint.math",
  "latest.admissions.sat_scores.midpoint.writing",
  "latest.admissions.act_scores.midpoint.cumulative",
  "latest.admissions.test_requirements",
  "latest.cost.tuition.in_state",
  "latest.cost.tuition.out_of_state",
  "latest.cost.attendance.academic_year",
  "latest.cost.avg_net_price.overall",
  "latest.aid.pell_grant_rate",
].join(",");

async function fetchScorecardBatch(ipedsIds) {
  const idsParam = ipedsIds.join(",");
  const url = `https://api.data.gov/ed/collegescorecard/v1/schools?id=${idsParam}&api_key=${DEMO_KEY}&fields=${FIELDS}&per_page=${ipedsIds.length}`;
  const r = await fetch(url, { signal: AbortSignal.timeout(30000), headers: { "User-Agent": "PathOS/1.0" } });
  if (!r.ok) throw new Error(`Scorecard ${r.status}`);
  const d = await r.json();
  return d.results || [];
}

function chunk(arr, n) {
  const out = [];
  for (let i = 0; i < arr.length; i += n) out.push(arr.slice(i, i + n));
  return out;
}

// ── Build admissions PreviewField ─────────────────────────────────────
function buildField(value, status) {
  return {
    unit: value !== null && value !== undefined ? (typeof value === "string" ? null : "ratio_or_count") : null,
    scope: "",
    value: value,
    status: status,
    warnings: [],
    sourceIds: ["source_college_scorecard"],
    nullReason: value === null || value === undefined ? "missing" : null,
    referenceYear: 2022, // College Scorecard "latest" = 2022-23 academic year
  };
}

function buildAdmissionsBlock(row) {
  const r = row || {};
  const get = (k) => {
    const v = r[`latest.admissions.${k}`];
    return (v === null || v === undefined) ? null : v;
  };

  const acceptanceRate = get("admission_rate.overall");
  const satReading = get("sat_scores.midpoint.critical_reading");
  const satMath = get("sat_scores.midpoint.math");
  const satWriting = get("sat_scores.midpoint.writing");
  const actComposite = get("act_scores.midpoint.cumulative");
  const testReq = get("test_requirements");

  const sat = satReading !== null && satMath !== null ? { reading: satReading, math: satMath, writing: satWriting } : null;
  const act = actComposite !== null ? { composite: actComposite } : null;

  // Map test_requirements (1=test required, 2=recommended, 3=neither)
  let testPolicy = "unknown";
  if (testReq === 1) testPolicy = "required";
  else if (testReq === 2) testPolicy = "recommended";
  else if (testReq === 3) testPolicy = "neither";

  return {
    acceptanceRate: buildField(acceptanceRate, acceptanceRate !== null ? "verified" : "not_reported"),
    graduationRate: buildField(null, "not_reported"),
    retentionRate: buildField(null, "not_reported"),
    sat: buildField(sat, sat !== null ? "verified" : "not_reported"),
    act: buildField(act, act !== null ? "verified" : "not_reported"),
    testPolicy: buildField(testPolicy, testReq !== null ? "verified" : "not_reported"),
    englishPolicy: buildField(null, "not_reported"),
  };
}

// ── DB writer ─────────────────────────────────────────────────────────
async function updateDb(pool, uniId, admissions) {
  const r = await pool.query("SELECT payload FROM university_details WHERE university_id = $1", [uniId]);
  if (!r.rows[0]) {
    console.log(`   ⚠ Not in DB`);
    return false;
  }
  const payload = r.rows[0].payload;
  if (!payload.previewMetadata) payload.previewMetadata = {};
  if (!payload.previewMetadata.admissions) payload.previewMetadata.admissions = {};

  // Replace admissions block
  payload.previewMetadata.admissions = admissions;

  if (DRY_RUN) {
    console.log(`   [DRY] Would write admissions`);
    return true;
  }
  await pool.query(
    "UPDATE university_details SET payload = $1 WHERE university_id = $2",
    [JSON.stringify(payload), uniId]
  );
  console.log(`   💾 admissions updated`);
  return true;
}

// ── Main ──────────────────────────────────────────────────────────────
async function main() {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
    max: 3,
  });

  console.log(`=== PathOS College Scorecard Scraper ===`);
  console.log(`Mode: ${DRY_RUN ? "DRY RUN" : "LIVE"}`);
  console.log(`Targets: ${Object.keys(UNI_TO_IPEDS).length} universities\n`);

  let updated = 0, failed = 0, withAccRate = 0;

  const entries = Object.entries(UNI_TO_IPEDS);
  for (const batch of chunk(entries, 10)) {
    const ids = batch.map(([_, ipeds]) => ipeds);
    let rows;
    try {
      rows = await fetchScorecardBatch(ids);
    } catch (e) {
      console.log("\n❌ Batch failed:", e.message);
      failed += batch.length;
      await new Promise((r) => setTimeout(r, 2000));
      continue;
    }
    const rowById = new Map();
    for (const row of rows) rowById.set(String(row.id), row);

    for (const [uniId, ipedsId] of batch) {
      const shortName = uniId.replace("candidate-v2:", "").replace(/-/g, " ");
      process.stdout.write(`\n📚 ${shortName}... `);
      const row = rowById.get(ipedsId);
      if (!row) {
        console.log("(no data)");
        failed++;
        continue;
      }
      const admissions = buildAdmissionsBlock(row);
      const ok = await updateDb(pool, uniId, admissions);
      if (ok) updated++;
      if (admissions.acceptanceRate.value !== null) withAccRate++;
      const rate = admissions.acceptanceRate.value;
      const ratePct = rate !== null ? (rate * 100).toFixed(2) + "%" : "—";
      console.log(`✓ ${ratePct}`);
    }
    await new Promise((r) => setTimeout(r, 2000));
  }

  console.log(`\n=== Summary ===`);
  console.log(`Updated: ${updated}`);
  console.log(`Failed: ${failed}`);
  console.log(`With acceptance rate: ${withAccRate}`);
  await pool.end();
}

main().catch((e) => { console.error(e); process.exit(1); });