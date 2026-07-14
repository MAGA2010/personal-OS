"use client";

import { useState, useMemo, type ReactNode } from "react";
import type { UniversityPOI, ChineseCommunityLevel } from "@/lib/types";
import rankingData from "@/data/university-rankings.json";
import {
  Trophy, DollarSign, GraduationCap, Shield, MapPin, Star,
  X, Plus, ChevronRight,
} from "lucide-react";

interface ComparePanelProps {
  universities: UniversityPOI[];
  selectedIds: string[];
  onRemove: (id: string) => void;
  onClear: () => void;
  onClose: () => void;
}

type IconComponent = typeof Trophy;

interface CategoryDef {
  label: string;
  icon: IconComponent;
  keys: string[];
}

const CATEGORIES: CategoryDef[] = [
  { label: "排名", icon: Trophy,     keys: ["QS", "ARWU", "USNews", "THE", "rankingBand"] },
  { label: "费用", icon: DollarSign, keys: ["annualCostRmb"] },
  { label: "入学要求", icon: GraduationCap, keys: ["admissionRate"] },
  { label: "安全", icon: Shield,     keys: ["safetyScore"] },
  { label: "认可度", icon: Star,     keys: ["recognitionScore"] },
  { label: "生活信息", icon: MapPin, keys: ["city", "postStudyVisa"] },
];

const ROW_LABELS: Record<string, string> = {
  QS: "QS 排名",
  ARWU: "ARWU 排名",
  USNews: "US News 排名",
  THE: "THE 排名",
  rankingBand: "排名等级",
  annualCostRmb: "学费 (RMB/年)",
  admissionRate: "录取率",
  safetyScore: "安全评分",
  recognitionScore: "认可度",
  city: "所在城市",
  postStudyVisa: "毕业签证",
};

const NUMERIC_KEYS = [
  "QS", "ARWU", "USNews", "THE",
  "annualCostRmb", "admissionRate", "safetyScore", "recognitionScore",
];

const UNI_COLORS = [
  { bar: "bg-cobalt", text: "text-cobalt", light: "bg-cobalt/10" },
  { bar: "bg-jade", text: "text-jade", light: "bg-jade/10" },
  { bar: "bg-persimmon", text: "text-persimmon", light: "bg-persimmon/10" },
  { bar: "bg-ink", text: "text-ink", light: "bg-ink/8" },
];

function formatValue(key: string, val: any): string {
  if (val === null || val === undefined) return "—";
  switch (key) {
    case "QS": case "ARWU": case "USNews": case "THE": return String(val);
    case "rankingBand": return val;
    case "annualCostRmb": return "¥" + Number(val).toLocaleString();
    case "admissionRate": return val + "%";
    case "safetyScore": return val + "/100";
    case "recognitionScore": return val + "/100";
    case "city": return val;
    case "postStudyVisa": return val;
    default: return String(val);
  }
}

