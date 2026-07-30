"use client";

// Stage 7B-A.3.3 — Single hero image.
//
// Stage 7B-A.3.2 used inline `data:` URI placeholders. Stage
// 7B-A.3.3 replaces them with real local resources at
// `/news/campus/<slug>.webp` (see news-images.ts). The image
// element renders the primary asset with a quiet solid-color
// fallback while decoding OR if the asset fails to load.
//
// The animation is bound through CSS custom properties so the loop
// never re-syncs between images (Stage 7B-A.3 invariant +
// Stage 7B-A.3.3 §九 softening: scale 0.78-0.86 → 1.0-1.04).

import { useState } from "react";
import Image from "next/image";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";
import type { NewsHeroImage } from "./news-images";
import { NEWS_HERO_COLORS } from "./news-images";

export interface HeroImageProps {
  image: NewsHeroImage;
  index: number;
}

export function HeroImage({ image, index }: HeroImageProps) {
  const reduced = usePrefersReducedMotion();
  // When the real .webp fails to decode (e.g. file not yet committed
  // because the sandbox has no network access for asset download),
  // we fall back to a quiet solid-color SVG block. The fallback is
  // intentionally NOT a photographic lookalike — it is a flat color
  // that signals "loading" without faking real photography.
  const [errored, setErrored] = useState(false);
  const src = errored ? image.fallbackHref : image.href;

  const style: React.CSSProperties & Record<string, string | number> = {
    ["--news-duration" as string]: `${image.duration}s`,
    ["--news-delay" as string]: `${image.delay}s`,
    ["--news-drift-x" as string]: `${image.driftX}px`,
    ["--news-drift-y" as string]: `${image.driftY}px`,
  };

  // Fallback color is applied via the background-color CSS variable
  // so the placeholder reads as a soft dark green panel rather than
  // a black void if the image hasn't been added to the bundle yet.
  const fallbackStyle: React.CSSProperties = {
    backgroundColor: NEWS_HERO_COLORS.fallback,
  };

  return (
    <Image
      src={src}
      alt={`${image.alt} / ${image.altEn}`}
      title={image.alt}
      aria-hidden={false}
      role="img"
      loading="lazy"
      decoding="async"
      width={image.width}
      height={image.height}
      sizes="(min-width: 1280px) 320px, (min-width: 768px) 220px, 160px"
      data-testid={`news-hero-img-${index + 1}`}
      data-aspect={image.aspect}
      data-reduced={reduced ? "true" : "false"}
      data-src={image.href}
      data-fallback={image.fallbackHref}
      onError={() => setErrored(true)}
      className={`news-hero-img object-cover ${image.anchor.base} ${image.anchor.md} ${image.anchor.xl} ${image.size.base} ${image.size.md} ${image.size.xl}`}
      style={{ ...style, ...fallbackStyle }}
    />
  );
}

export default HeroImage;
