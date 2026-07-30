"use client";

import { useState, useMemo, useCallback } from "react";
import { useDataSource } from "@/services/data-source-provider";
import { useRegionMetrics, useUniversitySummaries } from "@/hooks/use-data-source";
import { Calculator, DollarSign, Plane, ShieldCheck, FileText, Plus, X, Copy, Check } from "lucide-react";
import Link from "next/link";
import { useCompareStore } from "@/state/compare-store";
import {
  computeAnnualTotalRmb,
  computeCostMultiplier,
  formatRmbShort,
  TUITION_EMPTY_LABEL,
  type FormattedCost,
} from "@/lib/cost-format";
import { tuitionRmbFromSummary } from "@/lib/legacy-mappers";
import { SchoolPicker } from "@/components/calculator/SchoolPicker";

const EXCHANGE_RATE = 7.2;
const STANDARD_COSTS = [
  { label: "医疗保险", amount: 36000, icon: ShieldCheck },
  { label: "往返机票 (2次/年)", amount: 24000, icon: Plane },
  { label: "签证及服务费", amount: 12000, icon: FileText },
];
const LIVING_TIERS = [
  { id: "low", label: "低", labelEn: "Low", housing: 72000, food: 48000, transport: 12000, desc: "合租·自己做饭" },
  { id: "medium", label: "中", labelEn: "Medium", housing: 120000, food: 72000, transport: 24000, desc: "一居室·混合饮食" },
  { id: "high", label: "高", labelEn: "High", housing: 180000, food: 108000, transport: 36000, desc: "独立公寓·外食多" },
];
const TIER_LIVING_LABELS: Record<string, { label: string; items: { label: string; key: string }[] }> = {
  low:    { label: "节俭型", items: [{ label: "住宿 (合租)", key: "housing" }, { label: "餐饮 (自己做)", key: "food" }, { label: "交通 (公交)", key: "transport" }] },
  medium: { label: "标准型", items: [{ label: "住宿 (一居室)", key: "housing" }, { label: "餐饮 (混合)", key: "food" }, { label: "交通 (公交+打车)", key: "transport" }] },
  high:   { label: "舒适型", items: [{ label: "住宿 (独立公寓)", key: "housing" }, { label: "餐饮 (外食多)", key: "food" }, { label: "交通 (公交+车)", key: "transport" }] },
};

