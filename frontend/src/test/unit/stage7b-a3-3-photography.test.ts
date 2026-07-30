// Stage 7B-A.3.3 — News Entry Hero color reconciliation &
// real campus photography integration tests.
//
// Source-text + token-shape assertions covering:
//   - 9 real local image paths (no inline SVG, no remote URL)
//   - New ink-green-grey palette (no brown bias, no pure black)
//   - ATTRIBUTIONS.md + LICENSES.json schema integrity
//   - 9 fallback SVGs (quiet solid colors, no fake photo)
//   - Credits page reachable from /news
//   - Title hierarchy (one clear level per slot)
//   - Animation contract preserved (only transform + opacity)

import { describe, expect, it } from "vitest";
import { createHash } from "node:crypto";
import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { resolve } from "node:path";

const FRONTEND_ROOT = resolve(__dirname, "../../..");

function readSrc(rel: string): string {
  return readFileSync(resolve(FRONTEND_ROOT, rel), "utf8");
}
function readJson<T = unknown>(rel: string): T {
  return JSON.parse(readFileSync(resolve(FRONTEND_ROOT, rel), "utf8")) as T;
}
function listDir(rel: string): string[] {
  return existsSync(resolve(FRONTEND_ROOT, rel))
    ? readdirSync(resolve(FRONTEND_ROOT, rel))
    : [];
}

const EXPECTED_WEBP_FILES = [
  "harvard-yard.webp",
  "mit-great-dome.webp",
  "stanford-main-quad.webp",
  "stanford-aerial.webp",
  "ucla-royce-hall.webp",
  "berkeley-memorial-glade.webp",
  "berkeley-library.webp",
  "princeton-campus.webp",
  "yale-old-campus.webp",
] as const;

interface Dimensions {
  width: number;
  height: number;
}

interface LicenseRecord {
  localFile: string;
  fallbackFile: string;
  school: string;
  scene: string;
  originalFileName: string;
  photographer: string;
  sourcePage: string;
  originalFileUrl: string;
  licenseName: string;
  licenseUrl: string;
  attributionRequired: boolean;
  shareAlikeRequired: boolean;
  modificationAllowed: boolean;
  downloadDate: string;
  originalSha256: string;
  localWebpSha256: string;
  originalDimensions: Dimensions;
  localDimensions: Dimensions;
  localBytes: number;
  cropApplied: boolean;
  cropDescription: string;
  colorAdjustment: string;
  notes: string;
}

function sha256(buffer: Buffer): string {
  return createHash("sha256").update(buffer).digest("hex");
}

function readWebpDimensions(buffer: Buffer): Dimensions {
  expect(buffer.subarray(0, 4).toString("ascii")).toBe("RIFF");
  expect(buffer.subarray(8, 12).toString("ascii")).toBe("WEBP");

  let offset = 12;
  while (offset + 8 <= buffer.length) {
    const chunk = buffer.subarray(offset, offset + 4).toString("ascii");
    const chunkSize = buffer.readUInt32LE(offset + 4);
    const data = offset + 8;

    if (chunk === "VP8X") {
      return {
        width: buffer.readUIntLE(data + 4, 3) + 1,
        height: buffer.readUIntLE(data + 7, 3) + 1,
      };
    }
    if (chunk === "VP8 ") {
      expect(buffer.subarray(data + 3, data + 6)).toEqual(Buffer.from([0x9d, 0x01, 0x2a]));
      return {
        width: buffer.readUInt16LE(data + 6) & 0x3fff,
        height: buffer.readUInt16LE(data + 8) & 0x3fff,
      };
    }
    if (chunk === "VP8L") {
      expect(buffer[data]).toBe(0x2f);
      const bits = buffer.readUInt32LE(data + 1);
      return {
        width: (bits & 0x3fff) + 1,
        height: ((bits >>> 14) & 0x3fff) + 1,
      };
    }

    offset = data + chunkSize + (chunkSize % 2);
  }

  throw new Error("WebP dimensions chunk not found");
}

