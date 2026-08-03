// fill-notable-people.js — OpenAlex scraper for notableAttendance and people
//
// For each of 62 universities, queries OpenAlex for the most-cited authors
// ever affiliated (faculty + alumni) and writes them to Supabase.
//
// OpenAlex (https://openalex.org) is an open replacement for Microsoft
// Academic Graph — accessible in this environment where Wikipedia is not.
// Data is academic-publication-based, so the names will skew toward
// researchers (which is appropriate for a "people" field on a college
// admissions site, and complementary to business/political famous alumni).
//
// Usage:
//   node fill-notable-people.js            # write to DB
//   node fill-notable-people.js --dry-run  # preview without writing
//   node fill-notable-people.js --limit=N  # override 30 authors/school
//   node fill-notable-people.js --only=HARVARD  # just one school

const { Pool } = require("pg");
const fs = require("fs");
const path = require("path");

const DRY_RUN = process.argv.includes("--dry-run");
const args = process.argv.slice(2);
const limitArg = args.find((a) => a.startsWith("--limit="));
const PER_SCHOOL = limitArg ? Number(limitArg.split("=")[1]) : 30;
const onlyArg = args.find((a) => a.startsWith("--only="));
const ONLY = onlyArg ? onlyArg.split("=")[1].toUpperCase() : null;

// ── Env ──────────────────────────────────────────────────────────────────
function loadEnv() {
  const envPath = path.join(__dirname, ".env.local");
  const content = fs.readFileSync(envPath, "utf-8");
  for (const line of content.split("\n")) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m) process.env[m[1]] = m[2].trim();
  }
}
loadEnv();
if (!process.env.DATABASE_URL) {
  console.error("DATABASE_URL not found in .env.local");
  process.exit(1);
}

// ── Mapping: PathOS ID → OpenAlex ID ────────────────────────────────────
const UNI_OA_ID = {
  "candidate-v2:harvard-university": "I136199984",
  "candidate-v2:stanford-university": "I97018004",
  "candidate-v2:massachusetts-institute-of-technology": "I63966007",
  "candidate-v2:princeton-university": "I20089843",
  "candidate-v2:yale-university": "I32971472",
  "candidate-v2:columbia-university": "I78577930",
  "candidate-v2:university-of-pennsylvania": "I79576946",
  "candidate-v2:duke-university": "I170897317",
  "candidate-v2:johns-hopkins-university": "I145311948",
  "candidate-v2:university-of-chicago": "I40347166",
  "candidate-v2:california-institute-of-technology": "I122411786",
  "candidate-v2:dartmouth-college": "I107672454",
  "candidate-v2:brown-university": "I27804330",
  "candidate-v2:cornell-university": "I205783295",
  "candidate-v2:rice-university": "I74775410",
  "candidate-v2:vanderbilt-university": "I200719446",
  "candidate-v2:washington-university-in-st-louis": "I204465549",
  "candidate-v2:university-of-notre-dame": "I107639228",
  "candidate-v2:georgetown-university": "I184565670",
  "candidate-v2:carnegie-mellon-university": "I74973139",
  "candidate-v2:university-of-michigan-ann-arbor": "I27837315",
  "candidate-v2:university-of-virginia": "I51556381",
  "candidate-v2:university-of-north-carolina-chapel-hill": "I114027177",
  "candidate-v2:university-of-california-berkeley": "I95457486",
  "candidate-v2:university-of-california-los-angeles": "I161318765",
  "candidate-v2:university-of-southern-california": "I1174212",
  "candidate-v2:new-york-university": "I57206974",
  "candidate-v2:tufts-university": "I121934306",
  "candidate-v2:boston-university": "I111088046",
  "candidate-v2:boston-college": "I103531236",
  "candidate-v2:northeastern-university": "I12912129",
  "candidate-v2:emory-university": "I150468666",
  "candidate-v2:university-of-texas-austin": "I86519309",
  "candidate-v2:university-of-florida": "I33213144",
  "candidate-v2:university-of-georgia": "I165733156",
  "candidate-v2:university-of-illinois-urbana-champaign": "I157725225",
  "candidate-v2:university-of-wisconsin-madison": "I135310074",
  "candidate-v2:ohio-state-university": "I52357470",
  "candidate-v2:purdue-university-main-campus": "I219193219",
  "candidate-v2:university-of-washington": "I201448701",
  "candidate-v2:university-of-minnesota-twin-cities": "I130238516",
  "candidate-v2:university-of-colorado-boulder": "I188538660",
  "candidate-v2:georgia-institute-of-technology": "I130701444",
  "candidate-v2:university-of-maryland-college-park": "I66946132",
  "candidate-v2:university-of-california-san-diego": "I36258959",
  "candidate-v2:university-of-california-davis": "I84218800",
  "candidate-v2:university-of-california-irvine": "I204250578",
  "candidate-v2:university-of-california-santa-barbara": "I154570441",
  "candidate-v2:texas-a-and-m-university": "I91045830",
  "candidate-v2:university-of-rochester": "I5388228",
  "candidate-v2:lehigh-university": "I186143895",
  "candidate-v2:university-of-iowa": "I126307644",
  "candidate-v2:rutgers-university-new-brunswick": "I102322142",
  "candidate-v2:indiana-university-bloomington": "I4210119109",
  "candidate-v2:arizona-state-university": "I55732556",
  "candidate-v2:university-of-south-carolina-columbia": "I155781252",
  "candidate-v2:loyola-university-chicago": "I1925986",
  "candidate-v2:bucknell-university": "I131221577",
  "candidate-v2:harvey-mudd-college": "I133543626",
  "candidate-v2:rose-hulman-institute-of-technology": "I192578771",
  "candidate-v2:olin-college-of-engineering": "I137428128",
  "candidate-v2:northwestern-university": "I111979921",
};

