"use client";

// PathOS Stage 7B-A.1 — Unified Map Toolbar
//
// One and only one floating toolbar that sits at the top-right of the
// map. Consolidates:
//   • RegionalLayerControl (region heatmap selector)
//   • StateSelector        (drill-down to a single state)
//   • ViewModeBadge        (州级 / 城市级 / 城市详情 indicator)
// into a single `flex flex-wrap` row. The legacy 5-button row that
// used to sit at the top of the page (and the mobile sub-bar) is
// gone — see the Stage 7B-A.1 plan for the full rationale.

import { useState, useRef, useEffect } from "react";
import { ChevronDown } from "lucide-react";
import { RegionalLayerControl } from "@/components/map/regional/RegionalLayerControl";
import type { RegionalMetricId } from "@/regional/types";

export interface StateOption {
  fipsCode: string;
  name: string;
  nameEn: string;
}

export interface MapToolbarProps {
  /** Regional heatmap selector — null means no heatmap. */
  activeRegionalMetric: RegionalMetricId | null;
  setActiveRegionalMetric: (next: RegionalMetricId | null) => void;

  /** State drill-down. */
  cityDrilldownEnabled: boolean;
  selectedStateFips: string | null;
  onSelectState: (fipsCode: string) => void;
  stateOptions: ReadonlyArray<StateOption>;

  /** Status indicator (州级色块图 / 城市级 N 所大学 / 城市详情). */
  viewModeLabel: string;
}

/** Collapse the state dropdown on outside click. */
function useOutsideClose(
  ref: React.RefObject<HTMLElement>,
  onClose: () => void,
  active: boolean,
): void {
  useEffect(() => {
    if (!active) return;
    function handle(ev: MouseEvent): void {
      const el = ref.current;
      if (!el) return;
      if (ev.target instanceof Node && !el.contains(ev.target)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [ref, onClose, active]);
}

export function MapToolbar({
  activeRegionalMetric,
  setActiveRegionalMetric,
  cityDrilldownEnabled,
  selectedStateFips,
  onSelectState,
  stateOptions,
  viewModeLabel,
}: MapToolbarProps): JSX.Element {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  useOutsideClose(dropdownRef, () => setDropdownOpen(false), dropdownOpen);

  const selectedName = selectedStateFips
    ? stateOptions.find((s) => s.fipsCode === selectedStateFips)?.name ?? selectedStateFips
    : null;

  return (
    <div
      data-testid="map-toolbar"
      role="toolbar"
      aria-label="地图工具栏"
      className={`absolute right-3 top-3 flex max-w-[calc(100vw-1.5rem)] flex-wrap items-center gap-2 ${
        dropdownOpen ? "z-map-tooltip" : "z-map-toolbar"
      }`}
    >
      {/* 1. Regional heatmap selector — the only entry point. */}
      <RegionalLayerControl
        value={activeRegionalMetric}
        onChange={setActiveRegionalMetric}
      />

      {/* 2. State drill-down selector. */}
      <div
        ref={dropdownRef}
        className="relative min-w-0 max-[359px]:w-full"
      >
        <button
          type="button"
          data-testid="state-selector-button"
          onClick={() => setDropdownOpen((v) => !v)}
          aria-haspopup="listbox"
          aria-expanded={dropdownOpen}
          aria-pressed={cityDrilldownEnabled}
          className={`flex max-w-[140px] items-center gap-1 rounded-control border px-2.5 py-1 text-[11px] font-medium shadow-sm backdrop-blur transition-colors ${
            cityDrilldownEnabled
              ? "border-cobalt/35 bg-cobalt text-white"
              : "border-border-soft bg-surface-1/95 text-text-secondary hover:bg-surface-1 hover:text-text-primary"
          }`}
        >
          <span className="truncate">{selectedName ?? "选择州"}</span>
          <ChevronDown size={11} aria-hidden="true" className="shrink-0" />
        </button>
        {dropdownOpen && (
          <div
            data-testid="state-selector-dropdown"
            role="listbox"
            aria-label="选择一个州查看城市级数据"
            className="absolute right-0 top-full z-map-control mt-1 max-h-[320px] w-[240px] overflow-y-auto rounded-card border border-border-soft bg-surface-1 shadow-pop backdrop-blur-sm max-[359px]:left-0 max-[359px]:right-auto"
          >
            <div className="border-b border-border-soft px-3 py-2 text-[10px] font-semibold text-text-secondary">
              选择一个州查看城市级数据
            </div>
            <div className="py-1">
              {stateOptions.map((st) => (
                <button
                  key={st.fipsCode}
                  type="button"
                  role="option"
                  aria-selected={selectedStateFips === st.fipsCode}
                  onClick={() => {
                    onSelectState(st.fipsCode);
                    setDropdownOpen(false);
                  }}
                  className={`flex w-full items-center gap-3 px-3 py-1.5 text-left text-xs transition-colors hover:bg-cobalt/10 ${
                    selectedStateFips === st.fipsCode
                      ? "bg-cobalt/10 font-medium text-cobalt"
                      : "text-text-primary"
                  }`}
                >
                  <span className="w-6 text-center text-[10px] text-text-muted">
                    {st.fipsCode}
                  </span>
                  <span>{st.name}</span>
                  <span className="ml-auto text-[10px] text-text-muted">
                    {st.nameEn}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 3. View-mode indicator (status pill, not interactive). */}
      <span
        data-testid="map-toolbar-view-mode"
        aria-live="polite"
        className="pointer-events-none rounded-control border border-border-soft bg-surface-1/95 px-2.5 py-1 text-[11px] font-medium text-text-secondary backdrop-blur"
      >
        {viewModeLabel}
      </span>
    </div>
  );
}
