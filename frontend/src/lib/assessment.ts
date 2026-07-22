export type AdmissionTier = "reach" | "target" | "safety";
export type RiskLevel = "low" | "medium" | "high";

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
  top20: 1.0,
  top50: 0.7,
  top100: 0.4,
  other: 0.1,
};

export function assessSchoolFit(profile: StudentProfile, university: any): SchoolAssessment {
  const rate = university.admissionRate ?? 50;
  const tierScore = TIER_SCORE[university.rankingTier] ?? 0.1;
  let tier: AdmissionTier;
  if (rate < 8) tier = "reach";
  else if (rate < 20) tier = tierScore >= 0.7 ? "reach" : "target";
  else if (rate < 45) tier = "target";
  else tier = "safety";

  let costRisk: RiskLevel;
  const cost = university.annualCostRmb ?? 999999;
  if (cost > profile.budgetRmb) costRisk = "high";
  else if (cost > profile.budgetRmb * 0.85) costRisk = "medium";
  else costRisk = "low";

  const safety = university.safetyScore ?? 70;
  let safetyRisk: RiskLevel;
  if (safety < 65) safetyRisk = "high";
  else if (safety < 78) safetyRisk = "medium";
  else safetyRisk = "low";

  const comm = university.chineseCommunity ?? "medium";
  let envRisk: RiskLevel;
  if (safetyRisk === "high" && comm === "low") envRisk = "high";
  else if (safetyRisk === "medium" && comm === "low") envRisk = "medium";
  else envRisk = "low";

  let admissionRisk: RiskLevel;
  if (tier === "reach" && rate < 10) admissionRisk = "high";
  else if (tier === "reach") admissionRisk = "medium";
  else admissionRisk = "low";

  const costScore = costRisk === "low" ? 1 : costRisk === "medium" ? 0.6 : 0.2;
  const safetyScore = safetyRisk === "low" ? 1 : safetyRisk === "medium" ? 0.6 : 0.2;
  const admitScore = admissionRisk === "low" ? 1 : admissionRisk === "medium" ? 0.6 : 0.2;
  const rankScore = tierScore;
  const envScore = envRisk === "low" ? 1 : envRisk === "medium" ? 0.6 : 0.2;
  const fitScore = Math.round(
    (admitScore * 0.3 + costScore * 0.25 + safetyScore * 0.2 + rankScore * 0.15 + envScore * 0.1) * 100
  );

  const reasons: string[] = [];
  if (tier === "safety") reasons.push("该校录取率较高，适合作为保底选择。");
  else if (tier === "target") reasons.push("该校录取率适中，匹配当前学生水平。");
  else reasons.push("该校录取竞争激烈，适合作为冲刺目标。");
  if (costRisk === "low") reasons.push("年度费用在预算范围内，经济压力可控。");
  else reasons.push("费用较高，需提前评估四年总支出。");
  if (safetyRisk !== "high") reasons.push("所在城市安全状况良好，家长可放心。");
  else reasons.push("周边安全风险较高，建议关注具体社区情况。");
  if (envRisk !== "high") reasons.push("华人社区与生活便利度基本满足需求。");

  const warnings: string[] = [];
  if (tier === "reach") warnings.push("不建议作为主申核心，建议搭配匹配校使用。");
  if (costRisk === "high") warnings.push("年度费用超出预算上限，若无法获得奖学金将带来较大经济压力。");
  if (safetyRisk === "high") warnings.push("安全指数偏低，建议仔细了解校区周边环境。");
  if (admissionRisk === "high") warnings.push("该专业方向竞争激烈，录取不确定性较高。");

  return {
    universityId: university.id,
    tier,
    fitScore,
    admissionRisk,
    costRisk,
    safetyRisk,
    environmentRisk: envRisk,
    reasons,
    warnings,
  };
}

export function assessPortfolio(profile: StudentProfile, universities: any[]): PortfolioAssessment {
  const schools = universities.map((u) => assessSchoolFit(profile, u));
  const reachCount = schools.filter((s) => s.tier === "reach").length;
  const targetCount = schools.filter((s) => s.tier === "target").length;
  const safetyCount = schools.filter((s) => s.tier === "safety").length;
  const avgFit = Math.round(schools.reduce((s, x) => s + x.fitScore, 0) / schools.length);

  const parts: string[] = [];
  if (reachCount > 4) parts.push("冲刺校占比偏高，整体选校策略偏激进。");
  else if (reachCount <= 2) parts.push("冲刺校数量适中。");
  if (safetyCount < 2) parts.push("保底校不足，建议增加保底选择。");
  else parts.push("保底校数量合理。");
  const highCostCount = schools.filter((s) => s.costRisk === "high").length;
  if (highCostCount > 5) parts.push("多所学校费用超出预算，建议关注奖学金或替换方案。");
  const highSafetyCount = schools.filter((s) => s.safetyRisk === "high").length;
  if (highSafetyCount > 2) parts.push("部分学校所在城市安全风险偏高，建议仔细评估。");
  const summary = parts.join("");

  const majorRisks: string[] = [];
  if (reachCount > 4) majorRisks.push("冲刺校占比偏高，缺乏明确保底");
  if (safetyCount < 2) majorRisks.push("保底不足");
  if (highCostCount > 3) majorRisks.push("成本超预算的学校较多");
  if (highSafetyCount > 2) majorRisks.push("部分城市安全风险偏高");

  const parentQuestions: string[] = [
    "这所学校过去是否有与我孩子背景相近的录取案例？",
    "推荐该校是因为专业匹配，还是因为排名更好看？",
    "这份选校表中哪几所是真正保底？依据是什么？",
    "如果预算超过上限，是否有奖学金或替代学校方案？",
    "该专业录取难度是否高于学校整体录取率？",
    "这些学校的地理分布是否合理？是否集中在高成本区域？",
  ];

  return {
    summary,
    reachCount,
    targetCount,
    safetyCount,
    averageFitScore: avgFit,
    majorRisks,
    parentQuestions,
    schools,
  };
}
