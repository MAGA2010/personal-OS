"use client";

import type { UniversityPOI, RankingTier, ChineseCommunityLevel } from "@/lib/types";
import type { ReactNode } from "react";
import {
  ArrowDownAZ,
  DollarSign,
  Filter,
  GraduationCap,
  Plane,
  RotateCcw,
  Search,
  Shield,
  SlidersHorizontal,
  Users,
  X,
} from "lucide-react";

export type AdmissionSelectivity = "all" | "reach" | "target" | "likely";
export type UniversitySortKey = "recommended" | "cost" | "safety" | "admission" | "name";

export interface StrongMapFilters {
  searchQuery: string;
  rankingTier: RankingTier | null;
  maxCostRmb: number | null;
  minSafetyScore: number | null;
  chineseCommunityLevels: ChineseCommunityLevel[];
  admissionSelectivity: AdmissionSelectivity;
  stateCodes: string[];
  directFlightOnly: boolean;
  sortBy: UniversitySortKey;
}

interface MapFilterPanelProps {
  filters: StrongMapFilters;
  universities: UniversityPOI[];
  resultCount: number;
  totalCount: number;
  onChange: (next: StrongMapFilters) => void;
  onReset: () => void;
}

const RANKING_OPTIONS: Array<{ label: string; value: RankingTier | null }> = [
  { label: "全部", value: null },
  { label: "Top 20", value: "top20" },
  { label: "Top 50", value: "top50" },
  { label: "Top 100", value: "top100" },
  { label: "其他", value: "other" },
];

const COST_OPTIONS: Array<{ label: string; value: number | null }> = [
  { label: "全部", value: null },
  { label: "50万内", value: 500000 },
  { label: "60万内", value: 600000 },
  { label: "80万内", value: 800000 },
];

const ADMISSION_OPTIONS: Array<{ label: string; value: AdmissionSelectivity }> = [
  { label: "全部", value: "all" },
  { label: "挑战", value: "reach" },
  { label: "匹配", value: "target" },
  { label: "稳妥", value: "likely" },
];

const COMMUNITY_OPTIONS: Array<{ label: string; value: ChineseCommunityLevel }> = [
  { label: "华人多", value: "high" },
  { label: "适中", value: "medium" },
  { label: "较少", value: "low" },
];

const SORT_OPTIONS: Array<{ label: string; value: UniversitySortKey }> = [
  { label: "综合", value: "recommended" },
  { label: "费用低", value: "cost" },
  { label: "安全高", value: "safety" },
  { label: "录取友好", value: "admission" },
  { label: "A-Z", value: "name" },
];

export const DEFAULT_STRONG_MAP_FILTERS: StrongMapFilters = {
  searchQuery: "",
  rankingTier: null,
  maxCostRmb: null,
  minSafetyScore: null,
  chineseCommunityLevels: [],
  admissionSelectivity: "all",
  stateCodes: [],
  directFlightOnly: false,
  sortBy: "recommended",
};

export function countActiveFilters(filters: StrongMapFilters): number {
  let count = 0;
  if (filters.searchQuery.trim()) count += 1;
  if (filters.rankingTier) count += 1;
  if (filters.maxCostRmb) count += 1;
  if (filters.minSafetyScore) count += 1;
  if (filters.chineseCommunityLevels.length > 0) count += 1;
  if (filters.admissionSelectivity !== "all") count += 1;
  if (filters.stateCodes.length > 0) count += 1;
  if (filters.directFlightOnly) count += 1;
  return count;
}

