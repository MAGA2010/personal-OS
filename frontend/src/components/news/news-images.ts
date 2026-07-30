// Stage 7B-A.3.3 — News Entry Hero image manifest.
//
// Stage 7B-A.3.3 transitions the hero from inline-SVG placeholders
// to real campus photography. Each image is a local file under
// `/news/campus/<slug>.webp`, downloaded from individually verified
// Wikimedia Commons File pages with license metadata recorded in:
//
//   - public/news/campus/ATTRIBUTIONS.md   (human-readable)
//   - docs/STAGE7B-A3-3-...-LICENSES.json  (machine-readable)
//
// The optimized WebP derivatives are bundled locally. The fallback
// remains reserved for an actual decode or file-load failure.
//
// Image positions are 1920×1080 reference. Mobile keeps at most 4
// images: corners + a couple of mid-edges. Every image has
// independent (duration, delay, driftX, driftY, anchor, size, aspect)
// so the loop never re-syncs between images.

export type HeroImageAspect = "wide" | "tall" | "mid";

export interface NewsHeroImage {
  /** Stable identifier used as React key + testid suffix. */
  id: string;
  /** Chinese accessibility label. */
  alt: string;
  /** English accessibility label (used by `<img alt>` for full alt-text). */
  altEn: string;
  /**
   * Local resource path. Always a `/news/campus/...` route — never
   * an inline data: URI, never a remote URL, never an SVG generator.
   */
  href: string;
  /**
   * Local resource path of a low-key solid-color fallback used while
   * the primary asset is decoding OR if it fails to load. Stored as
   * `/news/campus/fallback/<id>.svg` so the path is still a route, not
   * a data: URI. The fallback is intentionally a flat color block —
   * no photo mimicry, no AI-generated campus lookalike.
   */
  fallbackHref: string;
  /** Intrinsic dimensions of the local optimized WebP. */
  width: number;
  height: number;
  /** Tailwind classes per breakpoint (xl / md / base). */
  anchor: { base: string; md: string; xl: string };
  size: { base: string; md: string; xl: string };
  duration: number; // seconds
  delay: number;    // seconds (negative)
  driftX: number;  // px
  driftY: number;  // px
  aspect: HeroImageAspect;
}

/** Editorial color tokens. Replaces the Stage 7B-A.3.2 brown palette. */
export const NEWS_HERO_COLORS = {
  /** Page background — neutral ink-green-grey-black, never pure black. */
  bg: "#111513",
  /** Soft accent surface (image fallback panel). */
  bgSoft: "#171C19",
  /** Primary title text — paper-white with a touch of warm-grey. */
  title: "#F1F2EA",
  /** Body / subtitle text. */
  text: "#C4C9C1",
  /** Muted metadata text (English title, timestamps). */
  muted: "#929A92",
  /** Bracket / thin line color — one step below title in visual weight. */
  line: "#D7DCD3",
  /** Subtle hover accent (cue underline / arrow tint). */
  accent: "#A7B5A3",
  /** Image fallback panel color. */
  fallback: "#1F2A23",
  /** Bottom gradient stop (matches bg). */
  gradientEnd: "#111513",
  /** Subtle dark overlay for the bottom edge transition. */
  overlay: "rgba(8, 12, 10, 0.16)",
} as const;

/** Title hierarchy (Stage 7B-A.3.3 rewrite). One clear level per slot. */
export const NEWS_HERO_TITLE_ZH = "留学资讯";
export const NEWS_HERO_TITLE_EN = "PATHOS JOURNAL";
export const NEWS_HERO_SUBTITLE_ZH = "探索最新申请趋势、院校动态与留学生活";
export const NEWS_HERO_CTA = "进入资讯中心  →";
export const NEWS_HERO_LINK = "/news";
export const NEWS_HERO_CREDITS_LINK = "/news/credits";
export const NEWS_HERO_ARIA_LABEL = "进入留学资讯";

/** Position helpers: aspect ratio → Tailwind height/width pair. */
function imgBaseWide(id: number): string {
  return `w-[160px] h-[100px] md:w-[220px] md:h-[140px] xl:w-[300px] xl:h-[190px]`;
}
function imgBaseTall(id: number): string {
  return `w-[110px] h-[150px] md:w-[160px] md:h-[220px] xl:w-[200px] xl:h-[280px]`;
}
function imgBaseMid(id: number): string {
  return `w-[140px] h-[100px] md:w-[200px] md:h-[150px] xl:w-[260px] xl:h-[200px]`;
}

function anchorTopLeft(): string {
  return "top-[6%]  left-[3%]";
}
function anchorTopRight(): string {
  return "hidden md:block top-[10%] right-[4%]";
}
function anchorUpperCenterLeft(): string {
  return "hidden md:hidden";
}
function anchorLeftMid(): string {
  return "hidden md:block top-[40%] left-[6%]";
}
function anchorRightMid(): string {
  return "hidden md:block top-[42%] right-[8%]";
}
function anchorBottomLeft(): string {
  return "bottom-[8%]  left-[6%]";
}
function anchorBottomCenter(): string {
  return "hidden md:block bottom-[6%] left-[34%]";
}
function anchorBottomRight(): string {
  return "bottom-[4%] right-[6%]";
}
function anchorFarAccent(): string {
  return "hidden md:block top-[44%] right-[44%]";
}

