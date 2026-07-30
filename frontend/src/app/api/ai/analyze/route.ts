import { NextResponse } from "next/server";
import { assessPortfolio, type StudentProfile } from "@/lib/assessment";
import { loadUniversities } from "@/server/pathos-preview";
import { resolveDataMode } from "@/server/pathos-preview";

type AnalyzeMode = "school_assessment" | "portfolio_review";
type AiProvider = "deepseek" | "custom";

interface AnalyzeRequest {
  mode: AnalyzeMode;
  profile?: Partial<StudentProfile> & Record<string, unknown>;
  schools?: Array<{ id?: string; name?: string; chineseName?: string }>;
  notes?: string;
}

async function loadAllUniversities() {
  return loadUniversities();
}

function selectedSchoolSnapshot(schools: ReturnType<typeof resolveSchoolsSync>) {
  // Gate-bloker repair #RG-P0-I: never coerce missing numeric fields
  // into 0. Downstream AI must see `null` plus the per-field
  // availability flag so it doesn't fabricate ¥0 schools or 0/100
  // safety scores into its recommendation. We also pass the
  // canonical `displayTier` so the LLM can decide whether to talk
  // about a record or to mark it "数据补充中".
  return schools.map((school) => ({
    id: school.id,
    name: school.name,
    chineseName: school.chineseName,
    city: school.city,
    state: school.state,
    rankingTier: school.rankingTier,
    annualCostRmb:
      typeof school.annualCostRmb === "number" && Number.isFinite(school.annualCostRmb)
        ? school.annualCostRmb
        : null,
    safetyScore:
      typeof school.safetyScore === "number" && Number.isFinite(school.safetyScore)
        ? school.safetyScore
        : null,
    recognitionScore:
      typeof school.recognitionScore === "number" && Number.isFinite(school.recognitionScore)
        ? school.recognitionScore
        : null,
    chineseCommunity: school.chineseCommunity ?? null,
    programs: school.programs,
    parentHighlights: school.parentHighlights,
    studentHighlights: school.studentHighlights,
    displayTier: school.displayTier ?? "preview",
    nullableFields: Array.isArray(school.nullableFields) ? school.nullableFields : [],
  }));
}

function toProfile(input: AnalyzeRequest["profile"]): StudentProfile {
  const budget = Number(input?.budgetRmb ?? input?.budget ?? 500000);
  const priorities = Array.isArray(input?.priorities) && input?.priorities.length > 0
    ? input.priorities
    : ["employment", "safety", "recognition", "cost", "community"];

  return {
    background: String(input?.background ?? input?.grade ?? "未填写"),
    targetDegree: String(input?.targetDegree ?? "bachelor"),
    targetMajor: String(input?.targetMajor ?? "Undecided"),
    gpa: Number(input?.gpa ?? 3.6),
    toefl: input?.toefl ? Number(input.toefl) : undefined,
    sat: input?.sat ? Number(input.sat) : undefined,
    budgetRmb: budget > 1000 ? budget : budget * 10000,
    priorities: priorities as StudentProfile["priorities"],
  };
}

function resolveSchoolsSync(
  universities: any[],
  schools: AnalyzeRequest["schools"] = [],
) {
  const ids = new Set(schools.map((school) => school.id).filter(Boolean));
  const names = new Set(
    schools
      .flatMap((school) => [school.name, school.chineseName])
      .filter(Boolean)
      .map((name) => String(name).toLowerCase())
  );

  const matched = universities.filter((university) => {
    return ids.has(university.id) || names.has(String(university.name).toLowerCase()) || names.has(String(university.chineseName).toLowerCase());
  });

  return matched.length > 0 ? matched : universities.slice(0, 8);
}

async function buildDeterministicAnalysis(payload: AnalyzeRequest) {
  const profile = toProfile(payload.profile);
  const universities = await loadAllUniversities();
  const schools = resolveSchoolsSync(universities, payload.schools);
  const portfolio = assessPortfolio(profile, schools);
  const sorted = portfolio.schools
    .map((assessment) => ({
      ...assessment,
      university: schools.find((school) => school.id === assessment.universityId),
    }))
    .sort((a, b) => b.fitScore - a.fitScore);

  const recommended = sorted.slice(0, 3).map((item) => ({
    id: item.universityId,
    name: item.university?.name,
    chineseName: item.university?.chineseName,
    fitScore: item.fitScore,
    tier: item.tier,
    reasons: item.reasons.slice(0, 2),
    warnings: item.warnings.slice(0, 2),
  }));

  const nextActions = [
    portfolio.reachCount > portfolio.safetyCount ? "补充 2 所录取更稳、成本更可控的保底校。" : "保留当前冲刺/匹配/保底比例，并继续核验专业录取要求。",
    "把目标专业、预算上限和地理偏好作为下一轮筛选的硬条件。",
    "对高成本学校单独确认奖学金、实习收入和四年总支出。",
  ];

  return {
    source: "local-model",
    mode: payload.mode,
    summary: portfolio.summary || "当前清单结构基本可用，但仍需要补充学生背景与专业方向后再做最终判断。",
    profile,
    portfolio: {
      reachCount: portfolio.reachCount,
      targetCount: portfolio.targetCount,
      safetyCount: portfolio.safetyCount,
      averageFitScore: portfolio.averageFitScore,
      majorRisks: portfolio.majorRisks,
      parentQuestions: portfolio.parentQuestions.slice(0, 5),
    },
    recommended,
    nextActions,
  };
}