export function MapFilterPanel({
  filters,
  universities,
  resultCount,
  totalCount,
  onChange,
  onReset,
}: MapFilterPanelProps) {
  const activeCount = countActiveFilters(filters);
  const states = getTopStates(universities);

  const update = <K extends keyof StrongMapFilters>(key: K, value: StrongMapFilters[K]) => {
    onChange({ ...filters, [key]: value });
  };

  const toggleCommunity = (level: ChineseCommunityLevel) => {
    const next = filters.chineseCommunityLevels.includes(level)
      ? filters.chineseCommunityLevels.filter((item) => item !== level)
      : [...filters.chineseCommunityLevels, level];
    update("chineseCommunityLevels", next);
  };

  const toggleState = (stateCode: string) => {
    const next = filters.stateCodes.includes(stateCode)
      ? filters.stateCodes.filter((item) => item !== stateCode)
      : [...filters.stateCodes, stateCode];
    update("stateCodes", next);
  };

  return (
    <section className="border-b border-line bg-panel px-4 py-3" aria-label="地图筛选">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-ink text-panel">
            <Filter size={15} aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-ink">筛选学校</h2>
            <p className="text-[11px] text-ink/44">
              {resultCount} / {totalCount} 所
              {activeCount > 0 ? ` · ${activeCount} 个条件` : ""}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onReset}
          disabled={activeCount === 0 && filters.sortBy === "recommended"}
          className="inline-flex h-7 items-center gap-1 rounded-md px-2 text-[11px] font-medium text-ink/48 transition-colors hover:bg-line/40 hover:text-ink disabled:cursor-default disabled:opacity-35 disabled:hover:bg-transparent disabled:hover:text-ink/48"
        >
          <RotateCcw size={12} aria-hidden="true" />
          重置
        </button>
      </div>

      <label className="relative block">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink/36" size={14} />
        <input
          value={filters.searchQuery}
          onChange={(event) => update("searchQuery", event.target.value)}
          placeholder="搜索学校、城市或州"
          className="h-9 w-full rounded-md border border-line bg-white/70 pl-8 pr-8 text-sm text-ink outline-none transition-colors placeholder:text-ink/32 focus:border-cobalt/50 focus:bg-white focus:ring-2 focus:ring-cobalt/10"
        />
        {filters.searchQuery && (
          <button
            type="button"
            onClick={() => update("searchQuery", "")}
            className="absolute right-2 top-1/2 grid h-5 w-5 -translate-y-1/2 place-items-center rounded text-ink/36 transition-colors hover:bg-line/50 hover:text-ink"
            aria-label="清空搜索"
          >
            <X size={12} />
          </button>
        )}
      </label>

      <div className="mt-3 space-y-3">
        <FilterGroup icon={GraduationCap} label="排名档位">
          <SegmentedOptions
            options={RANKING_OPTIONS}
            value={filters.rankingTier}
            onChange={(value) => update("rankingTier", value)}
          />
        </FilterGroup>

        <FilterGroup icon={DollarSign} label="年度预算">
          <SegmentedOptions
            options={COST_OPTIONS}
            value={filters.maxCostRmb}
            onChange={(value) => update("maxCostRmb", value)}
          />
        </FilterGroup>

        <FilterGroup icon={Shield} label="安全底线">
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={filters.minSafetyScore ?? 0}
              onChange={(event) => {
                const value = Number(event.target.value);
                update("minSafetyScore", value === 0 ? null : value);
              }}
              className="h-2 flex-1 accent-cobalt"
              aria-label="最低安全评分"
            />
            <span className="w-12 text-right text-xs font-medium tabular-nums text-ink/64">
              {filters.minSafetyScore ? `${filters.minSafetyScore}+` : "不限"}
            </span>
          </div>
        </FilterGroup>

        <FilterGroup icon={SlidersHorizontal} label="录取难度">
          <SegmentedOptions
            options={ADMISSION_OPTIONS}
            value={filters.admissionSelectivity}
            onChange={(value) => update("admissionSelectivity", value)}
          />
        </FilterGroup>

        <FilterGroup icon={Users} label="华人社区">
          <div className="flex flex-wrap gap-1.5">
            {COMMUNITY_OPTIONS.map((option) => {
              const selected = filters.chineseCommunityLevels.includes(option.value);
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => toggleCommunity(option.value)}
                  className={chipClass(selected)}
                  aria-pressed={selected}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        </FilterGroup>

        <FilterGroup icon={Plane} label="直飞与地区">
          <div className="space-y-2">
            <label className="inline-flex cursor-pointer items-center gap-2 text-xs font-medium text-ink/64">
              <input
                type="checkbox"
                checked={filters.directFlightOnly}
                onChange={(event) => update("directFlightOnly", event.target.checked)}
                className="h-3.5 w-3.5 rounded border-line text-cobalt accent-cobalt"
              />
              只看国内直飞城市
            </label>
            {states.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {states.map((state) => {
                  const selected = filters.stateCodes.includes(state.code);
                  return (
                    <button
                      key={state.code}
                      type="button"
                      onClick={() => toggleState(state.code)}
                      className={chipClass(selected)}
                      aria-pressed={selected}
                    >
                      {state.code}
                      <span className="text-current/50">{state.count}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </FilterGroup>

        <FilterGroup icon={ArrowDownAZ} label="排序">
          <SegmentedOptions
            options={SORT_OPTIONS}
            value={filters.sortBy}
            onChange={(value) => update("sortBy", value)}
          />
        </FilterGroup>
      </div>
    </section>
  );
}

function FilterGroup({
  icon: Icon,
  label,
  children,
}: {
  icon: typeof Filter;
  label: string;
  children: ReactNode;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-medium text-ink/48">
        <Icon size={12} aria-hidden="true" />
        <span>{label}</span>
      </div>
      {children}
    </div>
  );
}

function SegmentedOptions<T extends string | number | null>({
  options,
  value,
  onChange,
}: {
  options: Array<{ label: string; value: T }>;
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={`${option.value ?? "all"}`}
            type="button"
            onClick={() => onChange(option.value)}
            className={chipClass(selected)}
            aria-pressed={selected}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

function chipClass(selected: boolean): string {
  return [
    "inline-flex h-7 items-center gap-1 rounded-md border px-2 text-[11px] font-medium transition-colors",
    selected
      ? "border-cobalt/35 bg-cobalt/10 text-cobalt"
      : "border-line/70 bg-white/60 text-ink/56 hover:border-ink/25 hover:bg-white hover:text-ink",
  ].join(" ");
}

function getTopStates(universities: UniversityPOI[]): Array<{ code: string; count: number }> {
  const counts = new Map<string, number>();
  universities.forEach((university) => {
    const state = (university as UniversityPOI & { state?: string }).state;
    if (!state) return;
    counts.set(state, (counts.get(state) ?? 0) + 1);
  });

  return Array.from(counts.entries())
    .map(([code, count]) => ({ code, count }))
    .sort((a, b) => b.count - a.count || a.code.localeCompare(b.code))
    .slice(0, 12);
}
