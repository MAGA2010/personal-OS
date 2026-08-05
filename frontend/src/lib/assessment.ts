export type AdmissionTier = "reach" | "target" | "safety";
export type RiskLevel = "low" | "medium" | "high" | "unknown";

export interface StudentProfile {
  background: string;
  targetDegree: string;
  targetMajor: string;
  gpa: number;
  toefl?: number;
  sat?: number;
  budgetRmb: number;
  priorities: Array<"employment" | "safety" | "recognition" | "cost" | "community">;
}

export interface AssessmentUniversity {
  id: string;
  rankingTier?: string;
  admissionRate?: number | null;
  annualCostRmb?: number | null;
  safetyScore?: number | null;
  chineseCommunity?: string | null;
  sat25?: number | null;
  sat75?: number | null;
}

export interface SchoolAssessment {
  universityId: string;
  tier: AdmissionTier;
  fitScore: number;
  admissionRisk: RiskLevel;
  costRisk: RiskLevel;
  safetyRisk: RiskLevel;
  environmentRisk: RiskLevel;
  reasons: string[];
  warnings: string[];
}

export interface PortfolioAssessment {
  summary: string;
  reachCount: number;
  targetCount: number;
  safetyCount: number;
  averageFitScore: number;
  majorRisks: string[];
  parentQuestions: string[];
  schools: SchoolAssessment[];
}

const TIER_SCORE: Record<string, number> = {
  top20: 1,
  top50: 0.7,
  top100: 0.4,
  other: 0.1,
};

function finiteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function normalizeAdmissionRate(value: unknown): number | null {
  const rate = finiteNumber(value);
  if (rate === null || rate < 0) return null;
  return rate <= 1 ? rate * 100 : rate;
}

function riskScore(risk: RiskLevel): number | null {
  if (risk === "low") return 1;
  if (risk === "medium") return 0.6;
  if (risk === "high") return 0.2;
  return null;
}

function weightedScore(dimensions: Array<{ score: number | null; weight: number }>): number {
  let weighted = 0;
  let totalWeight = 0;
  for (const dimension of dimensions) {
    if (dimension.score === null) continue;
    weighted += dimension.score * dimension.weight;
    totalWeight += dimension.weight;
  }
  return totalWeight > 0 ? Math.round((weighted / totalWeight) * 100) : 0;
}

function inferTier(rate: number | null, rankingTier: string | undefined): AdmissionTier {
  if (rate === null) return rankingTier === "top20" ? "reach" : "target";
  if (rate < 8) return "reach";
  if (rate < 20) return rankingTier === "top20" || rankingTier === "top50" ? "reach" : "target";
  if (rate < 45) return "target";
  return "safety";
}

export function assessSchoolFit(
  profile: StudentProfile,
  university: AssessmentUniversity,
): SchoolAssessment {
  const rate = normalizeAdmissionRate(university.admissionRate);
  const tierScore = TIER_SCORE[university.rankingTier ?? ""] ?? null;
  const tier = inferTier(rate, university.rankingTier);

  const cost = finiteNumber(university.annualCostRmb);
  const costRisk: RiskLevel = cost === null
    ? "unknown"
    : cost > profile.budgetRmb
      ? "high"
      : cost > profile.budgetRmb * 0.85
        ? "medium"
        : "low";

  const safety = finiteNumber(university.safetyScore);
  const safetyRisk: RiskLevel = safety === null
    ? "unknown"
    : safety < 65
      ? "high"
      : safety < 78
        ? "medium"
        : "low";

  const community = university.chineseCommunity;
  const environmentRisk: RiskLevel = safetyRisk === "unknown" || !community
    ? "unknown"
    : safetyRisk === "high" && community === "low"
      ? "high"
      : safetyRisk === "medium" && community === "low"
        ? "medium"
        : "low";

  const admissionRisk: RiskLevel = rate === null
    ? "unknown"
    : tier === "reach" && rate < 10
      ? "high"
      : tier === "reach" || tier === "target"
        ? "medium"
        : "low";

  const fitScore = weightedScore([
    { score: riskScore(admissionRisk), weight: 0.35 },
    { score: riskScore(costRisk), weight: 0.25 },
    { score: riskScore(safetyRisk), weight: 0.2 },
    { score: tierScore, weight: 0.15 },
    { score: riskScore(environmentRisk), weight: 0.05 },
  ]);

  const reasons: string[] = [];
  if (rate !== null) {
    if (tier === "safety") reasons.push("学校整体录取率相对较高，可作为保底候选，但不构成录取保证。");
    else if (tier === "target") reasons.push("学校整体录取率处于中间区间，可作为匹配候选继续核验专业难度。");
    else reasons.push("学校整体录取竞争激烈，当前更适合作为冲刺候选。");
  }
  if (costRisk === "low") reasons.push("当前收录学费在预算范围内；住宿、保险和生活费仍需另算。");
  else if (costRisk === "medium") reasons.push("当前收录学费接近预算上限，需要核算完整年度支出。");
  else if (costRisk === "high") reasons.push("当前收录学费高于预算上限，需要奖助学金或替代方案。");
  if (safetyRisk === "low") reasons.push("已收录的区域安全指标表现较好。");
  else if (safetyRisk === "high") reasons.push("已收录的区域安全指标偏低，需要核验具体校区与居住地。");
  if (environmentRisk !== "unknown" && environmentRisk !== "high") {
    reasons.push("当前区域社区数据未显示明显环境风险。");
  }

  const sat25 = finiteNumber(university.sat25);
  const sat75 = finiteNumber(university.sat75);
  if (profile.sat && sat25 !== null && sat75 !== null) {
    if (profile.sat < sat25) {
      reasons.push(`当前 SAT 低于该校已报告中间 50% 区间下沿 ${sat25}。`);
    } else if (profile.sat > sat75) {
      reasons.push(`当前 SAT 高于该校已报告中间 50% 区间上沿 ${sat75}。`);
    } else {
      reasons.push(`当前 SAT 位于该校已报告中间 50% 区间 ${sat25}–${sat75}。`);
    }
  }

  const warnings: string[] = [];
  if (rate === null) warnings.push("学校整体录取率未报告，冲刺/匹配标签仅按排名档次暂定。");
  if (tier === "reach") warnings.push("建议搭配录取更稳的匹配校和保底校，不把该校作为唯一核心选择。");
  if (costRisk === "unknown") warnings.push("学费数据未报告，评分已自动排除成本维度。");
  if (safetyRisk === "unknown") warnings.push("区域安全数据未接入，评分已自动排除安全维度。");
  if (environmentRisk === "unknown") warnings.push("华人社区或区域环境数据未接入，未对该维度作结论。");
  if (admissionRisk === "high") warnings.push("这里只使用学校整体录取率；目标专业的实际竞争可能更高，需单独核验。");

  return {
    universityId: university.id,
    tier,
    fitScore,
    admissionRisk,
    costRisk,
    safetyRisk,
    environmentRisk,
    reasons,
    warnings,
  };
}