async function buildDeepSeekPrompt(payload: AnalyzeRequest, deterministic: Awaited<ReturnType<typeof buildDeterministicAnalysis>>) {
  const universities = await loadAllUniversities();
  const schools = resolveSchoolsSync(universities, payload.schools);
  return JSON.stringify({
    role: "PathOS 留学选校 AI 分析师",
    instruction: [
      "面向中国家庭，用简洁、克制、可执行的中文输出。",
      "只能基于输入的学生画像、学校数据和 localBaseline 推理；不要编造未提供的数据、录取案例或政策细节。",
      "任何字段缺失（值为 null 或不在 nullableFields 之外缺失）一律视为“数据补充中”，不要推断为 0、不要把 null 当作 0。",
      "不要把 annualCostRmb 为 null 的学校说成“免费”或“免学费”；这是缺失数据。",
      "不要把 safetyScore / recognitionScore 为 null 的学校说成“0/100 安全”或“0/100 认可度”；这是缺失数据。",
      "必须返回合法 JSON，不要使用 Markdown，不要包裹代码块。",
      "JSON 字段必须包含 summary、majorRisks、parentQuestions、recommended、nextActions、unknowns。",
      "recommended 中每项包含 id、chineseName、fitScore、tier、reasons、warnings。",
      "如果证据不足，把不确定项写入 unknowns。",
    ],
    mode: payload.mode,
    profile: deterministic.profile,
    schools: selectedSchoolSnapshot(schools),
    localBaseline: deterministic,
    notes: payload.notes,
  });
}

function parseAiJson(content: string) {
  const cleaned = content.trim().replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/```$/i, "").trim();
  return JSON.parse(cleaned) as Record<string, any>;
}

async function callDeepSeek(payload: AnalyzeRequest, deterministic: Awaited<ReturnType<typeof buildDeterministicAnalysis>>) {
  const apiKey = process.env.DEEPSEEK_API_KEY ?? process.env.PATHOS_AI_API_KEY;
  if (!apiKey) return deterministic;

  const baseUrl = process.env.DEEPSEEK_BASE_URL ?? "https://api.deepseek.com";
  const model = process.env.DEEPSEEK_MODEL ?? "deepseek-chat";
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      temperature: 0.2,
      response_format: { type: "json_object" },
      messages: [
        {
          role: "system",
          content: "你是 PathOS 的留学选校分析引擎。你输出严格 JSON，提供可追问、可复核、不过度承诺的分析。",
        },
        {
          role: "user",
          content: buildDeepSeekPrompt(payload, deterministic),
        },
      ],
    }),
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`DeepSeek request failed: ${response.status}${detail ? ` ${detail.slice(0, 180)}` : ""}`);
  }

  const data = await response.json();
  const content = data?.choices?.[0]?.message?.content;
  if (!content) throw new Error("DeepSeek returned empty content");

  const ai = parseAiJson(content);

  return {
    ...deterministic,
    source: "deepseek",
    summary: typeof ai.summary === "string" ? ai.summary : deterministic.summary,
    portfolio: {
      ...deterministic.portfolio,
      majorRisks: Array.isArray(ai.majorRisks) ? ai.majorRisks : deterministic.portfolio.majorRisks,
      parentQuestions: Array.isArray(ai.parentQuestions) ? ai.parentQuestions : deterministic.portfolio.parentQuestions,
    },
    recommended: Array.isArray(ai.recommended) ? ai.recommended : deterministic.recommended,
    nextActions: Array.isArray(ai.nextActions) ? ai.nextActions : deterministic.nextActions,
    ai: {
      provider: "deepseek",
      model,
      unknowns: Array.isArray(ai.unknowns) ? ai.unknowns : [],
      raw: ai,
    },
  };
}

async function callCustomEndpoint(payload: AnalyzeRequest, deterministic: Awaited<ReturnType<typeof buildDeterministicAnalysis>>) {
  const endpoint = process.env.PATHOS_AI_ENDPOINT;
  const apiKey = process.env.PATHOS_AI_API_KEY;

  if (!endpoint) return deterministic;

  const universities = await loadAllUniversities();
  const schools = resolveSchoolsSync(universities, payload.schools);

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
    },
    body: JSON.stringify({
      task: payload.mode,
      profile: deterministic.profile,
      schools: selectedSchoolSnapshot(schools),
      localBaseline: deterministic,
      notes: payload.notes,
    }),
  });

  if (!response.ok) {
    throw new Error(`AI endpoint failed: ${response.status}`);
  }

  return {
    ...deterministic,
    source: "external-ai",
    ai: await response.json(),
  };
}

async function callExternalAi(payload: AnalyzeRequest, deterministic: Awaited<ReturnType<typeof buildDeterministicAnalysis>>) {
  const provider = (process.env.AI_PROVIDER ?? "deepseek") as AiProvider;
  if (provider === "custom") return callCustomEndpoint(payload, deterministic);
  return callDeepSeek(payload, deterministic);
}

export async function POST(request: Request) {
  if (resolveDataMode() === "backend") {
    return NextResponse.json(
      {
        error: "ai_context_disabled",
        code: "AI_CONTEXT_DISABLED",
        featureStatus: "disabled",
        retryable: false,
      },
      { status: 503 },
    );
  }
  try {
    const payload = (await request.json()) as AnalyzeRequest;
    if (payload.mode !== "school_assessment" && payload.mode !== "portfolio_review") {
      return NextResponse.json({ error: "Unsupported analysis mode" }, { status: 400 });
    }

    const deterministic = await buildDeterministicAnalysis(payload);
    const result = await callExternalAi(payload, deterministic);

    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "AI analysis failed" },
      { status: 500 }
    );
  }
}