// ──────────────────────────────────────────────────────────────────
// A. No inline SVG / no remote URL in production path
// ──────────────────────────────────────────────────────────────────
describe("A. No placeholder SVG in production render", () => {
  it("A1. news-images.ts does NOT generate inline data: URIs", () => {
    const src = readSrc("src/components/news/news-images.ts");
    // The previous Stage 7B-A.3.2 had `gradientSvg(...)` returning a
    // data: URI. That function must be gone in 7B-A.3.3.
    expect(src).not.toMatch(/data:image\/svg\+xml/);
    expect(src).not.toMatch(/encodeURIComponent\(svg\)/);
    expect(src).not.toMatch(/function\s+gradientSvg/);
  });

  it("A2. NEWS_HERO_IMAGES has 9 entries with local /news/campus/ href template", () => {
    const src = readSrc("src/components/news/news-images.ts");
    // 9 entries, each with `href: \`/news/campus/<slug>.webp\``. Match
    // each manifest line directly.
    const makeCount = (src.match(/makeHeroImage\(/g) ?? []).length;
    // 1 declaration + 9 calls = 10 occurrences; the 9 calls produce 9 entries.
    expect(makeCount).toBe(10);
    const matches = src.match(/href:\s*`\/news\/campus\//g) ?? [];
    expect(matches.length).toBe(1); // single template literal used by all 9
    // The template uses ${slugFor(i)} interpolation. Confirm the file
    // also exports slugFor and each entry's anchor/size/alt are well
    // formed. No http://, no https://, no data: URL anywhere in the
    // manifest.
    expect(src).not.toMatch(/href:\s*"https?:/);
    expect(src).not.toMatch(/href:\s*"data:/);
    expect(src).not.toMatch(/href:\s*`https?:/);
    expect(src).not.toMatch(/href:\s*`data:/);
  });

  it("A3. NEWS_HERO_IMAGES has 9 entries with /news/campus/fallback/<slug>.svg", () => {
    const src = readSrc("src/components/news/news-images.ts");
    const matches = src.match(/fallbackHref:\s*`\/news\/campus\/fallback\//g) ?? [];
    expect(matches.length).toBe(1); // single template literal used by all 9
  });

  it("A4. HeroImage src falls back when <img> fails to load", () => {
    const src = readSrc("src/components/news/HeroImage.tsx");
    expect(src).toContain("useState");
    expect(src).toContain("setErrored");
    expect(src).toMatch(/onError=\{[^}]*setErrored\(true\)/);
    // The src must be the fallback after an error.
    expect(src).toMatch(/src = errored \? image\.fallbackHref : image\.href/);
  });

  it("A5. no image href points to google / news site / xiaohongshu / pinterest", () => {
    const src = readSrc("src/components/news/news-images.ts");
    for (const blocked of [
      "google.com",
      "googleusercontent.com",
      "xiaohongshu.com",
      "pinterest.com",
      "news.cn",
      "bbc.com",
      "nytimes.com",
    ]) {
      expect(src, `href should not reference ${blocked}`).not.toContain(blocked);
    }
  });

  it("A6. all 9 production WebP files exist, are real WebP images, and are not tiny placeholders", () => {
    const campusDir = resolve(FRONTEND_ROOT, "public/news/campus");
    const files = readdirSync(campusDir).filter((file) => file.endsWith(".webp")).sort();
    expect(files).toEqual([...EXPECTED_WEBP_FILES].sort());

    for (const file of files) {
      const bytes = readFileSync(resolve(campusDir, file));
      expect(bytes.subarray(0, 4).toString("ascii"), file).toBe("RIFF");
      expect(bytes.subarray(8, 12).toString("ascii"), file).toBe("WEBP");
      expect(bytes.length, `${file} is too small to be a campus photograph`).toBeGreaterThan(50_000);
      const dimensions = readWebpDimensions(bytes);
      expect(dimensions.width, file).toBeGreaterThanOrEqual(900);
      expect(dimensions.height, file).toBeGreaterThanOrEqual(500);
    }
  });

  it("A7. HeroImage uses next/image with intrinsic dimensions, sizes, and object-cover", () => {
    const src = readSrc("src/components/news/HeroImage.tsx");
    expect(src).toContain('import Image from "next/image"');
    expect(src).toContain("<Image");
    expect(src).not.toMatch(/<img\b/);
    expect(src).toContain("width={image.width}");
    expect(src).toContain("height={image.height}");
    expect(src).toContain("sizes=");
    expect(src).toContain("object-cover");
  });
});

// ──────────────────────────────────────────────────────────────────
// B. New color palette
// ──────────────────────────────────────────────────────────────────
describe("B. New ink-green-grey palette", () => {
  it("B1. the new bg color (#111513) is exported from news-images.ts", () => {
    const src = readSrc("src/components/news/news-images.ts");
    expect(src).toContain("#111513");
  });

  it("B2. the old #0E0B08 brown-black is no longer in any source file", () => {
    // strip comments first so we don't catch the explanation text
    const stripComments = (s: string) =>
      s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
    for (const f of [
      "src/components/news/NewsEntryHero.tsx",
      "src/components/news/news-images.ts",
      "src/app/globals.css",
    ]) {
      const s = stripComments(readSrc(f));
      expect(s, `${f} still uses #0E0B08`).not.toContain("#0E0B08");
      // also strip 0E0B08 from any rgb()
      expect(s, `${f} still uses rgb(14,`).not.toMatch(/rgb\(\s*14\s*,\s*11\s*,\s*8/);
    }
  });

  it("B3. the new title color (#F1F2EA) is exported from news-images.ts and used in NewsEntryHero", () => {
    const manifest = readSrc("src/components/news/news-images.ts");
    expect(manifest).toContain("#F1F2EA");
    const hero = readSrc("src/components/news/NewsEntryHero.tsx");
    // The hero references NEWS_HERO_COLORS.title (the const), not the
    // literal hex. The hex is documented in news-images.ts.
    expect(hero).toContain("NEWS_HERO_COLORS.title");
  });

  it("B4. no forced brown filter (sepia, hue-rotate to warm, etc.) is applied to images", () => {
    // The CSS keyframes and the React component must not apply a
    // brown tint to images. We assert no `sepia(...)`, no warm
    // `hue-rotate()`, no saturate > 1.3, and no contrast shifts.
    const css = readSrc("src/app/globals.css");
    expect(css).not.toMatch(/filter\s*:\s*sepia\(/);
    expect(css).not.toMatch(/filter\s*:\s*hue-rotate\((?:[12]\d|[3-9]\d|1\d\d)/); // > 10deg warm
    // The hero keyframes only animate transform + opacity.
    expect(css).toMatch(/transform: scale3d/);
  });

  it("B5. all 9 color tokens are present in news-images.ts", () => {
    const src = readSrc("src/components/news/news-images.ts");
    const expected = [
      "#111513", // bg
      "#171C19", // bgSoft
      "#F1F2EA", // title
      "#C4C9C1", // text
      "#929A92", // muted
      "#D7DCD3", // line
      "#A7B5A3", // accent
      "#1F2A23", // fallback
    ];
    for (const t of expected) {
      expect(src, `color ${t} not exported`).toContain(t);
    }
  });
});

// ──────────────────────────────────────────────────────────────────
// C. ATTRIBUTIONS.md + LICENSES.json
// ──────────────────────────────────────────────────────────────────
describe("C. License / attribution metadata", () => {
  it("C1. ATTRIBUTIONS.md exists", () => {
    expect(
      existsSync(resolve(FRONTEND_ROOT, "public/news/campus/ATTRIBUTIONS.md")),
    ).toBe(true);
  });

  it("C2. LICENSES.json exists and parses", () => {
    const path = resolve(FRONTEND_ROOT, "docs/STAGE7B-A3-3-NEWS-PHOTOGRAPHY-LICENSES.json");
    expect(existsSync(path)).toBe(true);
    const data = readJson(path) as { records: Array<Record<string, unknown>> };
    expect(Array.isArray(data.records)).toBe(true);
  });

  it("C3. LICENSES.json has 9 records, each with required fields", () => {
    const data = readJson<{ records: Array<Record<string, unknown>> }>(
      "docs/STAGE7B-A3-3-NEWS-PHOTOGRAPHY-LICENSES.json",
    );
    expect(data.records.length).toBe(9);
    const requiredFields = [
      "localFile", "fallbackFile", "school", "scene", "originalFileName",
      "photographer", "sourcePage", "originalFileUrl", "licenseName",
      "licenseUrl", "attributionRequired", "shareAlikeRequired",
      "modificationAllowed", "downloadDate", "originalSha256",
      "localWebpSha256", "originalDimensions", "localDimensions",
      "localBytes", "cropApplied", "cropDescription", "colorAdjustment", "notes",
    ];
    for (const r of data.records) {
      for (const f of requiredFields) {
        expect(r, `record ${r.id} missing field ${f}`).toHaveProperty(f);
        const v = (r as Record<string, unknown>)[f];
        // attributionRequired and shareAlikeRequired are explicit
        // booleans (false for public-domain records); we only require
        // string-typed fields to be non-empty.
        if (["attributionRequired", "shareAlikeRequired", "cropApplied"].includes(f)) continue;
        expect(v, `record ${r.id} field ${f} is empty`).toBeTruthy();
      }
    }
  });

  it("C4. every localFile path lives under /news/campus/", () => {
    const data = readJson<{ records: Array<{ localFile: string; fallbackFile: string }> }>(
      "docs/STAGE7B-A3-3-NEWS-PHOTOGRAPHY-LICENSES.json",
    );
    for (const r of data.records) {
      expect(r.localFile).toMatch(/^public\/news\/campus\/[a-z0-9\-]+\.webp$/);
      expect(r.fallbackFile).toMatch(/^public\/news\/campus\/fallback\/[a-z0-9\-]+\.svg$/);
    }
  });

  it("C5. every sourcePage is a valid https URL on wikimedia.org or unsplash.com", () => {
    const data = readJson<{ records: Array<{ sourcePage: string; originalFileUrl: string }> }>(
      "docs/STAGE7B-A3-3-NEWS-PHOTOGRAPHY-LICENSES.json",
    );
    for (const r of data.records) {
      expect(r.sourcePage).toMatch(/^https:\/\/commons\.wikimedia\.org\/wiki\/File:/);
      expect(r.originalFileUrl).toMatch(/^https:\/\/upload\.wikimedia\.org\/wikipedia\/commons\//);
    }
  });

  it("C6. no license is CC BY-NC (commercial use forbidden)", () => {
    // The directive forbids commercial-photographer-restricted images.
    // CC BY-SA is OK; CC BY-NC is NOT.
    const data = readJson<{ records: Array<{ licenseName: string }> }>(
      "docs/STAGE7B-A3-3-NEWS-PHOTOGRAPHY-LICENSES.json",
    );
    for (const r of data.records) {
      expect(r.licenseName).not.toMatch(/BY-NC/);
    }
  });

  it("C7. fallback SVGs exist for all 9 records", () => {
    const fallbackFiles = listDir("public/news/campus/fallback");
    expect(fallbackFiles.length).toBeGreaterThanOrEqual(9);
    for (const f of fallbackFiles) {
      expect(f).toMatch(/\.svg$/);
    }
  });

  it("C8. Credits page exists and is reachable from the hero", () => {
    const hero = readSrc("src/components/news/NewsEntryHero.tsx");
    // The credits link uses a const ref for the URL. The literal
      // /news/credits value lives in news-images.ts.
      expect(hero).toContain("NEWS_HERO_CREDITS_LINK");
      const manifest = readSrc("src/components/news/news-images.ts");
      expect(manifest).toContain("/news/credits");
    expect(hero).toContain("校园摄影来源与授权");
    expect(
      existsSync(resolve(FRONTEND_ROOT, "src/app/news/credits/page.tsx")),
    ).toBe(true);
  });

  it("C9. every record has a known author/license and hashes that match the local WebP", () => {
    const data = readJson<{ records: LicenseRecord[] }>(
      "docs/STAGE7B-A3-3-NEWS-PHOTOGRAPHY-LICENSES.json",
    );
    const attributed = readSrc("public/news/campus/ATTRIBUTIONS.md");

    for (const record of data.records) {
      expect(record.photographer).not.toMatch(/^unknown$/i);
      expect(record.licenseName).not.toMatch(/^unknown$/i);
      expect(record.modificationAllowed).toBe(true);
      expect(record.downloadDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(record.originalSha256).toMatch(/^[a-f0-9]{64}$/);
      expect(record.localWebpSha256).toMatch(/^[a-f0-9]{64}$/);

      const absolute = resolve(FRONTEND_ROOT, record.localFile);
      const bytes = readFileSync(absolute);
      expect(sha256(bytes), record.localFile).toBe(record.localWebpSha256);
      expect(statSync(absolute).size, record.localFile).toBe(record.localBytes);
      expect(readWebpDimensions(bytes), record.localFile).toEqual(record.localDimensions);
      expect(attributed).toContain(record.photographer);
      expect(attributed).toContain(record.sourcePage);
      expect(attributed).toContain(record.licenseName);
    }
  });

  it("C10. the 9 license records map one-to-one to the 9 runtime image files", () => {
    const data = readJson<{ records: LicenseRecord[] }>(
      "docs/STAGE7B-A3-3-NEWS-PHOTOGRAPHY-LICENSES.json",
    );
    const files = data.records.map((record) => record.localFile.replace("public/news/campus/", ""));
    expect(files.sort()).toEqual([...EXPECTED_WEBP_FILES].sort());
    expect(new Set(files).size).toBe(9);
  });

  it("C11. Credits renders from the canonical license JSON instead of a duplicate hard-coded table", () => {
    const credits = readSrc("src/components/news/NewsCreditsPage.tsx");
    expect(credits).toContain("STAGE7B-A3-3-NEWS-PHOTOGRAPHY-LICENSES.json");
    expect(credits).not.toMatch(/const\s+PHOTOS\s*:/);
  });
});

// ──────────────────────────────────────────────────────────────────
// D. Title hierarchy (one clear level per slot)
// ──────────────────────────────────────────────────────────────────
describe("D. Title hierarchy", () => {
  it("D1. main title is 留学资讯 (single line)", () => {
    const src = readSrc("src/components/news/news-images.ts");
    expect(src).toContain('NEWS_HERO_TITLE_ZH = "留学资讯"');
  });

  it("D2. the old 集合 line is removed from the title constant", () => {
    const src = readSrc("src/components/news/news-images.ts");
    expect(src).not.toMatch(/留学资讯\\n集合/);
  });

  it("D3. CTA is 进入资讯中心 → (not EXPLORE STORIES, not 进入留学资讯)", () => {
    const src = readSrc("src/components/news/news-images.ts");
    expect(src).toContain('NEWS_HERO_CTA = "进入资讯中心  →"');
    expect(src).not.toContain("EXPLORE STORIES");
    expect(src).not.toMatch(/进入留学资讯\s*→/);
  });

  it("D4. English title is PATHOS JOURNAL (uppercase tracking)", () => {
    const src = readSrc("src/components/news/news-images.ts");
    expect(src).toContain('NEWS_HERO_TITLE_EN = "PATHOS JOURNAL"');
  });
});

// ──────────────────────────────────────────────────────────────────
// E. Animation contract (preserved)
// ──────────────────────────────────────────────────────────────────
describe("E. Animation still uses only transform + opacity", () => {
  // Helper: capture body of an @keyframes block by walking braces.
  // The non-greedy regex `\s\S+?` stops at the first `@` which
  // truncates the block before the next @keyframes declaration.
  function keyframeBody(css: string, name: string): string | null {
    const startRe = new RegExp("@keyframes\\s+" + name + "\\s*\\{");
    const start = css.search(startRe);
    if (start < 0) return null;
    let depth = 0;
    for (let i = start; i < css.length; i++) {
      if (css[i] === "{") depth++;
      else if (css[i] === "}") {
        depth--;
        if (depth === 0) return css.slice(start, i + 1);
      }
    }
    return null;
  }

  it("E1. news-hero-img-loop keyframes only animate transform + opacity", () => {
    const css = readSrc("src/app/globals.css");
    const block = keyframeBody(css, "news-hero-img-loop");
    expect(block, "keyframe block not found").not.toBeNull();
    const body = block!;
    expect(body).toMatch(/transform:/);
    expect(body).toMatch(/opacity:/);
    expect(body).not.toMatch(/\bwidth\s*:/);
    expect(body).not.toMatch(/\bheight\s*:/);
    expect(body).not.toMatch(/\bfilter\s*:/);
  });

  it("E2. initial scale is between 0.78 and 0.86 (no flash from 0)", () => {
    const css = readSrc("src/app/globals.css");
    const block = css.match(/@keyframes\s+news-hero-img-loop\s*\{([\s\S]+?)\}/);
    expect(block).not.toBeNull();
    const m = block![1].match(/scale3d\(([\d.]+)/);
    expect(m).not.toBeNull();
    const scale = Number(m![1]);
    expect(scale).toBeGreaterThanOrEqual(0.78);
    expect(scale).toBeLessThanOrEqual(0.86);
  });

  it("E3. peak and final scales stay between 1.0 and 1.04", () => {
    const css = readSrc("src/app/globals.css");
    const scales = Array.from(css.matchAll(/scale3d\(([\d.]+)/g)).map((match) => Number(match[1]));
    const animatedScales = scales.filter((scale) => scale >= 1);
    expect(animatedScales.length).toBeGreaterThan(0);
    expect(Math.max(...animatedScales)).toBeLessThanOrEqual(1.04);
  });

  it("E4. prefers-reduced-motion fallback is present", () => {
    const css = readSrc("src/app/globals.css");
    expect(css).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/);
    expect(css).toMatch(/animation:\s*none\s*!important/);
  });
});

// ──────────────────────────────────────────────────────────────────
// F. Build does NOT depend on external image network
// ──────────────────────────────────────────────────────────────────
describe("F. Build isolation", () => {
  it("F1. no image href in source points to an external https:// URL", () => {
    const src = readSrc("src/components/news/news-images.ts");
    // Every href must be a local /news/campus path.
    const hrefRe = /href:\s*`([^`]+)`/g;
    const hrefs: string[] = [];
    let m: RegExpExecArray | null;
    while ((m = hrefRe.exec(src))) {
      hrefs.push(m[1]);
    }
    for (const h of hrefs) {
      expect(h, `external URL in hero: ${h}`).not.toMatch(/^https?:/);
    }
  });

  it("F2. <img loading=\"lazy\"> ensures no eager fetch", () => {
    const src = readSrc("src/components/news/HeroImage.tsx");
    expect(src).toMatch(/loading="lazy"/);
  });

  it("F3. fallback SVGs are inlined flat colors (no fake photo)", () => {
    const fallbackDir = resolve(FRONTEND_ROOT, "public/news/campus/fallback");
    const files = readdirSync(fallbackDir);
    for (const f of files) {
      if (!f.endsWith(".svg")) continue;
      const content = readFileSync(`${fallbackDir}/${f}`, "utf8");
      // A real photo would be encoded with base64. Fallback is
      // a small text SVG.
      expect(content.length).toBeLessThan(2000);
      expect(content).toContain("<svg");
      expect(content).toContain("<rect");
      // No complex gradients that mimic photo textures
      expect(content).not.toContain("feTurbulence");
    }
  });
});
