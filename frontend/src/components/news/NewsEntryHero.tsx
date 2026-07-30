"use client";

// Stage 7B-A.3.3 — News Entry Hero (color-reconciled).
//
// Stage 7B-A.3.3 changes vs 7B-A.3.2:
//   - Color palette swapped from brown-black to ink-green-grey-black
//     (no warm bias, no pure black, no brown filter).
//   - Title hierarchy simplified: 留学资讯 / PATHOS JOURNAL /
//     探索最新申请趋势... / 进入资讯中心 →.
//   - 9 photographic slots now reference real campus images
//     (image references in news-images.ts; binary .webp files are
//     committed separately once network download is available).
//   - Image fallback uses a quiet solid-color panel (no fake photo).
//   - "校园摄影来源与授权" credit link at the bottom.

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { HeroImage } from "./HeroImage";
import { HeroBracket } from "./HeroBracket";
import {
  NEWS_HERO_IMAGES,
  NEWS_HERO_TITLE_ZH,
  NEWS_HERO_TITLE_EN,
  NEWS_HERO_SUBTITLE_ZH,
  NEWS_HERO_CTA,
  NEWS_HERO_LINK,
  NEWS_HERO_CREDITS_LINK,
  NEWS_HERO_ARIA_LABEL,
  NEWS_HERO_COLORS,
} from "./news-images";

export function NewsEntryHero() {
  return (
    <section
      data-testid="news-entry-hero"
      aria-label={NEWS_HERO_ARIA_LABEL}
      data-colors="v3"
      className="relative isolate w-full overflow-hidden"
      style={{
        backgroundColor: NEWS_HERO_COLORS.bg,
        minHeight: "min(80vh, 720px)",
      }}
    >
      {/* Photographic placeholders — each image is its own
          independent loop. They are rendered behind the central
          title via a low z-index wrapper. */}
      <div className="pointer-events-none absolute inset-0 z-0" aria-hidden="true">
        {NEWS_HERO_IMAGES.map((img, i) => (
          <HeroImage key={img.id} image={img} index={i} />
        ))}
      </div>

      {/* Centre: title + bracket + cue. The <Link> wraps the entire
          editorial cluster so the click target is generous. */}
      <div className="relative z-10 mx-auto flex h-full w-full max-w-7xl items-center justify-center px-6 py-24 md:py-32">
        <Link
          href={NEWS_HERO_LINK}
          aria-label={NEWS_HERO_ARIA_LABEL}
          data-testid="news-entry-link"
          className="news-hero-link group relative flex w-full max-w-3xl flex-col items-center text-center"
          style={{ minHeight: "min(60vh, 480px)" }}
        >
          {/* Editorial corner brackets. Two SVG elements at opposite
              corners of the title safe area. They do NOT form a
              closed border — only top-left + bottom-right "L" hooks,
              to read as a viewfinder rather than a frame. */}
          <HeroBracket
            width={320}
            height={220}
            className="absolute left-1/2 top-1/2 hidden -translate-x-1/2 -translate-y-1/2 md:block"
            alpha={0.32}
          />
          <HeroBracket
            width={240}
            height={170}
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 md:hidden"
            alpha={0.28}
          />

          {/* Stage 7B-A.3.3: one clear level — large Chinese title
              (single line). The previous "集合" line is removed; the
              English title sits below at a different scale. */}
          <h1
            data-testid="news-hero-title"
            className="news-hero-title font-serif font-semibold leading-[1.05] tracking-[-0.02em]"
            style={{
              color: NEWS_HERO_COLORS.title,
              fontSize: "clamp(56px, 9vw, 128px)",
            }}
          >
            {NEWS_HERO_TITLE_ZH}
          </h1>

          {/* English title — small uppercase */}
          <p
            data-testid="news-hero-title-en"
            className="mt-3 font-sans uppercase"
            style={{
              color: NEWS_HERO_COLORS.muted,
              fontSize: "11px",
              letterSpacing: "0.32em",
            }}
          >
            {NEWS_HERO_TITLE_EN}
          </p>

          {/* Subtitle (Chinese) */}
          <p
            data-testid="news-hero-subtitle"
            className="mt-6 max-w-xl font-sans leading-relaxed"
            style={{
              color: NEWS_HERO_COLORS.text,
              fontSize: "15px",
            }}
          >
            {NEWS_HERO_SUBTITLE_ZH}
          </p>

          {/* Entry cue */}
          <span
            data-testid="news-hero-cue"
            className="news-hero-cue mt-10 inline-flex items-center gap-2 font-sans uppercase"
            style={{
              color: NEWS_HERO_COLORS.line,
              fontSize: "11px",
              letterSpacing: "0.28em",
            }}
          >
            <span>{NEWS_HERO_CTA.split("→")[0].trim()}</span>
            <span className="news-hero-cue-arrow" aria-hidden="true">
              <ArrowRight size={14} strokeWidth={1.5} />
            </span>
          </span>
        </Link>
      </div>

      {/* Bottom edge: gradient to bg + Credits link (Stage 7B-A.3.3
          §十). The link is a normal text link, not a floating chip. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 bottom-0 h-24"
        style={{
          background: `linear-gradient(to bottom, transparent, ${NEWS_HERO_COLORS.gradientEnd})`,
        }}
      />
      <div className="relative z-10 mx-auto flex w-full max-w-7xl justify-end px-6 pb-6">
        <Link
          href={NEWS_HERO_CREDITS_LINK}
          data-testid="news-hero-credits-link"
          className="news-hero-credits-link font-sans"
          style={{
            color: NEWS_HERO_COLORS.muted,
            fontSize: "10px",
            letterSpacing: "0.22em",
            textTransform: "uppercase",
            opacity: 0.7,
          }}
        >
          校园摄影来源与授权
        </Link>
      </div>
    </section>
  );
}

export default NewsEntryHero;
