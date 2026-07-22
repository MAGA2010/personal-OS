
"use client";

import { useState, useMemo, useCallback } from "react";
import universityData from "@/data/universities.json";
import regionMetrics from "@/data/region-metrics.json";
import { Calculator, DollarSign, Plane, ShieldCheck, FileText, Plus, X, Copy, Check } from "lucide-react";
import Link from "next/link";

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
const fmt = (n: number) => "¥" + n.toLocaleString();
const fmtUSD = (n: number) => "$" + (n / EXCHANGE_RATE).toLocaleString(undefined, { maximumFractionDigits: 0 });
// state cost multiplier from income data
const STATE_COST_MULT = new Map<string, number>();
for (const r of ((regionMetrics as any).records ?? [])) {
  if (r.metricId === "income") {
    STATE_COST_MULT.set(r.fipsCode, 0.4 + r.value * 0.6);
  }
}
const getCostMult = (fips?: string) => STATE_COST_MULT.get(fips ?? "") ?? 0.7;
const COST_LEVEL = (m: number) => m >= 0.85 ? "H" : m >= 0.70 ? "M" : "L";

export default function CalculatorPage() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [tierId, setTierId] = useState("medium");
  const [copied, setCopied] = useState(false);
  const allUnis = (universityData as any).universities as any[];
  const selected = useMemo(() => allUnis.filter((u: any) => selectedIds.includes(u.id)), [allUnis, selectedIds]);
  const available = useMemo(() => allUnis.filter((u: any) => !selectedIds.includes(u.id)), [allUnis, selectedIds]);
  const addUni = useCallback((id: string) => { if (selectedIds.length < 3) setSelectedIds(p => [...p, id]); }, [selectedIds.length]);
  const removeUni = useCallback((id: string) => setSelectedIds(p => p.filter(i => i !== id)), []);
  const tier = LIVING_TIERS.find(t => t.id === tierId)!;
  const totalCost = (u: any) => { const cm = getCostMult(u.stateFips); return u.annualCostRmb + Math.round((tier.housing + tier.food + tier.transport) * cm) + STANDARD_COSTS.reduce((s, c: any) => s + c.amount, 0); };
  const maxTotal = selected.length > 0 ? Math.max(...selected.map(totalCost)) : 1;
  const BAR_COLORS = ["bg-cobalt", "bg-jade", "bg-persimmon"];

  const handleCopy = useCallback(() => {
    const lines = ["PathOS 留学预算计算器", "=".repeat(30), ""];
    selected.forEach((u: any) => {
      const t = totalCost(u);
      lines.push("■ " + u.chineseName + " (" + u.name + ")");
      lines.push("  学费: " + fmt(u.annualCostRmb));
      lines.push("  生活费: " + fmt(tier.housing + tier.food + tier.transport));
      lines.push("  其他: " + fmt(STANDARD_COSTS.reduce((s: number, c: any) => s + c.amount, 0)));
      lines.push("  总计: " + fmt(t) + " / " + fmtUSD(t));
      lines.push("");
    });
    navigator.clipboard.writeText(lines.join("\n")).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); });
  }, [selected, tierId]);

  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-line bg-panel px-5 py-3">
        <div className="mx-auto flex max-w-6xl items-center gap-3">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-ink text-panel"><Calculator size={18} /></div>
          <div><h1 className="text-base font-semibold text-ink">留学预算计算器</h1><p className="text-xs text-ink/52">Study Abroad Budget Calculator</p></div>
          <Link href="/map" className="ml-auto text-xs text-cobalt hover:underline">← 返回地图</Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        {/* Controls */}
        <div className="flex flex-wrap items-center gap-4 mb-5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-ink/60 whitespace-nowrap">生活费档次</span>
            <div className="flex rounded-lg border border-line/60 overflow-hidden">
              {LIVING_TIERS.map(t => (
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
          {selected.map((u: any, i: number) => (
            <span key={u.id} className={"inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium text-panel " + BAR_COLORS[i % 3]}>
              {u.chineseName}
              <button onClick={() => removeUni(u.id)} className="opacity-60 hover:opacity-100"><X size={12} /></button>
            </span>
          ))}
          {selectedIds.length < 3 && (
            <select value="" onChange={e => e.target.value && addUni(e.target.value)}
              className="rounded-lg border border-line/60 bg-white px-3 py-1.5 text-xs text-ink/60 outline-none focus:border-cobalt">
              <option value="">+ 添加大学（最多3所）</option>
              {available.map((u: any) => <option key={u.id} value={u.id}>{u.chineseName} ({u.name})</option>)}
            </select>
          )}
        </div>

        {/* Empty */}
        {selectedIds.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Calculator size={48} className="text-ink/10 mb-4" />
            <p className="text-sm text-ink/40">请从上方下拉菜单中选择大学开始计算</p>
          </div>
        )}

        {/* Cards */}
        {selectedIds.length > 0 && (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {selected.map((u: any, i: number) => {
                const costMult = getCostMult(u.stateFips);
                const tuition = u.annualCostRmb;
                const adjH = Math.round(tier.housing * costMult);
                const adjF = Math.round(tier.food * costMult);
                const adjT = Math.round(tier.transport * costMult);
                const living = adjH + adjF + adjT;
                const standard = STANDARD_COSTS.reduce((s: number, c: any) => s + c.amount, 0);
                const total = tuition + living + standard;
                return (
                  <div key={u.id} className="rounded-xl border border-line/50 bg-white/90 shadow-sm overflow-hidden">
                    <div className={"px-4 py-2.5 text-panel text-sm font-medium flex items-center justify-between " + BAR_COLORS[i % 3]}>
                      <span>{u.chineseName}</span>
                      <button onClick={() => removeUni(u.id)} className="opacity-60 hover:opacity-100"><X size={14} /></button>
                    </div>
                    <div className="text-[10px] px-4 pb-2 -mt-1 opacity-70 text-panel/80 font-normal">{u.name} · {u.city}, {u.state}</div>
                    <div className="p-4 space-y-2">
                      <div className="flex justify-between text-xs"><span className="text-ink/60">学费</span><span className="font-medium tabular-nums">{fmt(tuition)}</span></div>
                      <div className="h-px bg-line/30" />
                      <div className="text-[10px] font-medium text-ink/40 uppercase tracking-wide">生活费 · {TIER_LIVING_LABELS[tierId].label}</div>
                      {TIER_LIVING_LABELS[tierId].items.map((item: any) => (
                        <div key={item.key} className="flex justify-between text-xs"><span className="text-ink/60">{item.label}</span><span className="tabular-nums">{fmt(Math.round((tier as any)[item.key] * costMult))}</span></div>
                      ))}
                      <div className="flex justify-between text-xs bg-ink/3 -mx-4 px-4 py-1"><span className="font-medium text-ink/60">小计</span><span className="font-medium tabular-nums">{fmt(living)}</span><span className="text-[9px] text-ink/40 ml-2">cost: {COST_LEVEL(costMult)}</span></div>
                      <div className="h-px bg-line/30" />
                      <div className="text-[10px] font-medium text-ink/40 uppercase tracking-wide">其他固定费用</div>
                      {STANDARD_COSTS.map((c: any) => (
                        <div key={c.label} className="flex justify-between text-xs"><span className="flex items-center gap-1 text-ink/60"><c.icon size={10} />{c.label}</span><span className="tabular-nums">{fmt(c.amount)}</span></div>
                      ))}
                      <div className="h-px bg-line/30" />
                                          </div>
                    <div className="h-px bg-line/30" />
                    <div className="flex items-center justify-between pt-1">
                        <span className="text-sm font-bold text-ink">年度总费用</span>
                        <div className="text-right"><div className="text-base font-bold tabular-nums">{fmt(total)}</div><div className="text-[10px] text-ink/40 tabular-nums">{fmtUSD(total)} USD</div></div>
                    </div>

                    {/* Calculation breakdown */}
                    <details className="group mt-2">
                      <summary className="cursor-pointer text-[10px] text-ink/30 hover:text-ink/60 transition-colors select-none">
                        ╨ 查看计算过程
                      </summary>
                      <div className="mt-2 pt-2 border-t border-dashed border-line/30 space-y-1 text-[10px] text-ink/40">
                        <div className="flex justify-between"><span>学费（固定）</span><span>{fmt(tuition)}</span></div>
                        <div className="flex justify-between">
                          <span>生活费基数 × {costMult.toFixed(2)}</span>
                          <span>{fmt(adjH + adjF + adjT)}</span>
                        </div>
                        <div className="text-[9px] pl-2 text-ink/20">住宿 {fmt(adjH)} + 餐饮 {fmt(adjF)} + 交通 {fmt(adjT)}</div>
                        <div className="text-[9px] pl-2 text-ink/20">系数来源: 州收入水平 → {COST_LEVEL(costMult)} = {costMult.toFixed(2)}</div>
                        <div className="flex justify-between"><span>医疗保险（固定）</span><span>{fmt(36000)}</span></div>
                        <div className="flex justify-between"><span>往返机票（固定）</span><span>{fmt(24000)}</span></div>
                        <div className="flex justify-between"><span>签证费用（固定）</span><span>{fmt(12000)}</span></div>
                        <div className="border-t border-dotted border-line/20 pt-1 flex justify-between font-medium text-ink/60">
                          <span>总计</span><span>{fmt(total)}</span>
                        </div>
                      </div>
                      </details>
                      </div>
                );
              })}
              {selectedIds.length < 3 && (
                <div className="flex items-center justify-center rounded-xl border-2 border-dashed border-line/40 bg-white/40 min-h-[350px]">
                  <div className="text-center"><Plus size={24} className="mx-auto text-ink/20 mb-2" /><p className="text-xs text-ink/30">添加更多大学对比</p></div>
                </div>
              )}
            </div>

            {/* Comparison bars */}
            {selected.length >= 2 && (
              <div className="mt-6 rounded-xl border border-line/50 bg-white/90 shadow-sm p-5">
                <h3 className="text-sm font-semibold text-ink mb-4">总费用对比</h3>
                <div className="space-y-3">
                  {selected.map((u: any, i: number) => {
                    const total = totalCost(u);
                    const pct = (total / maxTotal) * 100;
                    return (
                      <div key={u.id}>
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="font-medium text-ink/70">{u.chineseName}</span>
                          <span className="tabular-nums font-medium">{fmt(total)}</span>
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
    </div>
  );
}