// ── OpenAlex API ────────────────────────────────────────────────────────

const UA = { "User-Agent": "PathOS/1.0 (pathos.app; mailto:dev@pathos.app)" };

async function fetchTopAuthors(oaId, perPage) {
  const url = `https://api.openalex.org/authors?filter=affiliations.institution.id:${oaId}&per-page=${perPage}&sort=cited_by_count:desc`;
  const r = await fetch(url, { signal: AbortSignal.timeout(25000), headers: UA });
  if (!r.ok) throw new Error(`OpenAlex ${r.status}`);
  return (await r.json()).results || [];
}

// Classify as faculty vs alumni based on current institution
function classify(author, schoolOaId) {
  const current = author.last_known_institutions || [];
  const isCurrent = current.some((i) => i.id?.endsWith(schoolOaId));
  return isCurrent ? "faculty" : "alumnus_unspecified";
}

function shortInstitutionName(inst) {
  return (inst?.display_name || "").replace(/,? (United States|USA|U\.S\.A\.)$/i, "").slice(0, 80);
}

// ── Build records ───────────────────────────────────────────────────────

function buildRecords(authors, schoolOaId, uniId) {
  const shortId = uniId.replace("candidate-v2:", "");
  const attendance = [];
  const people = [];
  const seen = new Set();

  for (const a of authors) {
    const name = a.display_name;
    if (!name) continue;
    if (seen.has(name.toLowerCase())) continue;
    seen.add(name.toLowerCase());

    const rel = classify(a, schoolOaId);
    const inst = (a.last_known_institutions || [])[0];
    const instName = shortInstitutionName(inst);
    const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

    // Notable attendance record
    attendance.push({
      personName: name,
      relationship: rel === "faculty" ? "current_faculty" : "attended",
      program: instName,
    });

    // People record
    people.push({
      id: `person:${slug}:${shortId}:openalex-${a.id?.split("/").pop() || "x"}`,
      name,
      relationshipType: rel,
      verificationStatus: "ai_assisted",
      sourceIds: ["source_openalex"],
      displayTier: "preview",
      quarantined: false,
      // Extra metadata for UI:
      _meta: {
        cited_by_count: a.cited_by_count,
        works_count: a.works_count,
        current_inst: instName,
        oa_id: a.id?.split("/").pop(),
      },
    });
  }
  return { attendance, people };
}

