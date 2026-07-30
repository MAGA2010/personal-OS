import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const mapShell = readFileSync(
  resolve(__dirname, "../../components/map/MapShell.tsx"),
  "utf8",
);

describe("public map backend request contract", () => {
  it("does not call the blocked region-detail endpoint when state schools come from summaries", () => {
    expect(mapShell).not.toContain("useRegionDetail");
    expect(mapShell).not.toContain("regionDetailState");
  });
});
