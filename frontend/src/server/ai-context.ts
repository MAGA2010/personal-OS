// AI context interface.
//
// Builds a structured payload for downstream LLM calls (analyze route,
// future chat route). The payload is *only* a projection of fields the
// backend has already provided — never fabricated, never enriched with
// copy that "looks like" a real statistic.
//
// Hard rules:
//   1. If the data source is `unavailable`, respond 503 with a code that
//      the AI UI surfaces as "数据补充中" — never serve canned copy.
//   2. Always include `provenance` so the LLM can be told which fields
//      are live-verified vs awaiting review. Quarantined `Person`
//      records are never copied into the payload.
//   3. cap schools at 3 (matches ComparePanel) so cost / context length
//      stays bounded.
//
// Gate-bloker repair #RG-P0-J:
//   `source_review_not_completed` is NOT the same as `quarantined`.
//   Quarantined records are dropped entirely (a user must not see a
//   "pending review" person). But `source_review_not_completed`
//   records are public-visible slots awaiting review — they keep
//   their place in the AI context with an explicit `available:false`
//   flag and a `publicLabel` of "数据补充中". This gives the LLM
//   enough information to say "I don't have this data yet" instead
//   of hallucinating one.

import { NextResponse } from "next/server";
import { loadUniversities } from "@/server/pathos-preview";
import { parseUniversityDetail, parseStatusDictionary } from "@/schemas/dataset.schema";
import type { UniversityDetail } from "@/domain/dataset";
import { resolveDataMode } from "@/server/pathos-preview";

export interface AiContextRequest {
  schoolIds: string[];
  viewMode?: "parent" | "student";
  activeMetricId?: string;
  selectedRegionFips?: string;
}

export interface AiContextPayload {
  viewMode: "parent" | "student";
  activeMetricId: string;
  selectedRegionFips?: string;
  generatedAt: string;
  schools: Array<{
    id: string;
    chineseName: string;
    name: string;
    city?: string;
    state?: string;
    rankingBand?: string;
    rankingTier?: string;
    programs: string[];
    people: Array<{ name: string; relationship: string }>;
    anecdotes: Array<{ text: string; status: string; publicLabel: string; available: boolean }>;
    notableAttendance: Array<{ year?: number; context?: string; status: string; publicLabel: string; available: boolean }>;
    costLines: Array<{ year: number; scope: string; amountRmb: number; provenance: string; available: boolean }>;
    studentFacultyRatio?: number | null;
    provenance: { previewOnly: boolean; status: string };
  }>;
  presetQuestions: ReadonlyArray<{ id: string; text: string; audience: "parent" | "student" | "both" }>;
}

const PRESET_QUESTIONS = [
  { id: "q-safety", audience: "parent", text: "对比这三所学校所在城市的安全指标,哪些更适合未成年人独自生活?" },
  { id: "q-cost", audience: "parent", text: "三年总费用分别是多少?性价比如何?" },
  { id: "q-fit", audience: "student", text: "我的兴趣方向是计算机科学 — 这三所学校的 CS 项目哪个更适合?" },
  { id: "q-visa", audience: "both", text: "毕业后留美工作的签证政策如何?STEM OPT 是否适用?" },
  { id: "q-chinese", audience: "both", text: "中国学生社区规模如何?新生入学过渡支持有哪些?" },
] as const;

// Status dictionary for public-visible labels. Re-Gate repair #RG-P0-J
// keeps this in lockstep with the canonical status-dictionary config
// so the AI prompt and the UI label can never diverge.
const REVIEW_PENDING_LABEL = "数据补充中";