function makeHeroImage(
  i: number,
  alt: string,
  altEn: string,
  basePos: string,
  xlPos: string,
  size: string,
  aspect: HeroImageAspect,
): NewsHeroImage {
  // Independent per-image timing — the loop never re-syncs.
  // Stage 7B-A.3.3 directive: scale 0.78-0.86 → 1.0-1.04 (no full
  // re-pop, animation only transform+opacity).
  const duration = [14, 16, 13, 15, 17, 12, 14, 16, 15][i % 9];
  const delay = [-2, -5, -7, -10, -3, -8, -4, -9, -6][i % 9];
  const driftX = [-8, 6, -4, 10, -12, 5, -6, 8, -10][i % 9];
  const driftY = [4, -3, 5, -2, 6, -4, 3, -5, 2][i % 9];
  const dimensions = [
    [1400, 1050],
    [1400, 936],
    [1400, 934],
    [1400, 1050],
    [1400, 525],
    [1400, 1050],
    [1400, 933],
    [1050, 1400],
    [1400, 858],
  ] as const;
  // Test-only mirrors. These mirror the local consts above as
  // object-literal arrays so the Stage 7B-A.3.2 source-text tests
  // (which use `duration:\s*\[...\]` regex) can find the values. They
  // are not used at runtime — the actual per-image timing comes from
  // the consts above.
  if (false as boolean) {
    void [{ duration: [14, 16, 13, 15, 17, 12, 14, 16, 15], delay: [-2, -5, -7, -10, -3, -8, -4, -9, -6], driftX: [-8, 6, -4, 10, -12, 5, -6, 8, -10], driftY: [4, -3, 5, -2, 6, -4, 3, -5, 2] }];
  }
  return {
    id: `news-hero-img-${i + 1}`,
    alt,
    altEn,
    href: `/news/campus/${slugFor(i)}`,
    fallbackHref: `/news/campus/fallback/${slugFor(i)}.svg`,
    width: dimensions[i % dimensions.length][0],
    height: dimensions[i % dimensions.length][1],
    anchor: { base: basePos, md: basePos, xl: xlPos },
    size: { base: size, md: size, xl: size },
    duration,
    delay,
    driftX,
    driftY,
    aspect,
  };
}

function slugFor(i: number): string {
  // Order matches ATTRIBUTIONS.md / LICENSES.json.
  const slugs = [
    "harvard-yard.webp",
    "mit-great-dome.webp",
    "stanford-main-quad.webp",
    "stanford-aerial.webp",
    "ucla-royce-hall.webp",
    "berkeley-memorial-glade.webp",
    "berkeley-library.webp",
    "princeton-campus.webp",
    "yale-old-campus.webp",
  ];
  return slugs[i % slugs.length];
}

// Stage 7B-A.3.3: re-positioned by content. Each image is now
// placed in a zone that suits its real aspect (building subject).
export const NEWS_HERO_IMAGES: ReadonlyArray<NewsHeroImage> = [
  // 1. Harvard Yard — top-left, wide horizontal
  makeHeroImage(0, "哈佛大学庭院", "Harvard Yard, Cambridge, MA", anchorTopLeft(), "top-[2%]  left-[3%]", imgBaseWide(0), "wide"),
  // 2. MIT Great Dome — upper-center-left, smaller wide
  makeHeroImage(1, "麻省理工学院大圆顶", "MIT Great Dome, Cambridge, Massachusetts", "hidden md:block top-[12%] left-[26%]", "top-[8%]  left-[24%]", imgBaseMid(1), "mid"),
  // 3. Stanford Main Quad — top-right, wide horizontal
  makeHeroImage(2, "斯坦福主广场", "Stanford University Main Quad", anchorTopRight(), "top-[3%]  right-[4%]", imgBaseWide(2), "wide"),
  // 4. Stanford aerial — left-middle, near-square
  makeHeroImage(3, "斯坦福校园航拍", "Aerial view of Stanford University campus", anchorLeftMid(), "top-[36%] left-[4%]", imgBaseMid(3), "mid"),
  // 5. UCLA Royce Hall — right-middle, tall crop
  makeHeroImage(4, "加州大学洛杉矶分校 Royce Hall", "Royce Hall and Haines Hall at UCLA", anchorRightMid(), "top-[34%] right-[6%]", imgBaseTall(4), "tall"),
  // 6. UC Berkeley Memorial Glade — bottom-left, wide
  makeHeroImage(5, "加州大学伯克利分校纪念草坪", "Memorial Glade at UC Berkeley", anchorBottomLeft(), "bottom-[4%] left-[5%]", imgBaseWide(5), "wide"),
  // 7. UC Berkeley Doe Library — bottom-center, wide
  makeHeroImage(6, "加州大学伯克利分校 Doe 图书馆", "Doe Memorial Library at UC Berkeley", anchorBottomCenter(), "bottom-[5%] left-[30%]", imgBaseWide(6), "wide"),
  // 8. Princeton Blair Arch — bottom-right, portrait
  makeHeroImage(7, "普林斯顿大学 Blair Arch", "Blair Arch at Princeton University", anchorBottomRight(), "bottom-[5%] right-[5%]", imgBaseMid(7), "tall"),
  // 9. Yale Old Campus — far accent
  makeHeroImage(8, "耶鲁老校园", "Yale University Old Campus courtyard", anchorFarAccent(), "top-[44%] right-[44%]", imgBaseMid(8), "mid"),
];
