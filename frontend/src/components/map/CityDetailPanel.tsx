"use client";

import type { CityAggregate } from "@/lib/types";
import {
  ArrowLeft,
  Building2,
  DollarSign,
  GraduationCap,
  MapPin,
  Plane,
  Plus,
  Shield,
  Star,
  Users,
} from "lucide-react";

interface CityDetailPanelProps {
  city: CityAggregate;
  onBack: () => void;
  onUniversitySelect: (id: string) => void;
  selectedUniversityId?: string | null;
  onAddToCompare?: (id: string) => void;
}

function formatCost(rmb: number | null | undefined): string {
  // Gate-bloker repair #RG-P0-H: cost is nullable now. A missing
  // (null/undefined/<=0/non-finite) value renders the empty-state
  // label, never "¥0.0万/年".
  if (typeof rmb !== "number" || !Number.isFinite(rmb) || rmb <= 0) return "学费数据补充中";
  return `¥${(rmb / 10000).toFixed(1)}万/年`;
}

function formatAdmission(rate?: number | null): string {
  if (typeof rate !== "number" || !Number.isFinite(rate)) return "数据补充中";
  return `${rate.toFixed(rate < 10 ? 1 : 0)}%`;
}

function communityLabel(level: CityAggregate["dominantChineseCommunity"] | null | undefined): string {
  if (level === "high") return "高";
  if (level === "medium") return "中";
  if (level === "low") return "低";
  return "—";
}

function scoreLabel(score: number | null | undefined, unit = "/100"): string {
  if (typeof score !== "number" || !Number.isFinite(score)) return "数据补充中";
  return `${Math.round(score)}${unit}`;
}

/** Sidebar panel for the city stage of the state -> city -> university drill-down. */
export function CityDetailPanel({
  city,
  onBack,
  onUniversitySelect,
  selectedUniversityId,
  onAddToCompare,
}: CityDetailPanelProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-line px-4 py-3">
        <button
          type="button"
          onClick={onBack}
          className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-ink/52 transition-colors hover:text-ink"
        >
          <ArrowLeft size={13} />
          返回州级城市列表
        </button>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-ink">{city.nameZh}</h2>
            <p className="text-xs text-ink/48">
              {city.name}, {city.stateAbbr} · {city.universityCount} 所大学
            </p>
          </div>
          <span className="rounded-full border border-cobalt/25 bg-cobalt/8 px-2 py-1 text-[11px] font-medium text-cobalt">
            城市视图
          </span>
        </div>
      </div>

      <div className="border-b border-line px-4 py-3">
        <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-ink/44">城市概览</h3>
        <div className="grid grid-cols-2 gap-2">
          <MetricCard icon={GraduationCap} label="大学数量" value={`${city.universityCount} 所`} />
          <MetricCard icon={DollarSign} label="平均费用" value={formatCost(city.avgAnnualCostRmb)} />
          <MetricCard
            icon={Shield}
            label="平均安全"
            value={city.universities.some((university) => typeof university.safetyScore === "number")
              ? scoreLabel(city.avgSafetyScore)
              : "数据补充中"}
          />
          <MetricCard
            icon={Users}
            label="华人社区"
            value={city.universities.some((university) => university.chineseCommunity !== null)
              ? communityLabel(city.dominantChineseCommunity)
              : "数据补充中"}
          />
          <MetricCard
            icon={Star}
            label="平均认可度"
            value={city.universities.some((university) => typeof university.recognitionScore === "number")
              ? scoreLabel(city.avgRecognitionScore)
              : "数据补充中"}
          />
          <MetricCard icon={Plane} label="直飞覆盖" value={`${city.directFlightCount}/${city.universityCount}`} />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xs font-medium uppercase tracking-wide text-ink/44">该城市大学</h3>
          <span className="rounded bg-ink/8 px-1.5 py-0.5 text-[10px] text-ink/52">
            {city.universities.length}
          </span>
        </div>

        {city.universities.length === 0 ? (
          <p className="rounded-lg border border-dashed border-line bg-white/50 px-3 py-6 text-center text-xs text-ink/40">
            当前筛选条件下暂无大学。
          </p>
        ) : (
          <ul className="space-y-2" role="list">
            {city.universities.map((uni) => {
              const selected = uni.id === selectedUniversityId;
              const admissionRate = (uni as typeof uni & { admissionRate?: number | null }).admissionRate;
              return (
                <li key={uni.id}>
                  <button
                    type="button"
                    onClick={() => onUniversitySelect(uni.id)}
                    className={`w-full rounded-lg border px-3 py-2.5 text-left text-xs transition-colors ${
                      selected
                        ? "border-cobalt/35 bg-cobalt/8"
                        : "border-line/70 bg-white hover:border-cobalt/30 hover:bg-cobalt/[0.03]"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate font-medium text-ink">{uni.chineseName}</div>
                        <div className="truncate text-ink/52">{uni.name}</div>
                      </div>
                      <span className="shrink-0 rounded-full bg-ink/8 px-1.5 py-0.5 text-[10px] font-medium text-ink/56">
                        {uni.rankingTier}
                      </span>
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-ink/48">
                      <span className="inline-flex items-center gap-1">
                        <DollarSign size={10} />
                        {formatCost(uni.annualCostRmb)}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <Shield size={10} />
                        {scoreLabel(uni.safetyScore)}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <GraduationCap size={10} />
                        录取 {formatAdmission(admissionRate)}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <MapPin size={10} />
                        {uni.city}
                      </span>
                    </div>
                  </button>
                  {onAddToCompare && (
                    <button
                      type="button"
                      onClick={() => onAddToCompare(uni.id)}
                      className="mt-1 inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-cobalt transition-colors hover:bg-cobalt/8"
                    >
                      <Plus size={10} />
                      加入对比
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Building2;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border border-line/60 bg-white/60 px-3 py-2 text-xs">
      <div className="flex items-center gap-1 text-ink/48">
        <Icon size={11} />
        <span>{label}</span>
      </div>
      <div className="mt-0.5 font-semibold text-ink">{value}</div>
    </div>
  );
}
