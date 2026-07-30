// PathOS Stage 7B-A.1 — Map Z-Index Token System
//
// Single source of truth for every z-index used inside the map view.
// Components MUST consume these tokens via Tailwind utilities
// (`z-map-basemap`, `z-map-toolbar`, `z-map-legend`, …) or via
// `var(--map-z-<token>)` for ad-hoc cases. Arbitrary `z-10`, `z-20`,
// `z-30` literals are not allowed — they invite stacking collisions
// like the one Stage 7B-A.1 is closing.
//
// Update the Tailwind theme to add the matching utility classes.

export const MAP_Z = {
  /** Vector basemap canvas (the lowest interactive surface). */
  basemap: 0,
  /** Regional state choropleth layer (state polygons). */
  region: 5,
  /** City-level choropleth (when a state is drilled down). */
  city: 10,
  /** Persistent university POI markers. */
  marker: 15,
  /** Hover outlines / focus rings on geometry. */
  hover: 18,
  /** Generic in-map controls (badge, search shortcut). */
  control: 20,
  /** The unified MapToolbar (top-right). */
  toolbar: 22,
  /** The active regional legend (bottom-right). */
  legend: 24,
  /** Hover tooltips (regional + city). */
  tooltip: 28,
  /** Floating profile / detail panels anchored to the map. */
  profile: 30,
  /** Modal dialogs (e.g. compare, save preset). */
  modal: 50,
} as const;

export type MapZToken = keyof typeof MAP_Z;

/** Stable CSS variable names — paired 1:1 with MAP_Z. */
export const MAP_Z_CSS_VARS: Readonly<Record<MapZToken, string>> = {
  basemap: "--map-z-basemap",
  region: "--map-z-region",
  city: "--map-z-city",
  marker: "--map-z-marker",
  hover: "--map-z-hover",
  control: "--map-z-control",
  toolbar: "--map-z-toolbar",
  legend: "--map-z-legend",
  tooltip: "--map-z-tooltip",
  profile: "--map-z-profile",
  modal: "--map-z-modal",
};

/**
 * Build a CSS string that mirrors MAP_Z into CSS custom properties.
 * Call once at app startup (e.g. in a layout effect) so that ad-hoc
 * styles can reference `--map-z-toolbar` without a Tailwind rebuild.
 */
export function buildMapZCssVars(): string {
  return Object.entries(MAP_Z)
    .map(([key, value]) => `${MAP_Z_CSS_VARS[key as MapZToken]}: ${value};`)
    .join("\n");
}