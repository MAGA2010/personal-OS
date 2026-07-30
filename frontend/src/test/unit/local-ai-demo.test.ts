import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(__dirname, "../../..");
const read = (path: string) => readFileSync(resolve(ROOT, path), "utf8");

describe("local AI preview demos", () => {
  for (const route of ["assessment", "portfolio"]) {
    it(`${route} shows an explicit local demo without calling the disabled AI endpoint`, () => {
      const page = read(`src/app/${route}/page.tsx`);
      expect(page).toContain('source: "本地 Demo 示例"');
      expect(page).toContain("非真实 AI 结论");
      expect(page).toContain("averageFitScore: null");
      expect(page).not.toContain('fetch("/api/ai/analyze"');
    });
  }

  it("keeps demo output free of fabricated admissions scores", () => {
    const sources = ["assessment", "portfolio"]
      .map((route) => read(`src/app/${route}/page.tsx`))
      .join("\n");
    expect(sources).toContain("示例不评分");
    expect(sources).toContain("—");
    expect(sources).not.toContain("demoFitScore");
  });
});