// ── DB writer ──────────────────────────────────────────────────────────

async function updateDb(pool, uniId, attendance, people) {
  const r = await pool.query(
    "SELECT payload FROM university_details WHERE university_id = $1",
    [uniId]
  );
  if (!r.rows[0]) {
    console.log(`   ⚠ Not in DB`);
    return false;
  }
  const payload = r.rows[0].payload;
  const existingAttendance = payload.notableAttendance || [];
  const existingPeople = payload.people || [];

  if (existingAttendance.length >= attendance.length && existingPeople.length >= people.length) {
    console.log(`   ⏭ Already has ${existingAttendance.length} attendance, ${existingPeople.length} people`);
    return false;
  }

  const existingNames = new Set([
    ...existingAttendance.map((a) => a.personName?.toLowerCase()),
    ...existingPeople.map((p) => p.name?.toLowerCase()),
  ]);

  const newAttendance = attendance.filter((a) => !existingNames.has(a.personName?.toLowerCase()));
  const newPeople = people.filter((p) => !existingNames.has(p.name?.toLowerCase()));

  // Strip _meta before writing (it's UI-only)
  const cleanPeople = newPeople.map(({ _meta, ...rest }) => rest);
  payload.notableAttendance = [...existingAttendance, ...newAttendance];
  payload.people = [...existingPeople, ...cleanPeople];

  if (DRY_RUN) {
    console.log(`   [DRY] +${newAttendance.length} attendance, +${newPeople.length} people`);
    return true;
  }

  await pool.query(
    "UPDATE university_details SET payload = $1 WHERE university_id = $2",
    [JSON.stringify(payload), uniId]
  );
  console.log(`   💾 +${newAttendance.length} attendance, +${newPeople.length} people`);
  return true;
}

// ── Main ────────────────────────────────────────────────────────────────

async function main() {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
    max: 3,
  });

  console.log(`=== PathOS OpenAlex People Scraper ===`);
  console.log(`Mode: ${DRY_RUN ? "DRY RUN" : "LIVE"}`);
  console.log(`Per-school limit: ${PER_SCHOOL} authors`);
  console.log(`Targets: ${Object.keys(UNI_OA_ID).length} universities\n`);

  let totalAtt = 0, totalPeople = 0, updated = 0, failed = 0;

  for (const [uniId, oaId] of Object.entries(UNI_OA_ID)) {
    if (ONLY && !uniId.toUpperCase().includes(ONLY)) continue;

    const shortName = uniId.replace("candidate-v2:", "").replace(/-/g, " ");
    process.stdout.write(`\n📚 ${shortName}... `);

    try {
      const authors = await fetchTopAuthors(oaId, PER_SCHOOL);
      if (!authors.length) {
        console.log("(no authors found)");
        continue;
      }

      const { attendance, people } = buildRecords(authors, oaId, uniId);
      const ok = await updateDb(pool, uniId, attendance, people);
      totalAtt += attendance.length;
      totalPeople += people.length;
      if (ok) updated++;

      // Sample
      const sample = authors.slice(0, 3).map((a) => a.display_name).join(", ");
      console.log(`  Top: ${sample}` + (authors.length > 3 ? ` (+${authors.length - 3})` : ""));
    } catch (e) {
      console.log(`❌ ${e.message}`);
      failed++;
    }

    await new Promise((r) => setTimeout(r, 400));
  }

  console.log(`\n=== Summary ===`);
  console.log(`Attendance scraped: ${totalAtt}`);
  console.log(`People scraped: ${totalPeople}`);
  console.log(`Schools updated: ${updated}`);
  console.log(`Failed: ${failed}`);
  await pool.end();
}

main().catch((e) => { console.error(e); process.exit(1); });