import type { Granularity } from "@/lib/types";
import { ZoomIn } from "lucide-react";

// ── Granularity metadata ──────────────────────────────────────
// Maps each Granularity value to its Chinese label and a short
// English fallback.  Used by the badge and by other zoom‑aware
// UI (tooltips, sidebar region headers, etc.).

const GRANULARITY_LABELS: Record<
  Granularity,
  { label: string; labelEn: string }
> = {
  state: { label: "州级", labelEn: "State" },
  county: { label: "县级", labelEn: "County" },
  city: { label: "市级", labelEn: "City" },
};

// ── Zoom thresholds ───────────────────────────────────────────
// The choropleth source toggles between state / county / city
// tilesets based on these breakpoints.  Copied here so the
// badge stays in sync with the map engine without importing
// MapLibre internals.

/** MapLibre zoom level at or above which counties replace states. */
const ZOOM_COUNTY_THRESHOLD = 7;

/** MapLibre zoom level at or above which cities replace counties. */
const ZOOM_CITY_THRESHOLD = 10;

// ── Props ─────────────────────────────────────────────────────

interface GranularityBadgeProps {
  /**
   * Current MapLibre zoom level (0‑22).
   *
   * TODO: Replace with real zoom value from map viewport state
   *       — read from `useMap()` or `MapViewState.zoom`.
   */
  zoom: number;

  /**
   * Explicit granularity override.  When provided the badge uses
   * this value directly; otherwise it derives granularity from
   * the `zoom` prop using the thresholds above.
   *
   * TODO: Connect to Supabase when available — the backend may
   *       dictate granularity per region independent of zoom.
   */
  granularity?: Granularity;
}

// ── Helpers ───────────────────────────────────────────────────

/**
 * Derive the current granularity from a MapLibre zoom level.
 *
 * Matches the choropleth‑map source‑selection logic so the badge
 * always reflects the tileset actually being rendered.
 */
function granularityFromZoom(zoom: number): Granularity {
  if (zoom >= ZOOM_CITY_THRESHOLD) return "city";
  if (zoom >= ZOOM_COUNTY_THRESHOLD) return "county";
  return "state";
}

// ── Component ─────────────────────────────────────────────────

/**
 * `GranularityBadge`
 *
 * A small pill displayed in the map toolbar that tells the user
 * which geographic resolution the choropleth is currently showing:
 * 州级 (state), 县级 (county), or 市级 (city).
 *
 * It updates reactively as the user zooms in / out so they always
 * know the data granularity beneath the cursor.
 *
 * Usage:
 * ```tsx
 * <GranularityBadge zoom={mapViewState.zoom ?? 4} />
 * <GranularityBadge granularity="county" />
 * ```
 */
export function GranularityBadge({ zoom, granularity }: GranularityBadgeProps) {
  const resolved: Granularity = granularity ?? granularityFromZoom(zoom);
  const { label, labelEn } = GRANULARITY_LABELS[resolved];

  return (
    <div
      role="status"
      aria-label={`当前地图粒度: ${label} (${labelEn})`}
      className="pointer-events-auto inline-flex items-center gap-1.5 rounded-full border border-line bg-white/94 px-3 py-1.5 text-xs font-medium text-ink/72 shadow-panel backdrop-blur"
    >
      {/* Icon — subtle magnifying glass reusing lucide-react */}
      <ZoomIn
        aria-hidden
        className="h-3.5 w-3.5 shrink-0 text-ink/40"
        strokeWidth={1.8}
      />

      {/* Primary Chinese label */}
      <span className="leading-none">{label}</span>

      {/* English fallback — muted, narrower tracking */}
      <span
        aria-hidden
        className="hidden text-[10px] font-normal tracking-wide text-ink/36 sm:inline"
      >
        {labelEn}
      </span>

      {/* Dot indicator — colour communicates granularity depth */}
      <span
        aria-hidden
        className={`ml-0.5 inline-block h-1.5 w-1.5 rounded-full ${
          resolved === "city"
            ? "bg-jade"
            : resolved === "county"
            ? "bg-cobalt"
            : "bg-persimmon"
        }`}
      />
    </div>
  );
}