export function assessPortfolio(
  profile: StudentProfile,
  universities: AssessmentUniversity[],
): PortfolioAssessment {
  const schools = universities.map((university) => assessSchoolFit(profile, university));
  const reachCount = schools.filter((school) => school.tier === "reach").length;
  const targetCount = schools.filter((school) => school.tier === "target").length;
  const safetyCount = schools.filter((school) => school.tier === "safety").length;
  const averageFitScore = schools.length > 0
    ? Math.round(schools.reduce((sum, school) => sum + school.fitScore, 0) / schools.length)
    : 0;
  const highCostCount = schools.filter((school) => school.costRisk === "high").length;
  const highSafetyCount = schools.filter((school) => school.safetyRisk === "high").length;
  const unknownCostCount = schools.filter((school) => school.costRisk === "unknown").length;
  const unknownSafetyCount = schools.filter((school) => school.safetyRisk === "unknown").length;

  const summaryParts: string[] = [];
  if (reachCount > Math.max(2, schools.length / 2)) summaryParts.push("冲刺校占比偏高，整体策略较激进。");
  else summaryParts.push("冲刺校比例基本可控。");
  if (safetyCount < 2) summaryParts.push("保底候选不足，建议至少补充 2 所并人工核验。");
  else summaryParts.push("保底候选数量达到基础要求。");
  if (highCostCount > 0) summaryParts.push(`${highCostCount} 所学校当前收录学费高于预算。`);
  if (unknownSafetyCount > 0) summaryParts.push("区域安全维度尚未进入评分，相关结论保持空缺。");

  const majorRisks: string[] = [];
  if (reachCount > Math.max(2, schools.length / 2)) majorRisks.push("冲刺校占比偏高");
  if (safetyCount < 2) majorRisks.push("保底候选不足");
  if (highCostCount > 0) majorRisks.push("部分学校学费超预算");
  if (highSafetyCount > 0) majorRisks.push("部分区域安全指标偏低");
  if (unknownCostCount > 0) majorRisks.push(`${unknownCostCount} 所学校缺少可比较学费`);
  if (unknownSafetyCount > 0) majorRisks.push("区域安全数据尚未接入评分");

  const parentQuestions: string[] = [
    "学校整体录取率与目标专业录取难度之间有多大差异？",
    "这份清单中哪些学校是真正的保底候选，依据是什么？",
    "学费之外的住宿、保险、交通和生活费分别是多少？",
    "如果预算超过上限，是否有奖学金或替代学校方案？",
    "标化与英语要求是否来自当前申请周期的官方本科页面？",
    "区域安全与华人社区数据何时完成核验？",
  ];

  return {
    summary: summaryParts.join(""),
    reachCount,
    targetCount,
    safetyCount,
    averageFitScore,
    majorRisks,
    parentQuestions,
    schools,
  };
}
