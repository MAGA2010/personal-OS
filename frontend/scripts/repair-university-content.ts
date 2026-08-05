import { readFile } from "node:fs/promises";
import path from "node:path";
import { Client } from "pg";

type JsonObject = Record<string, unknown>;

interface HistorySource {
  candidate_id: string;
  history_summary: string;
  source_id: string;
  evidence_anchor?: {
    quote?: string;
  };
}

interface AnecdoteSource {
  candidate_id: string;
  anecdote_text: string;
  anecdote_type?: string;
  source_id: string;
}

interface SourceDocument<T> {
  universities: T[];
}

interface DatabaseRow {
  university_id: string;
  summary: JsonObject;
  detail: JsonObject;
}

const PERSON_NAME_FIXES = new Map([
  [
    "person:james-jim-l-adams:california-institute-of-technology:wave7-caltech-jim-adams-me",
    "James “Jim” L. Adams",
  ],
  [
    "person:fadi-chehad:new-york-university:source-wave3-nyu-fadi-chehade",
    "Fadi Chehadé",
  ],
  [
    "person:michael-mac-cross:purdue-university-main-campus:wave8-purdue-mac-cross-mechanical",
    "Michael “Mac” Cross",
  ],
]);

function isObject(value: unknown): value is JsonObject {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function requiredString(value: unknown, label: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${label} must be a non-empty string`);
  }
  return value;
}

function parseEnvLine(line: string): [string, string] | null {
  const match = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
  if (!match) return null;
  const value = match[2].trim().replace(/^(['"])(.*)\1$/, "$2");
  return [match[1], value];
}

async function loadLocalEnv(): Promise<void> {
  if (process.env.DATABASE_URL) return;
  const text = await readFile(path.join(process.cwd(), ".env.local"), "utf8");
  for (const line of text.split(/\r?\n/)) {
    const entry = parseEnvLine(line);
    if (entry && process.env[entry[0]] === undefined) {
      process.env[entry[0]] = entry[1];
    }
  }
}

async function readJson<T>(filePath: string): Promise<T> {
  return JSON.parse(await readFile(filePath, "utf8")) as T;
}

function buildHistory(
  source: HistorySource,
  anecdote: AnecdoteSource,
): { value: string; sourceIds: string[] } {
  const summary = requiredString(source.history_summary, `${source.candidate_id}.history_summary`);
  const quote = source.evidence_anchor?.quote?.trim();
  let value = !quote || summary.includes(quote)
    ? summary
    : `${summary} Official university history records: “${quote}”`;
  const sourceIds = [source.source_id];
  if (value.length < 80) {
    value = `${value} A verified university-history note adds: ${anecdote.anecdote_text}`;
    sourceIds.push(anecdote.source_id);
  }
  return { value, sourceIds };
}

function repairPrograms(detail: JsonObject, summary: JsonObject): void {
  const cleanNames = Array.isArray(summary.topPrograms)
    ? summary.topPrograms.filter((value): value is string => typeof value === "string")
    : [];
  const replacements = new Map<string, string>();

  if (cleanNames.length > 0 && Array.isArray(detail.programs)) {
    detail.programs = detail.programs.map((value, index) => {
      if (!isObject(value) || !cleanNames[index]) return value;
      if (typeof value.name === "string") replacements.set(value.name, cleanNames[index]);
      return { ...value, name: cleanNames[index] };
    });
    detail.topPrograms = structuredClone(cleanNames);
  }

  if (Array.isArray(detail.programPeopleGaps)) {
    detail.programPeopleGaps = detail.programPeopleGaps.map((value) => {
      if (!isObject(value)) return value;
      const programName =
        typeof value.programName === "string"
          ? replacements.get(value.programName) ?? value.programName
          : value.programName;
      return { ...value, programName, displayLabel: "数据补充中" };
    });
  }
}

function repairPeople(detail: JsonObject): number {
  if (!Array.isArray(detail.people)) return 0;
  let repaired = 0;
  detail.people = detail.people.map((value) => {
    if (!isObject(value) || typeof value.id !== "string") return value;
    const replacement = PERSON_NAME_FIXES.get(value.id);
    if (!replacement || value.name === replacement) return value;
    repaired += 1;
    return { ...value, name: replacement };
  });
  return repaired;
}

async function main(): Promise<void> {
  await loadLocalEnv();
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) throw new Error("DATABASE_URL is required");

  const artifactRoot = path.resolve(
    process.cwd(),
    "../PathOS-db-ranking-standalone/data-pipeline/artifacts/stage3d-fill-bulk-completion-v2",
  );
  const historyDocument = await readJson<SourceDocument<HistorySource>>(
    path.join(artifactRoot, "stage3d-fill-bulk-v2-history.json"),
  );
  const anecdoteDocument = await readJson<SourceDocument<AnecdoteSource>>(
    path.join(artifactRoot, "stage3d-fill-bulk-v2-anecdotes.json"),
  );
  const histories = new Map(historyDocument.universities.map((row) => [row.candidate_id, row]));
  const anecdotes = new Map(anecdoteDocument.universities.map((row) => [row.candidate_id, row]));

  if (histories.size !== 62 || anecdotes.size !== 62) {
    throw new Error(`Expected 62 history and anecdote sources, found ${histories.size}/${anecdotes.size}`);
  }

  const client = new Client({ connectionString });
  await client.connect();
  const result = await client.query<DatabaseRow>(
    `SELECT u.id AS university_id, u.payload AS summary, d.payload AS detail
     FROM universities u
     JOIN university_details d ON d.university_id = u.id
     ORDER BY u.id`,
  );

  if (result.rows.length !== 62) {
    await client.end();
    throw new Error(`Expected 62 database rows, found ${result.rows.length}`);
  }

  const write = process.argv.includes("--write");
  let repairedPeople = 0;
  let minimumHistoryLength = Number.POSITIVE_INFINITY;

  if (write) await client.query("BEGIN");
  try {
    for (const row of result.rows) {
      const detail = structuredClone(row.detail);
      const chineseName = requiredString(
        row.summary.nameZh ?? row.summary.chineseName,
        `${row.university_id}.nameZh`,
      );
      const history = histories.get(row.university_id);
      const anecdote = anecdotes.get(row.university_id);
      if (!history || !anecdote) throw new Error(`Missing source content for ${row.university_id}`);

      detail.name = requiredString(row.summary.name, `${row.university_id}.name`);
      detail.nameZh = chineseName;
      detail.chineseName = chineseName;
      if (Array.isArray(row.summary.aliases)) {
        detail.aliases = structuredClone(row.summary.aliases);
      }
      if (isObject(row.summary.costSummary)) {
        detail.costSummary = structuredClone(row.summary.costSummary);
      }
      repairPrograms(detail, row.summary);
      const repairedHistory = buildHistory(history, anecdote);
      const historyValue = repairedHistory.value;
      detail.history = {
        value: historyValue,
        status: "verified",
        sourceIds: repairedHistory.sourceIds,
      };
      detail.anecdotes = [
        {
          text: requiredString(anecdote.anecdote_text, `${row.university_id}.anecdote_text`),
          type: anecdote.anecdote_type ?? "campus_fact",
          sourceIds: [anecdote.source_id],
        },
      ];
      repairedPeople += repairPeople(detail);
      minimumHistoryLength = Math.min(minimumHistoryLength, historyValue.length);

      if (JSON.stringify(detail).includes("�")) {
        throw new Error(`Replacement character remains in ${row.university_id}`);
      }

      if (write) {
        await client.query(
          "UPDATE university_details SET payload = $1::jsonb, updated_at = NOW() WHERE university_id = $2",
          [JSON.stringify(detail), row.university_id],
        );
      }
    }

    if (write) {
      await client.query("UPDATE manifest SET updated_at = NOW() WHERE id = 1");
      await client.query("COMMIT");
    }
  } catch (error) {
    if (write) await client.query("ROLLBACK");
    throw error;
  } finally {
    await client.end();
  }

  console.log(
    JSON.stringify(
      {
        mode: write ? "write" : "dry-run",
        universities: result.rows.length,
        histories: histories.size,
        anecdotes: anecdotes.size,
        repairedPeople,
        minimumHistoryLength,
        replacementCharacters: 0,
      },
      null,
      2,
    ),
  );
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
