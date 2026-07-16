"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import type { MetricId, MapViewState, MapFilters, UniversityPOI, MapRegion, NewsArticle } from "@/lib/types";
import type maplibregl from "maplibre-gl";
import { METRIC_DEFINITIONS, METRIC_ORDER } from "@/lib/metrics";
import { MapCanvas } from "./MapCanvas";
import { MetricTabs } from "./MetricTabs";
import { MapLegend } from "./MapLegend";
import { UniversityMarkers, UniversityMapPins } from "./UniversityMarkers";
import { UniversityCard } from "./UniversityCard";
import { CityLayer } from "./CityLayer";
import { CityDetailPanel } from "./CityDetailPanel";
import { CaliforniaRoadLayer } from "./CaliforniaRoadLayer";
import { CityChoroplethLayer } from "./CityChoroplethLayer";
import { buildCityAggregates, getCitiesByState, getStateCenter, getCityMetricDisplay, getCityMetricValue } from "@/lib/city-utils";
import ComparePanel from "./ComparePanel";
import universityData from "@/data/universities.json";
import regionMetrics from "@/data/region-metrics.json";
import STATE_OPTIONS from "@/data/state-options.json";
import {
  Compass,
  PanelLeftOpen,
  PanelLeftClose,
  ChevronRight,
  ExternalLink,
  MapPin,
  DollarSign,
  Shield,
  GraduationCap,
  ChevronUp,
  ChevronDown,
  Calculator,
  Sparkles,
  Users,
} from "lucide-react";

// ═══════════════════════════════════════════════════════════════════
// MapShell — top-level map module orchestrator
// ═══════════════════════════════════════════════════════════════════
//
// Responsibilities:
//  1. Holds the single source of truth for map view state
//     (active metric, selected university, panel visibility).
//  2. Renders the choropleth map canvas with overlays (controls, legend).
//  3. Renders a collapsible sidebar that shows region detail when a
//     region is selected, or the news/article feed by default.
//
// TODO: Persist view state in URL search params (nuqs / next-usequerystate)
// TODO: Connect region detail queries to Supabase when available
// TODO: Replace hardcoded news/articles with live CMS / DB feed
// TODO: Wire metric switching to MapCanvas paint expression updates (Phase 2)

// ── Initial View State ────────────────────────────────────────────

const DEFAULT_VIEW_STATE: Required<MapViewState> = {
  longitude: -98.5,
  latitude: 39.8,
  zoom: 3.5,
  bearing: 0,
  pitch: 0,
  activeMetricId: "income",
  selectedUniversityId: null,
  selectedCampusPoiId: null,
  mode: "map",
  panelOpen: true,
};

// ── Default Filters ───────────────────────────────────────────────

const DEFAULT_FILTERS: MapFilters = {
  rankingTier: null,
  maxCostRmb: null,
  minSafetyScore: null,
  countries: [],
  directFlightOnly: false,
  cssaOnly: false,
};

// ── Region Detail Shape (sidebar when user clicks a choropleth region) ──
// TODO: Replace with real MapRegion from Supabase query

interface SelectedRegionDetail {
  region: MapRegion;
  /** Top universities in this region, ordered by ranking. */
  universities: UniversityPOI[];
}

// ── Props ─────────────────────────────────────────────────────────

interface MapShellProps {
  /** Additional CSS classes applied to the outermost shell wrapper. */
  className?: string;
  /** Called with a snapshot of view state whenever it changes. */
  onViewStateChange?: (state: MapViewState) => void;
  /** Called when the user selects a university POI (pin click). */
  onUniversitySelect?: (poi: UniversityPOI | null) => void;
}

// ═══════════════════════════════════════════════════════════════════
// Component
// ═══════════════════════════════════════════════════════════════════

