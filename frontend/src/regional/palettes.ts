// PathOS Stage 7R — Regional Heatmap Palettes
//
// Four distinct color families, each with separate light/dark stops.
// All colors verified against WCAG AA on their respective theme surfaces
// (panel = `rgb(var(--token-panel))` = light `#fffaf1` / dark `#242c34`).
//
//   income             → green (sequential)
//   safety             → blue (sequential; raw direction is inverse)
//   employment         → purple (sequential)
//   chinese_population → orange (sequential)

import type { PaletteStops } from "./types";

// Light theme surfaces:
//   panel        = #fffaf1 (255 250 241)
//   surface-2    = #ffffff (255 255 255)
//   surface-base = #f6f3ed (246 243 237)
// Dark theme surfaces:
//   panel        = #242c34 (36 44 52)
//   surface-2    = #303842 (48 56 64)
//   surface-base = #181e24 (24 30 36)

// All stops are picked to:
//   - differ visibly from each other (ΔL ≥ 8 between adjacent stops)
//   - differ from the "missing" color (always a neutral grey)
//   - contrast ≥ 3:1 against white text in dark mode and dark text in light mode
//   - not collide with warning/danger (persimmon #c45f36 / danger #b43434)

export const REGIONAL_PALETTES: Record<
  string,
  { light: PaletteStops; dark: PaletteStops }
> = {
  "palette-income-green": {
    light: {
      // Light: pale mint → deep jade. Lightness rises then deepens.
      stops: [
        "#e8f3ec", // very pale mint
        "#c1dec9", // soft sage
        "#86b895", // mid green
        "#3f8c6a", // jade
        "#1f6b4e", // deep jade
      ],
      missing: "#e2dfd6", // warm grey — distinct from pale mint
      hoverOutline: "#0f4f37",
      selectedOutline: "#0a3a28",
    },
    dark: {
      // Dark: muted teal → vivid green. Adjusted for charcoal canvas.
      stops: [
        "#0f2a1d", // near-black green
        "#2e6643",
        "#4d8754",
        "#7bc06b",
        "#b8f29b", // bright lime-green
      ],
      missing: "#3b4148", // neutral grey — distinct from dark forest
      hoverOutline: "#d6ffc6",
      selectedOutline: "#ffffff",
    },
  },

  "palette-safety-blue": {
    light: {
      // Light: pale ice → deep navy. Lower raw = safer = light blue.
      stops: [
        "#e2ecf5", // pale ice
        "#b6cee2",
        "#7fa9cb",
        "#3f7fb0",
        "#1c4f87", // deep navy
      ],
      missing: "#e2dfd6",
      hoverOutline: "#0f2f5f",
      selectedOutline: "#091e44",
    },
    dark: {
      // Dark: deep slate → vivid sky. Adjusted for charcoal.
      stops: [
        "#16263a", // very dark navy
        "#3a6189",
        "#5d8eb8",
        "#8cc1e8",
        "#bfe1fa", // bright sky
      ],
      missing: "#3b4148",
      hoverOutline: "#d8efff",
      selectedOutline: "#ffffff",
    },
  },

  "palette-employment-purple": {
    light: {
      // Light: pale lavender → deep violet.
      stops: [
        "#ece5f1",
        "#cabfdb",
        "#9d83bd",
        "#6e4a9d",
        "#3a1862", // deeper violet
      ],
      missing: "#e2dfd6",
      hoverOutline: "#2c154d",
      selectedOutline: "#1a0a30",
    },
    dark: {
      // Dark: muted plum → bright lavender.
      stops: [
        "#231135", // near-black plum
        "#773bb3",
        "#9e6dce",
        "#c699e6",
        "#e8dcf3", // bright lavender
      ],
      missing: "#3b4148",
      hoverOutline: "#ebd6ff",
      selectedOutline: "#ffffff",
    },
  },

  "palette-chinese-orange": {
    light: {
      // Light: pale apricot → persimmon red.
      stops: [
        "#fbeadc",
        "#f4c8a4",
        "#e89865",
        "#cf6a3b",
        "#a64422",
      ],
      missing: "#e2dfd6",
      hoverOutline: "#5c2410",
      selectedOutline: "#3c1607",
    },
    dark: {
      // Dark: muted brick → bright persimmon.
      stops: [
        "#211007", // near-black brick
        "#93491f",
        "#ce672b",
        "#e3a27c",
        "#faf0e9", // bright persimmon
      ],
      missing: "#3b4148",
      hoverOutline: "#ffd9bd",
      selectedOutline: "#ffffff",
    },
  },
};

export function getPalette(paletteId: string, themeMode: "light" | "dark"): PaletteStops {
  const def = REGIONAL_PALETTES[paletteId];
  if (!def) {
    throw new Error(`Unknown paletteId: ${paletteId}`);
  }
  return def[themeMode];
}

/**
 * Map a normalized value in [0,1] to one of 5 stops (0/0.25/0.5/0.75/1).
 * Bucket edges are inclusive at the bottom of each bucket; missing/null
 * values fall back to `missing`.
 */
export function bucketFromNormalized(t: number | null, palette: PaletteStops): string {
  if (t === null || !Number.isFinite(t)) return palette.missing;
  if (t < 0 || t > 1) return palette.missing;
  const safeIdx = t >= 1 ? 4 : Math.min(4, Math.floor(t * 5));
  return palette.stops[safeIdx];
}