export default function ComparePanel({
  universities,
  selectedIds,
  onRemove,
  onClear,
  onClose,
}: ComparePanelProps) {
  const [openCategories, setOpenCategories] = useState<string[]>(["排名", "费用", "认可度"]);

  const selected = useMemo(
    () => universities.filter(u => selectedIds.includes(u.id)),
    [universities, selectedIds]
  );

  const rankingMap = useMemo(() => {
    const m: Record<string, any> = {};
    (rankingData as any[]).forEach(r => { m[r.id] = r; });
    return m;
  }, []);

  const toggleCategory = (label: string) => {
    setOpenCategories(prev =>
      prev.includes(label) ? prev.filter(l => l !== label) : [...prev, label]
    );
  };

  const maxValues = useMemo(() => {
    const m: Record<string, number> = {};
    CATEGORIES.forEach(cat => cat.keys.forEach(key => {
      if (NUMERIC_KEYS.includes(key)) {
        const vals = selected.map(u => {
          if (["QS","ARWU","USNews","THE"].includes(key)) {
            const r = rankingMap[u.id];
            return r ? r[key] : 9999;
          }
          return (u as any)[key] ?? 0;
        }).filter(v => v !== null && v !== undefined);
        m[key] = vals.length > 0 ? Math.max(...vals) : 1;
      }
    }));
    return m;
  }, [selected, rankingMap]);

  function getVal(u: any, key: string): any {
    if (["QS","ARWU","USNews","THE"].includes(key)) {
      const r = rankingMap[u.id];
      return r ? r[key] : null;
    }
    return (u as any)[key];
  }

  return (
    <div className="shrink-0 border-t border-line bg-panel/95 backdrop-blur max-h-[55vh] flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-ink/60">大学对比</span>
          {selected.length > 0 && (
            <span className="text-[10px] text-ink/32">{selected.length} 所选</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {selected.length > 0 && (
            <button onClick={onClear} className="text-[10px] text-ink/36 hover:text-ink transition-colors">清空</button>
          )}
          <button onClick={onClose} className="rounded p-0.5 text-ink/36 hover:text-ink hover:bg-ink/5 transition-colors">
            <X size={14} />
          </button>
        </div>
      </div>

      {selected.length === 0 ? (
        <div className="flex items-center justify-center gap-2 px-4 pb-3 text-xs text-ink/32 shrink-0">
          <Plus size={14} />
          <span>点击大学添加到对比（最多 4 所）</span>
        </div>
      ) : (
        <div className="overflow-y-auto px-4 pb-3 space-y-3 flex-1">
          {/* University name badges */}
          <div className="flex flex-wrap gap-2">
            {selected.map((u, i) => {
              const c = UNI_COLORS[i % UNI_COLORS.length];
              return (
                <span key={u.id} className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${c.light} ${c.text}`}>
                  {u.chineseName}
                  <button onClick={() => onRemove(u.id)} className="ml-0.5 opacity-50 hover:opacity-100">
                    <X size={12} />
                  </button>
                </span>
              );
            })}
          </div>

          {/* ── Quick overview: cost, safety, admission rate ── */}
          {selected.length >= 2 && (
            <div className="rounded border border-line/30 overflow-hidden">
              <div className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-ink/60 bg-ink/3">
                <Star size={12} />
                <span>快速概览</span>
              </div>
              <div className="px-3 py-2 space-y-2">
                {OVERVIEW_METRICS.map(m => {
                  const maxV = maxValues[m.key] || 1;
                  return (
                    <div key={m.key}>
                      <div className="text-[10px] text-ink/36 mb-1 flex items-center gap-1">
                        <m.icon size={10} />
                        <span>{m.label}</span>
                      </div>
                      {selected.map((u, i) => (
                        <BarRow key={u.id} u={u} i={i} metricKey={m.key} val={getVal(u, m.key)}
                          maxVal={maxV} formatter={(v: any) => formatValue(m.key, v)} />
                      ))}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ── Detailed category comparison ── */}
          {CATEGORIES.map(cat => {
            const isOpen = openCategories.includes(cat.label);
            return (
              <div key={cat.label} className="rounded border border-line/30 overflow-hidden">
                <button
                  onClick={() => toggleCategory(cat.label)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-xs font-medium text-ink/60 hover:text-ink hover:bg-ink/3 transition-colors"
                >
                  <cat.icon size={13} />
                  <span>{cat.label}</span>
                  <ChevronRight size={12} className={`ml-auto text-ink/24 transition-transform ${isOpen ? "rotate-90" : ""}`} />
                </button>

                {isOpen && cat.keys.map(key => {
                  const maxVal = maxValues[key] || 1;
                  return (
                    <div key={key} className="border-t border-line/15 px-3 py-2">
                      <div className="text-[10px] text-ink/36 mb-1.5">{ROW_LABELS[key] || key}</div>
                      {selected.map((u, i) => {
                        const val = getVal(u, key);
                        return <BarRow key={u.id} u={u} i={selected.indexOf(u)} metricKey={key}
                          val={val} maxVal={maxVal} formatter={(v: any) => formatValue(key, v)} />;
                      })}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

  // ── Quick overview: three key metrics always visible ──
  const OVERVIEW_METRICS: { key: string; label: string; icon: IconComponent; unit: string }[] = [
    { key: "annualCostRmb",   label: "年度学费", icon: DollarSign,    unit: "¥" },
    { key: "safetyScore",     label: "安全评分", icon: Shield,       unit: "/100" },
    { key: "admissionRate",   label: "录取率",   icon: GraduationCap, unit: "%" },
  ];
  // ── Render a single comparison bar row ──
  function BarRow({ u, i, metricKey, val, maxVal, formatter }: {
    u: UniversityPOI; i: number; metricKey: string; val: any; maxVal: number; formatter: (v: any) => string;
  }) {
    const c = UNI_COLORS[i % UNI_COLORS.length];
    const numVal = Number(val) || 0;
    const inv = metricKey === "admissionRate" || metricKey === "QS" || metricKey === "ARWU" || metricKey === "USNews" || metricKey === "THE";
    const pct = maxVal > 0 ? (inv ? (1 - numVal / maxVal) * 100 : (numVal / maxVal) * 100) : 0;
    return (
      <div className="flex items-center gap-2 mb-1 last:mb-0">
        <span className={`w-16 shrink-0 text-[10px] font-medium truncate ${c.text}`}>{u.chineseName}</span>
        <div className="flex-1 h-4 bg-ink/5 rounded-sm overflow-hidden relative">
          <div className={`h-full rounded-sm transition-all duration-300 ${c.bar}`}
            style={{ width: Math.max(pct, 3) + "%", minWidth: pct > 0 ? "3px" : "0" }}
          />
        </div>
        <span className={`w-20 shrink-0 text-right text-[10px] tabular-nums ${c.text}`}>{formatter(val)}</span>
      </div>
    );
  }