import { existsSync, readFileSync, statSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(__dirname, "../../..");

function read(relativePath: string): string {
  return readFileSync(resolve(ROOT, relativePath), "utf8");
}

const ENTRY_ROUTES = {
  map: {
    component: "MapEntry",
    target: "/map",
  },
  match: {
    component: "MatchEntry",
    target: "/match",
  },
  assessment: {
    component: "AssessmentEntry",
    target: "/assessment",
  },
  portfolio: {
    component: "PortfolioEntry",
    target: "/portfolio",
  },
} as const;

describe("feature entry restoration routes", () => {
  for (const [entry, contract] of Object.entries(ENTRY_ROUTES)) {
    it(`mounts ${contract.component} at /entry/${entry}`, () => {
      const route = read(`src/app/entry/${entry}/page.tsx`);
      expect(route).toContain(`@/components/entry/${contract.component}`);
      expect(route).toContain(`<${contract.component} />`);
    });

    it(`${contract.component} enters the existing canonical ${contract.target} route`, () => {
      const component = read(`src/components/entry/${contract.component}.tsx`);
      const chrome = read("src/components/entry/EntryChrome.tsx");
      expect(component).toContain(`href="${contract.target}"`);
      expect(component).not.toContain("/explore");
      expect(component).not.toMatch(/universities\.json|PATHOS_DATA_MODE\s*=\s*["']fixture["']/);
      expect(component.match(/<h1\b/g) ?? []).toHaveLength(1);
      expect(chrome).toContain('href="/"');
    });
  }

  it("routes only the four restored home entries through entry pages", () => {
    const home = read("src/app/page.tsx");
    for (const entry of Object.keys(ENTRY_ROUTES)) {
      expect(home).toContain(`href: "/entry/${entry}"`);
    }
    expect(home).toContain('href: "/calculator"');
    expect(home).toContain('href: "/news"');
    expect(home).toContain('href="/entry/map"');
    expect(home).toContain('href="/entry/match"');
  });

  it("routes the primary navigation and footer through every restored entry experience", () => {
    const navigation = read("src/components/NavBar.tsx");
    const footer = read("src/components/Footer.tsx");

    for (const entry of Object.keys(ENTRY_ROUTES)) {
      expect(navigation).toContain(`href: "/entry/${entry}"`);
      expect(footer).toContain(`href="/entry/${entry}"`);
    }

    expect(navigation).toContain('href: "/calculator"');
    expect(navigation).toContain('href: "/news"');
    expect(footer).toContain('href="/calculator"');
    expect(footer).toContain('href="/news"');
  });

  it("keeps the canonical feature pages unwrapped and directly addressable", () => {
    const mapPage = read("src/app/map/page.tsx");
    expect(mapPage).toContain("return <MapPageShell />");
    expect(mapPage).not.toContain("MapEntry");

    for (const route of ["match", "assessment", "portfolio"]) {
      const page = read(`src/app/${route}/page.tsx`);
      expect(page).not.toMatch(/components\/entry|EntryGate|\/entry\//);
    }
  });
});

describe("feature entry restoration media and motion safety", () => {
  it("uses the verified local NASA image and local licensed campus photography", () => {
    const earthPath = resolve(ROOT, "public/entry/pathos-earth-from-orbit.jpg");
    expect(existsSync(earthPath)).toBe(true);
    expect(statSync(earthPath).size).toBeGreaterThan(100_000);

    const map = read("src/components/entry/MapEntry.tsx");
    const assessment = read("src/components/entry/AssessmentEntry.tsx");
    expect(map).toContain("/entry/pathos-earth-from-orbit.jpg");
    for (const image of [
      "/news/campus/harvard-yard.webp",
      "/news/campus/mit-great-dome.webp",
      "/news/campus/stanford-main-quad.webp",
    ]) {
      expect(assessment).toContain(image);
    }
  });

  it("does not restore unknown robot or candidate campus assets", () => {
    const sources = Object.values(ENTRY_ROUTES)
      .map(({ component }) => read(`src/components/entry/${component}.tsx`))
      .join("\n");

    expect(sources).not.toMatch(
      /portfolio-robot-cutout|harvard-library\.jpg|mit-dome\.jpg|stanford-quad\.jpg/,
    );
    expect(sources).not.toMatch(/https?:\/\//);
    expect(sources).not.toMatch(/data:image\/(?:jpeg|png|webp)/);
  });

  it("preserves explicit NASA attribution for the earth image", () => {
    const attribution = read("public/entry/ATTRIBUTIONS.md");
    expect(attribution).toContain("S131-E-006087");
    expect(attribution).toContain("NASA");
    expect(attribution).toMatch(/Public Domain|公共领域/);
    expect(attribution).toMatch(/[a-f0-9]{64}/);
  });

  it("provides reduced-motion fallbacks for every entry and the home environment", () => {
    const styles = [
      "src/components/entry/EntryChrome.module.css",
      "src/components/entry/MapEntry.module.css",
      "src/components/entry/MatchEntry.module.css",
      "src/components/entry/AssessmentEntry.module.css",
      "src/components/entry/PortfolioEntry.module.css",
      "src/app/home.module.css",
    ];

    for (const stylesheet of styles) {
      expect(read(stylesheet), stylesheet).toMatch(
        /@media\s*\(prefers-reduced-motion:\s*reduce\)/,
      );
    }
  });

  it("keeps decorative environment layers non-interactive", () => {
    const styles = [
      "src/components/entry/EntryChrome.module.css",
      "src/components/entry/MapEntry.module.css",
      "src/components/entry/MatchEntry.module.css",
      "src/components/entry/AssessmentEntry.module.css",
      "src/components/entry/PortfolioEntry.module.css",
      "src/app/home.module.css",
    ]
      .map(read)
      .join("\n");

    expect(styles.match(/pointer-events:\s*none/g)?.length ?? 0).toBeGreaterThanOrEqual(5);
  });

  it("keeps shared entry actions visible in the viewport without wrapping feature pages", () => {
    const chrome = read("src/components/entry/EntryChrome.module.css");
    expect(chrome).toMatch(/\.header,\s*\n\.footer\s*\{\s*\n\s*position:\s*fixed/);
    expect(chrome).toContain(":has(.root)");
  });

  it("keeps animation keyframes compositor-only", () => {
    const styles = [
      "src/components/entry/EntryChrome.module.css",
      "src/components/entry/MapEntry.module.css",
      "src/components/entry/MatchEntry.module.css",
      "src/components/entry/AssessmentEntry.module.css",
      "src/components/entry/PortfolioEntry.module.css",
      "src/app/home.module.css",
    ]
      .map(read)
      .join("\n");

    const blocks = styles.match(/@keyframes[\s\S]*?\n\}/g) ?? [];
    expect(blocks.length).toBeGreaterThanOrEqual(8);
    for (const block of blocks) {
      expect(block).not.toMatch(/\b(width|height|top|left|right|bottom|margin|padding)\s*:/);
    }
  });
});
