"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import universityData from "@/data/universities.json";
import { Plus, Trash2, Bookmark, Download, ChevronDown, ChevronUp, Search, X } from "lucide-react";
import Link from "next/link";
import { ProductJourney } from "@/components/ProductJourney";

interface PortfolioItem { id: string; addedAt: string; }
const STORAGE_KEY = "pathos_portfolio";

function loadP(): PortfolioItem[] {
  if (typeof window === "undefined") return [];
  try { const raw = localStorage.getItem(STORAGE_KEY); return raw ? JSON.parse(raw) : []; } catch { return []; }
}
function saveP(items: PortfolioItem[]) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(items)); } catch {}
}

export default function PortfolioPage() {
  const all = (universityData as any).universities as any[];
  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [sq, setSq] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => { setItems(loadP()); }, []);

  const add = useCallback((id: string) => {
    setItems((prev) => {
      if (prev.some((i) => i.id === id)) return prev;
      const next = [...prev, { id, addedAt: new Date().toISOString().split("T")[0] }];
      saveP(next); return next;
    });
    setShowAdd(false); setSq("");
  }, []);

  const remove = useCallback((id: string) => {
    setItems((prev) => { const next = prev.filter((i) => i.id !== id); saveP(next); return next; });
  }, []);

  const handleClear = useCallback(() => {
    if (confirm("确定清空选校单？")) { setItems([]); saveP([]); }
  }, []);

  const handleExport = useCallback(() => {
    const data = items.map((item) => {
      const u = all.find((x: any) => x.id === item.id);
      return u ? { id: u.id, name: u.chineseName, nameEn: u.name, city: u.city, cost: u.annualCostRmb, ranking: u.rankingTier } : null;
    }).filter(Boolean);
    const blob = new Blob([JSON.stringify({ exportedAt: new Date().toISOString(), universities: data }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "pathos-portfolio.json"; a.click();
    URL.revokeObjectURL(url);
  }, [all, items]);

  const unis = useMemo(() => {
    return items.map((item) => {
      const u = all.find((x: any) => x.id === item.id);
      return u ? { ...u, addedAt: item.addedAt } : null;
    }).filter(Boolean);
  }, [all, items]);

  const totalCost = useMemo(() => {
    return (unis as any[]).reduce((s, u: any) => s + (u.annualCostRmb || 0), 0);
  }, [unis]);

  const tiers = useMemo(() => {
    const t = { reach: 0, target: 0, safety: 0 };
    (unis as any[]).forEach((u: any) => {
      if (u.rankingTier === "top20") t.reach++;
      else if (u.rankingTier === "top50") t.target++;
      else t.safety++;
    });
    return t;
  }, [unis]);

  const filtered = useMemo(() => {
    if (!sq) return [];
    const q = sq.toLowerCase();
    return all.filter((u: any) =>
      u.chineseName.toLowerCase().includes(q) || u.name.toLowerCase().includes(q) || (u.city || "").toLowerCase().includes(q)
    ).slice(0, 10);
  }, [all, sq]);

  return (
    <div>
      <header className="border-b border-line bg-panel px-5 py-3">
        <div className="mx-auto flex max-w-6xl items-center gap-3">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-ink text-panel"><Bookmark size={18} /></div>
          <div><h1 className="text-base font-semibold text-ink">我的选校单</h1><p className="text-xs text-ink/52">第 4 步：沉淀候选学校，管理、对比并导出家庭讨论版本</p></div>
          <div className="ml-auto flex items-center gap-2">
            <Link href="/map" className="rounded-md border border-line/50 px-2.5 py-1 text-[11px] font-medium text-ink/60 transition-colors hover:bg-white hover:text-ink">← 地图验证</Link>
            <Link href="/assessment" className="rounded-md bg-ink px-2.5 py-1 text-[11px] font-medium text-panel transition-colors hover:bg-ink/90">方案体检</Link>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 pt-4"><ProductJourney active="portfolio" compact /></div>

      <main className="mx-auto max-w-4xl px-4 py-6">
        {/* Summary */}
        {unis.length > 0 && (
          <div className="mb-6 grid grid-cols-4 gap-3">
            <div className="rounded-xl border border-line/40 bg-white/90 p-3 text-center shadow-sm">
              <div className="text-lg font-bold text-ink">{unis.length}</div>
              <div className="text-[10px] text-ink/44">已选学校</div>
            </div>
            <div className="rounded-xl border border-line/40 bg-jade/10 p-3 text-center shadow-sm">
              <div className="text-lg font-bold text-jade">{tiers.reach}</div>
              <div className="text-[10px] text-jade/60">冲刺 (Reach)</div>
            </div>
            <div className="rounded-xl border border-line/40 bg-cobalt/10 p-3 text-center shadow-sm">
              <div className="text-lg font-bold text-cobalt">{tiers.target}</div>
              <div className="text-[10px] text-cobalt/60">匹配 (Target)</div>
            </div>
            <div className="rounded-xl border border-line/40 bg-persimmon/10 p-3 text-center shadow-sm">
              <div className="text-lg font-bold text-persimmon">{tiers.safety}</div>
              <div className="text-[10px] text-persimmon/60">保底 (Safety)</div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <button onClick={() => setShowAdd(!showAdd)} className="inline-flex items-center gap-1.5 rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-panel transition-colors hover:bg-ink/90">
            <Plus size={12} /> 添加学校
          </button>
          {unis.length > 0 && (
            <>
              <button onClick={handleExport} className="inline-flex items-center gap-1.5 rounded-lg border border-line/50 bg-white/80 px-3 py-1.5 text-xs font-medium text-ink/60 transition-colors hover:bg-white hover:text-ink">
                <Download size={12} /> 导出
              </button>
              <button onClick={handleClear} className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-400 transition-colors hover:bg-red-50">
                <Trash2 size={12} /> 清空
              </button>
            </>
          )}
        </div>

        {/* Search & Add */}
        {showAdd && (
          <div className="mb-4 rounded-xl border border-line/50 bg-white/90 p-4 shadow-sm">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink/30" />
              <input type="text" value={sq} onChange={(e) => setSq(e.target.value)}
                placeholder="搜索大学名称或城市..." autoFocus
                className="w-full rounded-lg border border-line/60 bg-white py-2 pl-9 pr-3 text-sm text-ink outline-none focus:border-cobalt/50" />
            </div>
            {filtered.length > 0 && (
              <div className="mt-2 space-y-1">
                {filtered.map((u: any) => (
                  <div key={u.id} className="flex items-center justify-between rounded-lg px-3 py-2 transition-colors hover:bg-paper">
                    <div>
                      <div className="text-sm font-medium text-ink">{u.chineseName}</div>
                      <div className="text-[10px] text-ink/40">{u.name} · {u.city} · {(u.annualCostRmb / 10000).toFixed(0)}万/年</div>
                    </div>
                    <button onClick={() => add(u.id)} className="rounded-md border border-line/50 px-2 py-1 text-[10px] font-medium text-ink/60 hover:bg-ink hover:text-panel transition-colors">添加</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {unis.length === 0 && !showAdd && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-4 grid h-16 w-16 place-items-center rounded-full bg-ink/5 text-ink/20"><Bookmark size={32} /></div>
            <h2 className="text-base font-semibold text-ink/60">选校单还是空的</h2>
            <p className="mt-1 max-w-xs text-xs text-ink/40">先去智能匹配加入候选学校，或点击上方「添加学校」搜索你感兴趣的大学</p>
            <div className="mt-6 flex gap-3">
              <Link href="/match" className="rounded-lg bg-cobalt px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-cobalt/90">去智能选校</Link>
              <button onClick={() => setShowAdd(true)} className="rounded-lg border border-line/50 px-4 py-2 text-xs font-medium text-ink/60 transition-colors hover:bg-white hover:text-ink">添加学校</button>
            </div>
          </div>
        )}

        {/* School list */}
        {unis.length > 0 && (
          <div className="space-y-2">
            {(unis as any[]).map((u: any, i: number) => (
              <div key={u.id} className="rounded-xl border border-line/40 bg-white/90 shadow-sm transition hover:shadow-md">
                <div className="flex items-start gap-3 px-4 py-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-cobalt/10 text-xs font-bold text-cobalt">{i + 1}</div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-semibold text-ink">{u.chineseName}</span>
                      <span className="rounded bg-ink/6 px-1.5 py-0.5 text-[10px] font-medium text-ink/50">{u.rankingTier}</span>
                      <span className="text-[10px] text-ink/36">{u.name}</span>
                    </div>
                    <div className="mt-0.5 flex items-center gap-2 text-[11px] text-ink/48">
                      <span>{u.city}, {u.state}</span>
                      <span>·</span>
                      <span className="text-persimmon">¥{(u.annualCostRmb / 10000).toFixed(0)}万/年</span>
                      <span>·</span>
                      <span>加入于 {u.addedAt}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button onClick={() => setExpanded(expanded === u.id ? null : u.id)} className="rounded-md p-1.5 text-ink/30 transition-colors hover:bg-ink/5 hover:text-ink">
                      {expanded === u.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>
                    <button onClick={() => remove(u.id)} className="rounded-md p-1.5 text-ink/30 transition-colors hover:bg-red-50 hover:text-red-400"><X size={14} /></button>
                  </div>
                </div>
                {expanded === u.id && (
                  <div className="border-t border-line/30 px-4 py-3">
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div className="rounded-md bg-paper px-2.5 py-1.5"><div className="text-[10px] text-ink/44">安全评分</div><div className="font-semibold text-ink">{u.safetyScore}/100</div></div>
                      <div className="rounded-md bg-paper px-2.5 py-1.5"><div className="text-[10px] text-ink/44">录取率</div><div className="font-semibold text-ink">{u.admissionRate}%</div></div>
                      <div className="rounded-md bg-paper px-2.5 py-1.5"><div className="text-[10px] text-ink/44">华人社区</div><div className="font-semibold text-ink">{u.chineseCommunity === "high" ? "高" : u.chineseCommunity === "medium" ? "中" : "低"}</div></div>
                    </div>
                    {u.programs && u.programs.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {u.programs.slice(0, 5).map((p: string) => (
                          <span key={p} className="rounded-full bg-cobalt/8 px-2 py-0.5 text-[10px] text-cobalt">{p}</span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}