export default function CalculatorPage() {
  const compare = useCompareStore();
  const selectedIds = compare.ids;
  const [tierId, setTierId] = useState("medium");
  const [copied, setCopied] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const dataSource = useDataSource();
  const summariesState = useUniversitySummaries(dataSource);
  const incomeMetricsState = useRegionMetrics(dataSource, {
    metricId: "income",
    granularity: "state",
  });
  const allUnis = useMemo<UniversityView[]>(
    () => (summariesState.state.status === "ready" ? (summariesState.state.data as unknown as UniversityView[]) : []),
    [summariesState.state],
  );
  const incomeRecords = useMemo(
    () => (incomeMetricsState.state.status === "ready" ? (incomeMetricsState.state.data as unknown as Array<{ metricId: string; value: number; fipsCode: string }>) : []),
    [incomeMetricsState.state],
  );
  const stateCostMult = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of incomeRecords) {
      if (r.metricId === "income" && typeof r.value === "number") {
        const fips = String(r.fipsCode ?? "").padStart(2, "0").slice(-2);
        map.set(fips, computeCostMultiplier(r.value));
      }
    }
    return map;
  }, [incomeRecords]);
  const getCostMult = useCallback(
    (fips?: string) => stateCostMult.get(String(fips ?? "").padStart(2, "0").slice(-2)) ?? 0.7,
    [stateCostMult],
  );
  const COST_LEVEL = (m: number) => (m >= 0.85 ? "H" : m >= 0.70 ? "M" : "L");

  const tier = LIVING_TIERS.find((t) => t.id === tierId)!;
  const standardTotal = STANDARD_COSTS.reduce((s, c) => s + c.amount, 0);

  const selected = useMemo(
    () => allUnis.filter((u) => selectedIds.includes(u.id)),
    [allUnis, selectedIds],
  );
  const available = useMemo(
    () => allUnis.filter((u) => !selectedIds.includes(u.id)),
    [allUnis, selectedIds],
  );
  const addUni = useCallback((id: string) => { compare.add(id); }, [compare]);
  const removeUni = useCallback((id: string) => { compare.remove(id); }, [compare]);

  const totalsById = useMemo(() => {
    const out = new Map<string, number | null>();
    for (const u of selected) {
      const tuition = tuitionRmbFromSummary(u);
      const cm = getCostMult(u.stateFips);
      const tierLiving = tier.housing + tier.food + tier.transport;
      out.set(u.id, computeAnnualTotalRmb(tuition, tierLiving, cm, standardTotal));
    }
    return out;
  }, [selected, getCostMult, tier, standardTotal]);

  const comparableTotals = useMemo(
    () => Array.from(totalsById.values()).filter((v): v is number => typeof v === "number"),
    [totalsById],
  );
  const maxTotal = comparableTotals.length > 0 ? Math.max(...comparableTotals) : 1;
  const BAR_COLORS = ["bg-cobalt", "bg-jade", "bg-persimmon"];

  const handleCopy = useCallback(() => {
    const lines = ["PathOS 留学预算计算器", "=".repeat(30), ""];
    selected.forEach((u) => {
      const tuition = tuitionRmbFromSummary(u);
      const tuitionLabel: FormattedCost = formatRmbShort(tuition);
      const t = totalsById.get(u.id) ?? null;
      const totalLabel: FormattedCost =
        t === null
          ? { kind: "empty", label: TUITION_EMPTY_LABEL }
          : { kind: "value", label: "¥" + t.toLocaleString() };
      lines.push("■ " + u.chineseName + " (" + u.name + ")");
      lines.push("  学费: " + tuitionLabel.label);
      lines.push("  生活费: ¥" + (tier.housing + tier.food + tier.transport).toLocaleString());
      lines.push("  其他: ¥" + standardTotal.toLocaleString());
      lines.push("  总计: " + totalLabel.label);
      lines.push("");
    });
    navigator.clipboard.writeText(lines.join("\n")).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [selected, tier, standardTotal, totalsById]);

  return (
    <div className="min-h-screen bg-surface-base">
      <header className="border-b border-border-soft bg-surface-1/70 backdrop-blur">
        <div className="mx-auto flex max-w-page items-center gap-3 px-4 py-3 sm:px-6">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-control bg-ink text-paper"><Calculator size={16} aria-hidden="true" /></div>
          <div className="min-w-0 flex-1">
            <p className="text-label uppercase tracking-[0.12em] text-cobalt">留学预算</p>
            <h1 className="text-page text-text-primary">预算计算器</h1>
          </div>
          <Link href="/map" className="ml-auto text-caption text-cobalt hover:underline">← 返回地图</Link>
        </div>
      </header>

      <main className="mx-auto max-w-page px-4 py-5 sm:px-6">
        {/* Controls */}
        <div className="flex flex-wrap items-center gap-4 mb-5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-ink/60 whitespace-nowrap">生活费档次</span>
            <div className="flex rounded-lg border border-line/60 overflow-hidden">
              {LIVING_TIERS.map((t) => (
                <button key={t.id} onClick={() => setTierId(t.id)}
                  className={"px-3 py-1.5 text-xs font-medium transition-colors " + (tierId === t.id ? "bg-ink text-panel" : "bg-white text-ink/50 hover:bg-ink/5")}>{t.label}</button>
              ))}
            </div>
            <span className="text-[10px] text-ink/40">{tier.desc}</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-ink/40">
            <DollarSign size={12} /><span>汇率 {EXCHANGE_RATE}</span>
          </div>
        </div>

        {/* University Selector */}
        <div className="flex flex-wrap items-center gap-2 mb-5">
          {selected.map((u, i) => {
            const total = totalsById.get(u.id) ?? null;
            const bar = total !== null ? BAR_COLORS[i % 3] : "bg-line/60";
            return (
              <span key={u.id} className={"inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium text-panel " + bar}>
                {u.chineseName}
                {total === null && (
                  <span className="ml-1 rounded-full bg-panel/30 px-1.5 py-0.5 text-[9px] font-normal">
                    数据补充中
                  </span>
                )}
                <button onClick={() => removeUni(u.id)} className="opacity-60 hover:opacity-100"><X size={12} /></button>
              </span>
            );
          })}
          {selectedIds.length < 3 && (
            <button
              type="button"
              onClick={() => setPickerOpen(true)}
              className="inline-flex h-control items-center gap-1.5 rounded-control border border-dashed border-border-soft bg-surface-1 px-3 text-caption font-medium text-text-secondary transition hover:border-cobalt/40 hover:bg-cobalt/8 hover:text-cobalt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
            >
              <Plus size={12} aria-hidden="true" />
              添加大学（还可选择 {3 - selectedIds.length} 所）
            </button>
          )}
        </div>

        {/* Empty */}
        {selectedIds.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-line/40 bg-white/40 py-16 text-center">
            <Calculator size={48} className="text-ink/10 mb-4" />
            <p className="text-sm text-ink/55">请添加大学开始预算计算</p>
            <button
              type="button"
              onClick={() => setPickerOpen(true)}
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-cobalt/40 bg-cobalt px-4 py-2 text-xs font-semibold text-panel transition hover:bg-cobalt/90 focus-visible:ring-2 focus-visible:ring-cobalt/50"
            >
              <Plus size={14} aria-hidden="true" />
              选择第一所大学
            </button>
          </div>
        )}

        {/* Cards */}
        {selectedIds.length > 0 && (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {selected.map((u, i) => {
                const tuition = tuitionRmbFromSummary(u);
                const tuitionLabel = formatRmbShort(tuition);
                const total = totalsById.get(u.id) ?? null;
                const hasCost = total !== null;
                const costMult = getCostMult(u.stateFips);
                const adjH = Math.round(tier.housing * costMult);
                const adjF = Math.round(tier.food * costMult);
                const adjT = Math.round(tier.transport * costMult);
                const living = adjH + adjF + adjT;
                return (
                  <div key={u.id} className="rounded-xl border border-line/50 bg-white/90 shadow-sm overflow-hidden">
                    <div className={"px-4 py-2.5 text-panel text-sm font-medium flex items-center justify-between " + BAR_COLORS[i % 3]}>
                      <span>{u.chineseName}</span>
                      <button onClick={() => removeUni(u.id)} className="opacity-60 hover:opacity-100"><X size={14} /></button>
                    </div>
                    <div className="text-[10px] px-4 pb-2 -mt-1 opacity-70 text-panel/80 font-normal">{u.name} · {u.city ?? "—"}, {u.state ?? "—"}</div>
                    <div className="p-4 space-y-2">
                      <div className="flex justify-between text-xs">
                        <span className="text-ink/60">学费</span>
                        <span className={"font-medium tabular-nums " + (tuitionLabel.kind === "empty" ? "text-ink/40" : "text-ink")}>
                          {tuitionLabel.label}
                        </span>
                      </div>
                      <div className="h-px bg-line/30" />
                      <div className="text-[10px] font-medium text-ink/40 uppercase tracking-wide">生活费 · {TIER_LIVING_LABELS[tierId].label}</div>
                      {TIER_LIVING_LABELS[tierId].items.map((item) => (
                        <div key={item.key} className="flex justify-between text-xs">
                          <span className="text-ink/60">{item.label}</span>
                          <span className="tabular-nums">¥{Math.round((tier as unknown as Record<string, number>)[item.key] * costMult).toLocaleString()}</span>
                        </div>
                      ))}
                      <div className="flex justify-between text-xs bg-ink/3 -mx-4 px-4 py-1">
                        <span className="font-medium text-ink/60">小计</span>
                        <span className="font-medium tabular-nums">¥{living.toLocaleString()}</span>
                        <span className="text-[9px] text-ink/40 ml-2">cost: {COST_LEVEL(costMult)}</span>
                      </div>
                      <div className="h-px bg-line/30" />
                      <div className="text-[10px] font-medium text-ink/40 uppercase tracking-wide">其他固定费用</div>
                      {STANDARD_COSTS.map((c) => (
                        <div key={c.label} className="flex justify-between text-xs">
                          <span className="flex items-center gap-1 text-ink/60"><c.icon size={10} />{c.label}</span>
                          <span className="tabular-nums">¥{c.amount.toLocaleString()}</span>
                        </div>
                      ))}
                      <div className="h-px bg-line/30" />
                      <div className="flex items-center justify-between pt-1">
                        <span className="text-sm font-bold text-ink">年度总费用</span>
                        <div className="text-right">
                          {hasCost ? (
                            <>
                              <div className="text-base font-bold tabular-nums">¥{(total as number).toLocaleString()}</div>
                              <div className="text-[10px] text-ink/40 tabular-nums">${Math.round((total as number) / EXCHANGE_RATE).toLocaleString()} USD</div>
                            </>
                          ) : (
                            <>
                              <div className="text-sm font-medium text-ink/40">{TUITION_EMPTY_LABEL}</div>
                              <div className="text-[10px] text-ink/30">该学校未参与费用对比</div>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Calculation breakdown */}
                      <details className="group mt-2">
                        <summary className="cursor-pointer text-[10px] text-ink/30 hover:text-ink/60 transition-colors select-none">
                          查看计算过程
                        </summary>
                        <div className="mt-2 pt-2 border-t border-dashed border-line/30 space-y-1 text-[10px] text-ink/40">
                          <div className="flex justify-between">
                            <span>学费（固定）</span>
                            <span>{tuitionLabel.label}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>生活费基数 × {costMult.toFixed(2)}</span>
                            <span>¥{(adjH + adjF + adjT).toLocaleString()}</span>
                          </div>
                          <div className="text-[9px] pl-2 text-ink/20">住宿 ¥{adjH.toLocaleString()} + 餐饮 ¥{adjF.toLocaleString()} + 交通 ¥{adjT.toLocaleString()}</div>
                          <div className="text-[9px] pl-2 text-ink/20">系数来源: 州收入水平 → {COST_LEVEL(costMult)} = {costMult.toFixed(2)}</div>
                          <div className="flex justify-between"><span>医疗保险（固定）</span><span>¥{STANDARD_COSTS[0].amount.toLocaleString()}</span></div>
                          <div className="flex justify-between"><span>往返机票（固定）</span><span>¥{STANDARD_COSTS[1].amount.toLocaleString()}</span></div>
                          <div className="flex justify-between"><span>签证费用（固定）</span><span>¥{STANDARD_COSTS[2].amount.toLocaleString()}</span></div>
                          <div className="border-t border-dotted border-line/20 pt-1 flex justify-between font-medium text-ink/60">
                            <span>总计</span>
                            <span>{hasCost ? `¥${(total as number).toLocaleString()}` : TUITION_EMPTY_LABEL}</span>
                          </div>
                        </div>
                      </details>
                    </div>
                  </div>
                );
              })}
              {selectedIds.length < 3 && (
                <button
                  type="button"
                  onClick={() => setPickerOpen(true)}
                  className="flex w-full flex-col items-center justify-center rounded-card border-2 border-dashed border-border-soft bg-surface-1 min-h-[350px] text-text-muted transition hover:border-cobalt/45 hover:bg-cobalt/5 hover:text-cobalt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                >
                  <Plus size={22} className="mx-auto mb-2 text-text-muted" aria-hidden="true" />
                  <p className="text-caption font-medium">添加大学</p>
                  <p className="mt-1 text-[11px] text-text-muted">还可选择 {3 - selectedIds.length} 所</p>
                </button>
              )}
            </div>

            {/* Comparison bars */}
            {selected.length >= 2 && (
              <div className="mt-6 rounded-xl border border-line/50 bg-white/90 shadow-sm p-5">
                <h3 className="text-sm font-semibold text-ink mb-4">总费用对比</h3>
                <div className="space-y-3">
                  {selected.map((u, i) => {
                    const total = totalsById.get(u.id) ?? null;
                    if (total === null) {
                      return (
                        <div key={u.id} className="flex items-start justify-between gap-3 rounded-control border border-persimmon/30 bg-persimmon/8 px-3 py-2 text-caption text-persimmon">
                          <span className="font-medium">{u.chineseName}</span>
                          <span className="text-right">该校费用数据未纳入最高费用比较</span>
                        </div>
                      );
                    }
                    const pct = (total / maxTotal) * 100;
                    return (
                      <div key={u.id}>
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="font-medium text-ink/70">{u.chineseName}</span>
                          <span className="tabular-nums font-medium">¥{total.toLocaleString()}</span>
                        </div>
                        <div className="h-3 bg-ink/5 rounded-full overflow-hidden">
                          <div className={"h-full rounded-full transition-all " + BAR_COLORS[i % 3]} style={{ width: pct + "%" }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="mt-6 flex gap-3">
              <button onClick={handleCopy} className="inline-flex items-center gap-2 rounded-lg border border-line/60 bg-white px-4 py-2 text-xs font-medium text-ink/60 hover:text-ink hover:border-ink/20 transition-colors">
                {copied ? <Check size={14} className="text-jade" /> : <Copy size={14} />}
                {copied ? "已复制" : "复制结果"}
              </button>
            </div>
          </>
        )}
      </main>

      {/* School picker dialog — opens from the empty-state CTA, the
          top-of-page selector, and the dashed-slot CTA on each card
          column. Mobile: full-height sheet; desktop: centered modal. */}
      <SchoolPicker
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        candidates={allUnis as unknown as readonly import("@/domain/dataset").UniversitySummary[]}
        selectedIds={selectedIds}
        max={3}
        onPick={(id) => addUni(id)}
        storageKey="pathos:calculator:picker:query"
      />
    </div>
  );
}

/** Minimum shape the Calculator reads from each row of the summary list. */
type UniversityView = {
  id: string;
  name: string;
  chineseName: string;
  state?: string;
  stateFips?: string;
  city?: string;
  costSummary?: { minimumUsd?: number | null; maximumUsd?: number | null } | null;
};