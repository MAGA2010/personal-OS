import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(__dirname, "../../..");
const read = (path: string) => readFileSync(resolve(ROOT, path), "utf8");

describe("home module flip cards", () => {
  it("uses one flip card for each of the six existing modules", () => {
    const home = read("src/app/page.tsx");
    expect(home).toContain("FlipModuleCard");
    expect(home).toContain("CORE_MODULES.map");
    expect(home).toContain("reveal={module.reveal}");
    expect(home).not.toContain("<Link key={module.href} href={module.href}");
  });

  it("keeps click, keyboard, route, and accessibility behavior explicit", () => {
    const component = read("src/components/home/FlipModuleCard.tsx");
    expect(component).toContain('"use client"');
    expect(component).toContain("useState(false)");
    expect(component).toContain('event.key === "Escape"');
    expect(component).toContain("aria-pressed={flipped}");
    expect(component).toContain("href={href}");
    expect(component).toContain("翻回正面");
  });

  it("uses a real 3D flip with a reduced-motion fallback", () => {
    const css = read("src/app/home.module.css");
    expect(css).toContain("perspective:");
    expect(css).toContain("transform-style: preserve-3d");
    expect(css).toContain("backface-visibility: hidden");
    expect(css).toContain("rotateY(180deg)");
    expect(css).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/);
  });
});