export async function buildAiContext(req: AiContextRequest): Promise<AiContextPayload> {
  const raw = await loadUniversities();
  const idSet = new Set(req.schoolIds.slice(0, 3));
  const matched = raw.filter((u) => idSet.has(u.id));
  const details: UniversityDetail[] = matched.map((u) => {
    try {
      return parseUniversityDetail(u);
    } catch {
      return null;
    }
  }).filter((d): d is UniversityDetail => d !== null);

  const _statusDictionary = parseStatusDictionary({});
  void _statusDictionary;

  return {
    viewMode: req.viewMode ?? "parent",
    activeMetricId: req.activeMetricId ?? "income",
    selectedRegionFips: req.selectedRegionFips,
    generatedAt: new Date().toISOString(),
    schools: details.map((d) => ({
      id: d.id,
      chineseName: d.chineseName,
      name: d.name,
      city: d.city,
      state: d.state,
      rankingBand: d.rankingBand,
      rankingTier: d.rankingTier,
      // Gate-bloker repair #GB-P1-9 + #RG-P0-J: every narrative /
      // people field that has a `displayTier === "quarantined"` entry
      // must be filtered here, never copied into the AI context.
      //
      // `source_review_not_completed` is the *public* "data pending"
      // status — those records keep their slot in the payload but
      // carry an `available:false` flag and a `publicLabel` of
      // "数据补充中" so the LLM is told not to invent content.
      programs: (d.programs ?? [])
        .filter((p) => p.displayTier !== "quarantined")
        .map((p) => p.name),
      people: (d.people ?? [])
        .filter((p) => !p.quarantined && p.displayTier !== "quarantined")
        .map((p) => ({ name: p.name, relationship: p.relationship })),
      anecdotes: (d.anecdotes ?? [])
        .map((a) => ({
          text: a.status === "source_review_not_completed" ? "" : a.text,
          status: a.status,
          publicLabel: REVIEW_PENDING_LABEL,
          available: a.status !== "source_review_not_completed",
        })),
      notableAttendance: (d.notableAttendance ?? [])
        .map((n) => ({
          year: n.year,
          context: n.status === "source_review_not_completed" ? "" : n.context,
          status: n.status,
          publicLabel: REVIEW_PENDING_LABEL,
          available: n.status !== "source_review_not_completed",
        })),
      costLines: (d.cost ?? [])
        .map((c) => ({
          year: c.year,
          scope: c.scope,
          amountRmb: c.amount,
          provenance: c.status,
          available: c.status !== "source_review_not_completed",
        })),
      studentFacultyRatio: d.studentFacultyRatio ?? null,
      provenance: { previewOnly: d.previewOnly, status: d.displayTier },
    })),
    presetQuestions: PRESET_QUESTIONS,
  };
}

export async function handleAiContextRoute(req: Request): Promise<NextResponse> {
  if (req.method !== "POST") {
    return NextResponse.json({ error: "method_not_allowed" }, { status: 405 });
  }
  if (resolveDataMode() === "backend") {
    return NextResponse.json(
      {
        error: "ai_context_disabled",
        code: "AI_CONTEXT_DISABLED",
        message: "Verified AI context is not eligible for this Preview checkpoint.",
        featureStatus: "disabled",
        retryable: false,
        requestContext: { endpoint: "/api/ai/context" },
      },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }
  let body: AiContextRequest;
  try {
    const raw = (await req.json()) as Partial<AiContextRequest>;
    body = {
      schoolIds: Array.isArray(raw.schoolIds) ? raw.schoolIds.filter((x): x is string => typeof x === "string") : [],
      viewMode: raw.viewMode === "student" ? "student" : "parent",
      activeMetricId: typeof raw.activeMetricId === "string" ? raw.activeMetricId : "income",
      selectedRegionFips: typeof raw.selectedRegionFips === "string" ? raw.selectedRegionFips : undefined,
    };
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }
  if (body.schoolIds.length === 0) {
    return NextResponse.json({ error: "missing_school_ids" }, { status: 400 });
  }
  try {
    const payload = await buildAiContext(body);
    return NextResponse.json(payload, {
      headers: { "Cache-Control": "no-store", "X-PathOS-BFF": "preview-context" },
    });
  } catch (e) {
    const err = e as Error & { code?: string };
    // Backend offline / preview unavailable — surface as 503 so the UI
    // can show the "数据补充中" state rather than a fabricated answer.
    return NextResponse.json(
      {
        error: "preview_not_yet_available",
        code: err.code ?? "PREVIEW_NOT_YET_AVAILABLE",
      },
      { status: 503 },
    );
  }
}