export function MapShell({
  className,
  onViewStateChange,
  onUniversitySelect,
}: MapShellProps) {
  // ── View State ──────────────────────────────────────────────────

  const [viewState, setViewState] =
    useState<Required<MapViewState>>(DEFAULT_VIEW_STATE);

  const [filters, setFilters] = useState<MapFilters>(DEFAULT_FILTERS);
  const mapRef = useRef<maplibregl.Map | null>(null);

  // ── Sidebar State ───────────────────────────────────────────────

 /** Null = showing news feed; non-null = showing region detail for this FIPS code. */
  const [selectedUniversityId, setSelectedUniversityId] = useState<string | null>(null);
 const [selectedRegionFips, setSelectedRegionFips] = useState<string | null>(null);
  const [cityDrilldownEnabled, setCityDrilldownEnabled] = useState(false);
  const [selectedStateFips, setSelectedStateFips] = useState<string | null>(null);
  const [selectedCityId, setSelectedCityId] = useState<string | null>(null);
  const [pillsOpen, setPillsOpen] = useState(false);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  // TODO: Replace with real region detail fetched from Supabase
  // Expected shape: { region: MapRegion, universities: UniversityPOI[] }
  
  const [regionDetail, setRegionDetail] =
    useState<SelectedRegionDetail | null>(null);

  // TODO: Replace with real news articles from Supabase / CMS
  // Expected shape: NewsArticle[]
  const [newsArticles, setNewsArticles] = useState<NewsArticle[]>(
    MOCK_NEWS_ARTICLES,
  );

  // ── Derived State ───────────────────────────────────────────────

  const activeMetricDef = METRIC_DEFINITIONS[viewState.activeMetricId];

  const allUniversities = useMemo(
    () => universityData.universities as unknown as UniversityPOI[],
    [],
  );

  const selectedUniversity = useMemo(
    () => allUniversities.find((u) => u.id === selectedUniversityId) ?? null,
    [allUniversities, selectedUniversityId],
  );

  const cityAggregates = useMemo(
    () => buildCityAggregates(allUniversities),
    [allUniversities],
  );

  const visibleCities = useMemo(
    () =>
      cityDrilldownEnabled && selectedStateFips
        ? getCitiesByState(selectedStateFips, cityAggregates)
        : [],
    [cityAggregates, cityDrilldownEnabled, selectedStateFips],
  );

  const selectedCity = useMemo(
    () =>
      cityDrilldownEnabled
        ? cityAggregates.find((city) => city.id === selectedCityId) ?? null
        : null,
    [cityAggregates, cityDrilldownEnabled, selectedCityId],
  );

  // ── Handlers ────────────────────────────────────────────────────

  const flyTo = useCallback((longitude: number, latitude: number, zoom = 5.5) => {
    mapRef.current?.flyTo({ center: [longitude, latitude], zoom, duration: 1000 });
  }, []);

  const flyToDefault = useCallback(() => {
    mapRef.current?.flyTo({ center: [-98.5, 39.8], zoom: 3.5, duration: 900 });
  }, []);

  const handleMetricChange = useCallback(
    (metricId: MetricId) => {
      const next = { ...viewState, activeMetricId: metricId };
     setViewState(next);
      setSelectedUniversityId(null);
     onViewStateChange?.(next);
    },
    [viewState, onViewStateChange],
  );

  const handlePanelToggle = useCallback(() => {
    const next = { ...viewState, panelOpen: !viewState.panelOpen };
    setViewState(next);
    onViewStateChange?.(next);
  }, [viewState, onViewStateChange]);

   const addToCompare = useCallback((id: string) => {
    setCompareIds(prev =>
      prev.includes(id) ? prev : [...prev, id].slice(0, 4)
    );
    setCompareOpen(true);
  }, []);

  const removeFromCompare = useCallback((id: string) => {
    setCompareIds(prev => prev.filter(i => i !== id));
  }, []);

  const clearCompare = useCallback(() => {
    setCompareIds([]);
    setCompareOpen(false);
  }, []);

  const handleRegionClick = useCallback(
   (fipsCode: string) => {
     setSelectedRegionFips(fipsCode);
      setSelectedUniversityId(null);
      setSelectedCityId(null);

      if (cityDrilldownEnabled) {
        setSelectedStateFips(fipsCode);
        const center = getStateCenter(fipsCode);
        if (center) flyTo(center[0], center[1], 4.35);
      }

      const stateMetrics = (regionMetrics.records as any[]).filter(
        (r: any) => r.granularity === "state" && r.fipsCode === fipsCode
      );
      if (stateMetrics.length > 0) {
        setRegionDetail({
          region: {
           fipsCode: fipsCode,
           name: stateMetrics[0].name,
           nameEn: stateMetrics[0].nameEn,
            granularity: "state" as any,
            universityCount: allUniversities.filter(
              (u: any) => u.stateFips === fipsCode
            ).length,
            metrics: stateMetrics,
          },
          universities: allUniversities.filter(
            (u: any) => u.id.startsWith(fipsCode) || u.state === stateMetrics[0].nameEn
          ),
        });
        return;
      }
      const mock = MOCK_REGION_DETAIL[fipsCode];
      setRegionDetail(mock ?? null);
    },
    [allUniversities, cityDrilldownEnabled, flyTo],
  );
  const handleCityClick = useCallback((cityId: string) => {
    setSelectedCityId(cityId);
    setSelectedUniversityId(null);
  }, []);

  const handleBackToState = useCallback(() => {
    setSelectedCityId(null);
    setSelectedUniversityId(null);
    if (selectedStateFips) {
      const center = getStateCenter(selectedStateFips);
      if (center) flyTo(center[0], center[1], 4.35);
    }
  }, [flyTo, selectedStateFips]);

  const [showStateDropdown, setShowStateDropdown] = useState(false);
  const handleStateSelect = useCallback((fips: string) => {
    setCityDrilldownEnabled(true);
    setSelectedStateFips(fips);
    setSelectedCityId(null);
    setShowStateDropdown(false);
    const center = getStateCenter(fips);
    if (center) flyTo(center[0], center[1], 6.0);
  }, [flyTo]);

  const handleDrilldownToggle = useCallback(() => {
    setCityDrilldownEnabled((enabled) => {
      const next = !enabled;
      if (!next) {
        setSelectedStateFips(null);
        setSelectedCityId(null);
        flyToDefault();
      } else if (selectedRegionFips) {
        setSelectedStateFips(selectedRegionFips);
        const center = getStateCenter(selectedRegionFips);
        if (center) flyTo(center[0], center[1], 4.35);
      }
      return next;
    });
  }, [flyTo, flyToDefault, selectedRegionFips]);

 const handleSidebarClose = useCallback(() => {
   setSelectedRegionFips(null);
   setSelectedStateFips(null);
   setSelectedCityId(null);
   setRegionDetail(null);
    setSelectedUniversityId(null);
 }, []);

  // ── Render ──────────────────────────────────────────────────────

  return (
    <div
      className={`flex h-full w-full overflow-hidden bg-paper ${className ?? ""}`}
      role="region"
      aria-label="留学地图交互面板"
    >
      {/* ── Map Panel ─────────────────────────────────────────────── */}
      <div className="relative flex flex-1 flex-col min-w-0">
        {/* Compact header bar */}
        <header className="flex shrink-0 items-center gap-3 border-b border-line bg-panel px-5 py-3">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-ink text-panel">
            <Compass aria-hidden="true" size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-base font-semibold text-ink truncate">
              留学地图
            </h1>
            <p className="text-xs text-ink/52 truncate">
              China-lens choropleth — 六大指标覆盖全美
            </p>
          </div>

          {/* Metric Tabs — inline in the header for compactness */}
          <div className="hidden lg:block">
            <MetricTabs
              active={viewState.activeMetricId}
              onSelect={handleMetricChange}
            />
          </div>

          {/* Calculator link */}
          <a href="/match"
            aria-label="智能选校"
            className="grid h-8 w-8 shrink-0 place-items-center rounded-md text-ink/52 transition-colors hover:bg-line/40 hover:text-ink"
          >
            <Sparkles size={18} />
          </a>
          <a href="/calculator"
            aria-label="预算计算器"
            className="grid h-8 w-8 shrink-0 place-items-center rounded-md text-ink/52 transition-colors hover:bg-line/40 hover:text-ink"
          >
            <Calculator size={18} />
          </a>
          {/* Panel toggle button */}
          <button
            type="button"
            onClick={handlePanelToggle}
            aria-label={viewState.panelOpen ? "关闭侧边栏" : "打开侧边栏"}
            className="grid h-8 w-8 shrink-0 place-items-center rounded-md text-ink/52 transition-colors hover:bg-line/40 hover:text-ink"
          >
            {viewState.panelOpen ? (
              <PanelLeftClose size={18} />
            ) : (
              <PanelLeftOpen size={18} />
            )}
          </button>
        </header>

        {/* Mobile metric tabs dropdown — visible below lg breakpoint */}
        <div className="lg:hidden border-b border-line bg-panel/60 px-4 py-2">
          <MetricTabs
            active={viewState.activeMetricId}
            onSelect={handleMetricChange}
          />
        </div>

        {/* Map canvas — fills remaining space */}
        <div className="relative flex flex-col flex-1 min-h-0">
          <MapCanvas
            className="flex-1 min-h-0"
            activeMetricId={viewState.activeMetricId}
            onRegionClick={handleRegionClick}
            onMapInit={(map) => { mapRef.current = map; }}
          >
             <UniversityMapPins
               universities={allUniversities}
               onSelect={(id) => {
                 if (id && compareOpen) {
                   addToCompare(id);
                 } else {
                   setSelectedUniversityId(id);
                 }
               }}
               selectedId={selectedUniversityId}
               pinMinZoom={cityDrilldownEnabled ? 7.6 : 0}
             />
             {selectedStateFips === "06" && (
               <CaliforniaRoadLayer enabled cities={visibleCities} />
             )}
             {cityDrilldownEnabled && (
               <CityLayer
                 visibleCities={visibleCities}
                 activeMetricId={viewState.activeMetricId}
                 onCityClick={handleCityClick}
                 selectedCityId={selectedCityId}
               />
             )}
           </MapCanvas>
          {/* ── University pill strip — collapsible ── */}
          {pillsOpen ? (
            <div className="shrink-0 border-t border-line bg-panel px-3 py-2 overflow-x-auto" role="navigation" aria-label="大学列表">
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-ink/40">{allUniversities.length} 所大学</span>
                  <button
                    onClick={() => setCompareOpen(v => !v)}
                    className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${
                      compareOpen ? "bg-cobalt/10 text-cobalt" : "text-ink/36 hover:text-ink hover:bg-ink/5"
                    }`}
                  >
                    对比 {compareIds.length > 0 ? `(${compareIds.length})` : ""}
                  </button>
                </div>
                <button
                  onClick={() => setPillsOpen(false)}
                  className="rounded p-0.5 text-ink/36 hover:text-ink hover:bg-ink/5 transition-colors"
                  aria-label="收起大学列表"
                >
                  <ChevronDown size={14} />
                </button>
              </div>
              <UniversityMarkers
                universities={allUniversities}
                onSelect={(id) => {
                  if (id && compareOpen) {
                    addToCompare(id);
                  } else {
                    setSelectedUniversityId(id);
                  }
                }}
                selectedId={selectedUniversityId}
              />
            </div>
         ) : (
            <div className="shrink-0 border-t border-line bg-panel flex items-center justify-between px-3">
              <button
                onClick={() => setPillsOpen(true)}
                className="flex items-center gap-1 py-1.5 text-xs text-ink/44 hover:text-ink transition-colors"
                aria-label="展开大学列表"
              >
                <GraduationCap size={11} />
                <span>{allUniversities.length} 所大学</span>
                <ChevronUp size={11} />
              </button>
              <button
                onClick={() => setCompareOpen(v => !v)}
                className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${
                  compareOpen ? "bg-cobalt/10 text-cobalt" : "text-ink/36 hover:text-ink hover:bg-ink/5"
                }`}
              >
                对比 {compareIds.length > 0 ? `(${compareIds.length})` : ""}
              </button>
            </div>
          )}
            { (compareOpen || compareIds.length > 0) && (
            <ComparePanel
              universities={allUniversities}
              selectedIds={compareIds}
              onRemove={removeFromCompare}
              onClear={clearCompare}
              onClose={() => { setCompareIds([]); setCompareOpen(false); }}
            />
          )}
          {selectedUniversity && (
            <div className="absolute inset-0 z-30 flex items-center justify-center bg-ink/20 backdrop-blur-sm" onClick={() => setSelectedUniversityId(null)}>
              <div onClick={(e) => e.stopPropagation()} className="max-h-[85vh] overflow-y-auto rounded-xl shadow-xl">
                <UniversityCard
                  poi={selectedUniversity as any}
                  onClose={() => setSelectedUniversityId(null)}
                />
              </div>
            </div>
          )}
          {/* Granularity/drill-down controls overlay */}
          <div className="absolute right-3 top-3 z-10 flex items-center gap-2">
            <button
              type="button"
              onClick={handleDrilldownToggle}
              className={`rounded-full border px-2.5 py-1 text-[11px] font-medium shadow-sm backdrop-blur transition-colors ${
                cityDrilldownEnabled
                  ? "border-cobalt/35 bg-cobalt text-white"
                  : "border-line bg-white/88 text-ink/64 hover:bg-white hover:text-ink"
              }`}
              aria-pressed={cityDrilldownEnabled}
            >
              城市下钻{cityDrilldownEnabled ? "已开" : ""}
            </button>
            <span className="pointer-events-none rounded-full border border-line bg-white/88 px-2.5 py-1 text-[11px] font-medium text-ink/64 backdrop-blur">
              {selectedCity ? "城市详情" : cityDrilldownEnabled && selectedStateFips ? selectedStateFips + " 城市级" : "州级色块图"}
            </span>
          </div>

          {cityDrilldownEnabled && selectedStateFips && visibleCities.length > 0 && (
            <div className="absolute left-4 top-4 z-10 w-[280px] rounded-xl border border-line bg-white/92 p-3 text-xs shadow-panel backdrop-blur">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div>
                  <div className="font-semibold text-ink">城市级数据</div>
                  <div className="text-[11px] text-ink/48">{activeMetricDef.label} · {visibleCities.length} 个城市</div>
                </div>
                <span className="rounded-full bg-cobalt/10 px-2 py-0.5 text-[10px] font-medium text-cobalt">City Layer</span>
              </div>
              <ol className="space-y-1.5">
                {[...visibleCities]
                  .sort((a, b) => getCityMetricValue(b, viewState.activeMetricId) - getCityMetricValue(a, viewState.activeMetricId))
                  .slice(0, 5)
                  .map((city, index) => (
                    <li key={city.id}>
                      <button
                        type="button"
                        onClick={() => handleCityClick(city.id)}
                        className={`flex w-full items-center justify-between gap-2 rounded-lg border px-2 py-1.5 text-left transition-colors ${
                          selectedCity?.id === city.id
                            ? "border-cobalt/35 bg-cobalt/8"
                            : "border-line/60 bg-white/70 hover:border-cobalt/25 hover:bg-cobalt/[0.03]"
                        }`}
                      >
                        <span className="min-w-0">
                          <span className="mr-1 text-ink/36">#{index + 1}</span>
                          <span className="font-medium text-ink">{city.nameZh}</span>
                          <span className="ml-1 text-ink/40">{city.universityCount}所</span>
                        </span>
                        <span className="shrink-0 font-semibold text-ink">{getCityMetricDisplay(city, viewState.activeMetricId)}</span>
                      </button>
                    </li>
                  ))}
              </ol>
              <p className="mt-2 rounded-lg bg-paper px-2 py-1.5 text-[10px] leading-relaxed text-ink/44">
                当前为城市聚合数据层；真实市级收入/道路/边界可继续接入 ACS city metrics 与 city roads GeoJSON。
              </p>
            </div>
          )}
          {/* Map legend overlay */}
          <div className="absolute bottom-4 left-4 z-10 pointer-events-none">
            <div className="pointer-events-auto">
              <MapLegend metric={activeMetricDef} />
            </div>
          </div>
        </div>
      </div>

      {/* ── Sidebar Panel ─────────────────────────────────────────── */}
      <aside
        aria-label="侧边栏信息面板"
        className={`flex shrink-0 flex-col border-l border-line bg-panel transition-all duration-300 ease-in-out ${
          viewState.panelOpen ? "w-[360px]" : "w-0 overflow-hidden border-l-0"
        }`}
      >
        <div className="flex h-full w-[360px] flex-col">
          {selectedCity ? (
            <CityDetailPanel
              city={selectedCity}
              onBack={handleBackToState}
              onUniversitySelect={setSelectedUniversityId}
              selectedUniversityId={selectedUniversityId}
              onAddToCompare={addToCompare}
            />
          ) : selectedRegionFips && regionDetail ? (
            <RegionDetailSidebar
              detail={regionDetail}
              activeMetricId={viewState.activeMetricId}
              onClose={handleSidebarClose}
            />
          ) : (
            <NewsFeedSidebar articles={newsArticles} />
          )}
        </div>
      </aside>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// RegionDetailSidebar — shown when a choropleth region is clicked
// ═══════════════════════════════════════════════════════════════════

function RegionDetailSidebar({
  detail,
  activeMetricId,
  onClose,
}: {
  detail: SelectedRegionDetail;
  activeMetricId: MetricId;
  onClose: () => void;
}) {
  const { region, universities } = detail;
  const activeMetric = region.metrics.find((m) => m.metricId === activeMetricId);
  const metricDef = METRIC_DEFINITIONS[activeMetricId];

  return (
    <>
      {/* Sidebar header */}
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold text-ink">
            {region.name}
          </h2>
          <p className="text-xs text-ink/48">{region.nameEn}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="关闭区域详情"
          className="grid h-7 w-7 shrink-0 place-items-center rounded text-ink/44 transition-colors hover:bg-line/40 hover:text-ink"
        >
          <ChevronRight size={16} />
        </button>
      </div>

      {/* Metric summary cards */}
      <div className="border-b border-line px-4 py-3">
        <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-ink/44">
          指标概览
        </h3>
        <div className="grid grid-cols-2 gap-2">
          {region.metrics.slice(0, 6).map((m) => {
            const def = METRIC_DEFINITIONS[m.metricId];
            const isActive = m.metricId === activeMetricId;
            return (
              <div
                key={m.metricId}
                className={`rounded-md border px-3 py-2 text-xs transition-colors ${
                  isActive
                    ? "border-cobalt/30 bg-cobalt/5"
                    : "border-line/60 bg-white/60"
                }`}
              >
                <div className="text-ink/48">{def.label}</div>
                <div className="mt-0.5 text-sm font-semibold text-ink">
                  {m.displayValue}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* University list */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-ink/44">
          该区域大学
          <span className="ml-1.5 rounded bg-ink/8 px-1.5 py-0.5 text-[10px]">
            {universities.length}
          </span>
        </h3>
        {universities.length === 0 ? (
          <p className="text-xs text-ink/40 italic">
            {/* TODO: Connect to Supabase when available */}
            暂无大学数据
          </p>
        ) : (
          <ul className="space-y-2" role="list">
            {universities.map((uni) => (
              <li
                key={uni.id}
                className="rounded-lg border border-line/70 bg-white px-3 py-2.5 text-xs transition-colors hover:border-cobalt/30 hover:bg-cobalt/[0.03]"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate font-medium text-ink">
                      {uni.chineseName}
                    </div>
                    <div className="truncate text-ink/52">{uni.name}</div>
                  </div>
                  <span className="shrink-0 rounded-full bg-ink/8 px-1.5 py-0.5 text-[10px] font-medium text-ink/56">
                    {uni.rankingBand}
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-ink/48">
                  <span className="inline-flex items-center gap-1">
                    <DollarSign size={10} />
                    ¥{(uni.annualCostRmb / 10000).toFixed(1)}万/年
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Shield size={10} />
                    {uni.safetyScore}分
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}

// ═══════════════════════════════════════════════════════════════════
// NewsFeedSidebar — default sidebar content with articles feed
// ═══════════════════════════════════════════════════════════════════

function NewsFeedSidebar({ articles }: { articles: NewsArticle[] }) {
  return (
    <>
      {/* Sidebar header */}
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-sm font-semibold text-ink">留学资讯</h2>
        <p className="text-xs text-ink/48">最新动态与政策解读</p>
      </div>

      {/* Article list */}
      <div className="flex-1 overflow-y-auto">
        {articles.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 px-4 py-12 text-center">
            <p className="text-sm text-ink/40">
              {/* TODO: Connect to Supabase when available */}
              暂无资讯
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-line/60" role="list">
            {articles.map((article) => (
              <li key={article.id}>
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block px-4 py-3 transition-colors hover:bg-ink/[0.03] group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="flex-1 text-xs font-medium leading-snug text-ink group-hover:text-cobalt transition-colors">
                      {article.title}
                    </h3>
                    <ExternalLink
                      size={12}
                      className="shrink-0 mt-0.5 text-ink/24 group-hover:text-cobalt/60 transition-colors"
                    />
                  </div>
                  <p className="mt-1 text-[11px] leading-relaxed text-ink/52 line-clamp-2">
                    {article.summary}
                  </p>
                  <div className="mt-2 flex items-center gap-2 text-[10px] text-ink/36">
                    <span>{article.source}</span>
                    <span aria-hidden="true">·</span>
                    <time dateTime={article.publishedAt}>
                      {formatRelativeDate(article.publishedAt)}
                    </time>
                    <span
                      className="ml-auto rounded-full bg-ink/6 px-1.5 py-0.5 text-[10px]"
                      aria-label={`分类: ${article.category}`}
                    >
                      {NEWS_CATEGORY_LABELS[article.category] ?? article.category}
                    </span>
                  </div>
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}

// ═══════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════

const NEWS_CATEGORY_LABELS: Record<string, string> = {
  admissions: "招生",
  visa: "签证",
  ranking: "排名",
  life: "生活",
  career: "就业",
  policy: "政策",
};

/** Simple relative date formatter (Chinese labels).
 *  TODO: Replace with a proper i18n date library (dayjs / date-fns). */
function formatRelativeDate(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;

  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 60) return `${Math.max(1, minutes)}分钟前`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;

  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}天前`;

  const months = Math.floor(days / 30);
  return `${months}个月前`;
}

// ═══════════════════════════════════════════════════════════════════
// Mock Data — to be replaced with Supabase / CMS
// ═══════════════════════════════════════════════════════════════════
//
// TODO: Replace with real {news, article} data
// TODO: Connect to Supabase when available
//
// Expected Supabase query shape:
//   SELECT id, title, title_en, summary, source, url, published_at, category
//     FROM news_articles
//    ORDER BY published_at DESC
//    LIMIT 20;

const MOCK_NEWS_ARTICLES: NewsArticle[] = [
  {
    id: "news-001",
    title: "2026年H-1B签证新规解读：对中国留学生的影响",
    titleEn: "2026 H-1B Visa Changes: Impact on Chinese Students",
    summary: "美国移民局发布2026年度H-1B签证最新政策，STEM专业优势进一步扩大，对中国留学生总体利好。",
    source: "EIC Education",
    url: "#",
    publishedAt: "2026-07-08T10:00:00Z",
    category: "visa",
  },
  {
    id: "news-002",
    title: "US News 2027全球大学排名提前泄露：亚洲高校表现亮眼",
    titleEn: "US News 2027 Rankings Leak: Asian Universities Shine",
    summary: "US News 2027全球大学排名中，新加坡国立大学首次进入全球前十，清北排名持续上升。",
    source: "US News",
    url: "#",
    publishedAt: "2026-07-07T14:30:00Z",
    category: "ranking",
  },
  {
    id: "news-003",
    title: "加州大学系统宣布扩招国际学生：2027秋季入学名额增加15%",
    titleEn: "UC System Expands International Enrollment by 15% for Fall 2027",
    summary: "加州大学伯克利、洛杉矶、圣地亚哥等校区将大幅增加国际学生录取名额，中国学生为最大受益群体。",
    source: "UC Newsroom",
    url: "#",
    publishedAt: "2026-07-06T08:15:00Z",
    category: "admissions",
  },
  {
    id: "news-004",
    title: "留学生活成本排行2026：纽约仍居榜首，德州城市性价比突出",
    titleEn: "2026 Cost of Living Rankings for International Students",
    summary: "最新留学生活成本数据显示，纽约、旧金山、波士顿继续占据前三，休斯顿、达拉斯性价比最优。",
    source: "QS",
    url: "#",
    publishedAt: "2026-07-05T16:45:00Z",
    category: "life",
  },
  {
    id: "news-005",
    title: "STEM OPT延期政策更新：2026年新增AI与量子计算方向",
    titleEn: "STEM OPT Extension Adds AI and Quantum Computing Fields for 2026",
    summary: "美国国土安全部将人工智能、量子计算等新兴领域纳入STEM OPT延期目录，相关专业毕业生可获36个月OPT。",
    source: "DHS",
    url: "#",
    publishedAt: "2026-07-04T09:00:00Z",
    category: "career",
  },
  {
    id: "news-006",
    title: "英国毕业生签证政策收紧：2027年起最低薪资门槛上调至3万英镑",
    titleEn: "UK Graduate Visa Tightens: Minimum Salary Threshold Rises to £30K from 2027",
    summary: "英国内政部宣布2027年起毕业生签证转工签的最低薪资要求从£26,200提高至£30,000，中国学生需提前规划。",
    source: "UK Home Office",
    url: "#",
    publishedAt: "2026-07-03T11:20:00Z",
    category: "policy",
  },
];

// ── Mock Region Detail ────────────────────────────────────────────
//
// TODO: Replace with real region detail from Supabase:
//
//   SELECT r.*, array_agg(json_build_object(...)) as universities
//     FROM map_regions r
//     LEFT JOIN universities u ON u.region_fips = r.fips_code
//    WHERE r.fips_code = $1
//    GROUP BY r.fips_code;

const MOCK_REGION_DETAIL: Record<string, SelectedRegionDetail> = {
  "06": {
    region: {
      fipsCode: "06",
      name: "加利福尼亚州",
      nameEn: "California",
      granularity: "state",
      metrics: [
        {
          fipsCode: "06",
          granularity: "state",
          metricId: "income",
          value: 0.9,
          rawValue: 135000,
          displayValue: "$135k",
          year: 2025,
        },
        {
          fipsCode: "06",
          granularity: "state",
          metricId: "safety",
          value: 0.55,
          rawValue: 450,
          displayValue: "450/100k",
          year: 2025,
        },
        {
          fipsCode: "06",
          granularity: "state",
          metricId: "employment",
          value: 0.82,
          rawValue: 89,
          displayValue: "89分",
          year: 2025,
        },

        {
          fipsCode: "06",
          granularity: "state",
          metricId: "cost",
          value: 0.92,
          rawValue: 427000,
          displayValue: "¥43万",
          year: 2025,
        },
        {
          fipsCode: "06",
          granularity: "state",
          metricId: "admission_rate",
          value: 0.2,
          rawValue: 26,
          displayValue: "26.0%",
          year: 2025,
        },
        {
          fipsCode: "06",
          granularity: "state",
          metricId: "chinese_population",
          value: 0.95,
          rawValue: 14.3,
          displayValue: "14.3%",
          year: 2025,
        },
      ],
      universityCount: 3,
    },
    universities: [
      {
        id: "stanford",
        name: "Stanford University",
        chineseName: "斯坦福大学",
        country: "United States",
        city: "Stanford",
        latitude: 37.4275,
        longitude: -122.1697,
        rankingBand: "Global Top 5",
        rankingTier: "top20",
        annualCostRmb: 620000,
        safetyScore: 88,
        recognitionScore: 98,
        chineseCommunity: "medium",
        directFlight: true,
        postStudyVisa: "OPT / STEM OPT",
        programs: ["Computer Science", "Engineering", "Business", "Law"],
        parentHighlights: ["顶级学术声誉", "硅谷核心位置", "强大校友网络"],
        studentHighlights: ["创新氛围浓厚", "多元文化校园", "丰富研究机会"],
        verifiedAt: "2026-07-01",
        sourceCount: 12,
        campusImages: [],
        nearby: {
          subwayStations: 2,
          chineseRestaurants: 8,
          asianGroceries: 3,
          avgRentRmb: 22000,
        },
      },
      {
        id: "berkeley",
        name: "University of California, Berkeley",
        chineseName: "加州大学伯克利分校",
        country: "United States",
        city: "Berkeley",
        latitude: 37.8719,
        longitude: -122.2585,
        rankingBand: "Global Top 10",
        rankingTier: "top20",
        annualCostRmb: 520000,
        safetyScore: 72,
        recognitionScore: 96,
        chineseCommunity: "high",
        directFlight: true,
        postStudyVisa: "OPT / STEM OPT",
        programs: ["Computer Science", "Data Science", "Engineering", "Economics"],
        parentHighlights: ["公立常春藤", "硅谷人才输送", "中国学生多"],
        studentHighlights: ["湾区就业优势", "学术自由氛围", "社团活动丰富"],
        verifiedAt: "2026-07-02",
        sourceCount: 11,
        campusImages: [],
        nearby: {
          subwayStations: 1,
          chineseRestaurants: 12,
          asianGroceries: 4,
          avgRentRmb: 18500,
        },
      },
      {
        id: "ucla",
        name: "University of California, Los Angeles",
        chineseName: "加州大学洛杉矶分校",
        country: "United States",
        city: "Los Angeles",
        latitude: 34.0689,
        longitude: -118.4452,
        rankingBand: "Global Top 15",
        rankingTier: "top20",
        annualCostRmb: 500000,
        safetyScore: 76,
        recognitionScore: 94,
        chineseCommunity: "high",
        directFlight: true,
        postStudyVisa: "OPT / STEM OPT",
        programs: ["Film", "Business", "Engineering", "Life Sciences"],
        parentHighlights: ["中国知名度极高", "洛杉矶华人圈成熟", "全美最多申请校"],
        studentHighlights: ["阳光海岸生活", "娱乐产业资源", "多元化环境"],
        verifiedAt: "2026-07-03",
        sourceCount: 10,
        campusImages: [],
        nearby: {
          subwayStations: 3,
          chineseRestaurants: 25,
          asianGroceries: 7,
          avgRentRmb: 20000,
        },
      },
    ],
  },
};




