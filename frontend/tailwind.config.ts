import type { Config } from "tailwindcss";

/**
 * PathOS design tokens.
 *
 * Stage 7A closing patch — design system ground-up. Tokens are
 * declared in two places:
 *
 *   1. CSS variables in globals.css (`:root` for light, `.dark` for
 *      dark) — the source of truth at runtime, swap targets for
 *      the theme toggle.
 *   2. The Tailwind theme extension below — re-exposed as utility
 *      classes (`bg-ink`, `text-cobalt`, …) so components can keep
 *      using the familiar Tailwind shorthand.
 *
 * Keep the two in sync. The hex values below mirror the CSS vars;
 * if you change one, change both.
 */
const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  // Toggle dark mode via a `.dark` class on <html> (or any ancestor).
  // This is what `lib/theme.ts` writes when the user picks Dark or
  // when the System listener resolves to dark.
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Brand / semantic tokens
        ink: "rgb(var(--token-ink) / <alpha-value>)",
        paper: "rgb(var(--token-paper) / <alpha-value>)",
        panel: "rgb(var(--token-panel) / <alpha-value>)",
        line: "rgb(var(--token-line) / <alpha-value>)",
        jade: "rgb(var(--token-jade) / <alpha-value>)",
        persimmon: "rgb(var(--token-persimmon) / <alpha-value>)",
        cobalt: "rgb(var(--token-cobalt) / <alpha-value>)",
        // Surfaces — distinct layers of elevation
        "surface-base": "rgb(var(--token-surface-base) / <alpha-value>)",
        "surface-1": "rgb(var(--token-surface-1) / <alpha-value>)",
        "surface-2": "rgb(var(--token-surface-2) / <alpha-value>)",
        "surface-muted": "rgb(var(--token-surface-muted) / <alpha-value>)",
        // Text — primary / secondary / muted
        "text-primary": "rgb(var(--token-text-primary) / <alpha-value>)",
        "text-secondary": "rgb(var(--token-text-secondary) / <alpha-value>)",
        "text-muted": "rgb(var(--token-text-muted) / <alpha-value>)",
        // Borders — soft / strong
        "border-soft": "rgb(var(--token-border-soft) / <alpha-value>)",
        "border-strong": "rgb(var(--token-border-strong) / <alpha-value>)",
        // Accent (alias for cobalt so semantic names compose)
        accent: "rgb(var(--token-cobalt) / <alpha-value>)",
        // Status
        success: "rgb(var(--token-jade) / <alpha-value>)",
        warning: "rgb(var(--token-persimmon) / <alpha-value>)",
        danger: "rgb(var(--token-danger) / <alpha-value>)",
        // Focus ring
        "focus-ring": "rgb(var(--token-focus) / <alpha-value>)",
      },
      // Standardised corner radii — three steps only, not every
      // component invents its own.
      borderRadius: {
        control: "0.375rem",  // 6px — buttons, inputs, small chips
        card: "0.75rem",      // 12px — cards, popovers, sheets
        overlay: "1rem",      // 16px — modals, large sheets
      },
      // Box-shadow layers — only for true elevation; surfaces
      // should rely on colour/border, not shadow.
      boxShadow: {
        // 1 — small floating UI (tooltips, popovers, dropdowns)
        pop: "0 6px 24px -8px rgb(0 0 0 / 0.16), 0 2px 6px -2px rgb(0 0 0 / 0.08)",
        // 2 — panels, sheets
        panel: "0 18px 60px -22px rgb(0 0 0 / 0.22), 0 6px 16px -8px rgb(0 0 0 / 0.10)",
        // 3 — modals, large overlays
        overlay: "0 32px 80px -28px rgb(0 0 0 / 0.30), 0 12px 24px -12px rgb(0 0 0 / 0.18)",
        // Focus ring (for keyboard navigation)
        ring: "0 0 0 3px rgb(var(--token-focus) / 0.45)",
      },
      // Standardised heights for controls (input / button / chip).
      // Use `h-control-sm`, `h-control`, `h-control-lg` instead of
      // bare pixel values.
      spacing: {
        "control-sm": "1.75rem",  // 28px
        "control":   "2.25rem",   // 36px
        "control-lg": "2.75rem",  // 44px
        "nav":       "3.5rem",    // 56px — global nav height
      },
      fontSize: {
        // Display / page-title / section-title / body / caption / label
        // expressed with the matching line-height baked in.
        "display":  ["1.75rem", { lineHeight: "1.2",  letterSpacing: "-0.02em", fontWeight: "600" }],
        "page":     ["1.375rem",{ lineHeight: "1.25", letterSpacing: "-0.01em", fontWeight: "600" }],
        "section":  ["1.125rem",{ lineHeight: "1.3",  letterSpacing: "-0.005em",fontWeight: "600" }],
        "body":     ["0.875rem",{ lineHeight: "1.55" }],
        "caption":  ["0.75rem", { lineHeight: "1.45" }],
        "label":    ["0.6875rem",{ lineHeight: "1.3",  letterSpacing: "0.04em", fontWeight: "600" }],
      },
      maxWidth: {
        "page": "72rem",  // 1152px — primary page container
        "prose": "42rem", // 672px — long-form text
      },
      // Stage 7B-A.1 — Map Z-Index Token System
      // All `z-` utilities inside the map view MUST use these named
      // tokens. Literal `z-10` / `z-20` / `z-30` are forbidden inside
      // src/components/map/ — they invited the Stage 7B-A.1 stacking
      // collision (RegionLayerControl + StateSelector + visibility
      // badge + drill-down helper all squeezed into one row).
      zIndex: {
        "map-basemap": "0",
        "map-region": "5",
        "map-city": "10",
        "map-marker": "15",
        "map-hover": "18",
        "map-control": "20",
        "map-toolbar": "22",
        "map-legend": "24",
        "map-tooltip": "28",
        "map-profile": "30",
        "map-modal": "50",
      },
    }
  },
  plugins: []
};

export default config;
