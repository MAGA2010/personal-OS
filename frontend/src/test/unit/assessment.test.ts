import { describe, expect, it } from "vitest";

import {
  assessPortfolio,
  assessSchoolFit,
  type AssessmentUniversity,
  type StudentProfile,
} from "@/lib/assessment";

const profile: StudentProfile = {
  background: "中国高中学生",
  targetDegree: "bachelor",
  targetMajor: "Computer Science",
  gpa: 3.8,
  sat: 1510,
  budgetRmb: 550000,
  priorities: ["cost", "recognition"],
};

function university(overrides: Partial<AssessmentUniversity> = {}): AssessmentUniversity {
  return {
    id: "candidate-v2:test-university",
    rankingTier: "top50",
    admissionRate: 25,
    annualCostRmb: 400000,
    safetyScore: null,
    chineseCommunity: null,
    sat25: 1450,
    sat75: 1530,
    ...overrides,
  };
}

describe("assessment missing-data policy", () => {
  it("keeps missing dimensions unknown instead of fabricating defaults", () => {
    const result = assessSchoolFit(
      profile,
      university({ admissionRate: null, annualCostRmb: null }),
    );

    expect(result.admissionRisk).toBe("unknown");
    expect(result.costRisk).toBe("unknown");
    expect(result.safetyRisk).toBe("unknown");
    expect(result.environmentRisk).toBe("unknown");
    expect(result.warnings).toContain("学费数据未报告，评分已自动排除成本维度。");
    expect(result.warnings).toContain("区域安全数据未接入，评分已自动排除安全维度。");
    expect(result.fitScore).toBeGreaterThan(0);
  });

  it("uses verified admission, tuition, and SAT values when present", () => {
    const result = assessSchoolFit(profile, university());

    expect(result.tier).toBe("target");
    expect(result.admissionRisk).toBe("medium");
    expect(result.costRisk).toBe("low");
    expect(result.reasons).toContain("当前 SAT 位于该校已报告中间 50% 区间 1450–1530。");
    expect(result.warnings).not.toContain("学费数据未报告，评分已自动排除成本维度。");
  });

  it("reports portfolio-wide unknown regional data", () => {
    const result = assessPortfolio(profile, [
      university({ id: "reach", admissionRate: 4 }),
      university({ id: "safety", admissionRate: 70, rankingTier: "other" }),
    ]);

    expect(result.reachCount).toBe(1);
    expect(result.safetyCount).toBe(1);
    expect(result.majorRisks).toContain("区域安全数据尚未接入评分");
    expect(result.averageFitScore).toBeGreaterThan(0);
  });
});
