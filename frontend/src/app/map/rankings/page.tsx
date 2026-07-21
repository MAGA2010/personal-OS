"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import rankingData from "@/data/university-rankings.json";

type RankKey = "QS" | "ARWU" | "USNews" | "THE";

interface TabDef {
  key: RankKey | "all";
  label: string;
  labelEn: string;
}

const TABS: TabDef[] = [
  { key: "all", label: "综合", labelEn: "All" },
  { key: "QS", label: "QS", labelEn: "QS" },
  { key: "USNews", label: "US News", labelEn: "US News" },
  { key: "THE", label: "THE", labelEn: "THE" },
  { key: "ARWU", label: "ARWU", labelEn: "ARWU" },
];

const RANK_ABBR: Record<RankKey, string> = {
  QS: "QS", ARWU: "ARWU", USNews: "USN", THE: "THE",
};

function rankColor(rank: number | null): string {
  if (rank === null) return "bg-ink/5 text-ink/30";
  if (rank <= 10) return "bg-jade/12 text-jade";
  if (rank <= 30) return "bg-cobalt/10 text-cobalt";
  if (rank <= 50) return "bg-persimmon/10 text-persimmon";
  if (rank <= 100) return "bg-ink/8 text-ink/60";
  return "bg-ink/4 text-ink/40";
}

function rankBadge(rank: number | null): string {
  if (rank === null) return "—";
  if (rank <= 10) return "Top 10";
  if (rank <= 30) return "Top 30";
  if (rank <= 50) return "Top 50";
  if (rank <= 100) return "Top 100";
  return "100+";
}

function parseLocation(desc: string): string {
  const m = desc.match(/位于(.+?)[，,]/);
  return m ? m[1] : "";
}

function extractSubjects(desc: string): string[] {
  const m = desc.match(/优势学科：(.+?)(?:，创建于|$)/);
  if (!m) return [];
  return m[1].split(/[、，]/).map(s => s.trim()).filter(Boolean);
}

function sortValue(uni: any, key: RankKey | "all"): number {
  if (key === "all") {
    const ranks = [uni.QS, uni.ARWU, uni.USNews, uni.THE].filter((r: any) => r !== null);
    return ranks.length > 0 ? ranks.reduce((a: number, b: number) => a + b, 0) / ranks.length : 9999;
  }
  return uni[key] ?? 9999;
}

export default function RankingsPage() {
  const [activeTab, setActiveTab] = useState<RankKey | "all">("all");
  const [search, setSearch] = useState("");

  const sorted = useMemo(() => {
    const q = search.toLowerCase();
    let data = (rankingData as any[]).filter((u: any) =>
      u.chineseName.toLowerCase().includes(q) ||
      u.id.toLowerCase().includes(q)
    );
    data.sort((a: any, b: any) => sortValue(a, activeTab) - sortValue(b, activeTab));
    return data;
  }, [search, activeTab]);

  return (
    <main className="flex h-screen flex-col bg-paper" aria-label="大学排名">
      {/* Header */}
      <header className="flex shrink-0 items-center border-b border-line bg-panel px-5 py-3">
        <Link
          href="/map"
          className="mr-3 grid h-7 w-7 place-items-center rounded-md text-ink/44 hover:text-ink hover:bg-ink/5 transition-colors"
          aria-label="返回地图"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeLinecap="round"
            strokeLinejoin="round" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M19 12H5m7-7-7 7 7 7" />
          </svg>
        </Link>
        <div className="min-w-0">
          <h1 className="text-base font-semibold text-ink">大学排名</h1>
          <p className="text-xs text-ink/52 truncate">37 所美国大学 · QS · ARWU · US News · THE</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <div className="relative">
            <svg className="pointer-events-none absolute left-2.5 top-1/2 h-3 w-3 -translate-y-1/2 text-ink/24"
              fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round"
              strokeWidth={2} viewBox="0 0 24 24">
              <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
            </svg>
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="搜索大学…"
              className="w-36 rounded-md border border-line/60 bg-white py-1.5 pl-7 pr-2 text-xs text-ink placeholder:text-ink/24 outline-none focus:border-cobalt/40 focus:ring-1 focus:ring-cobalt/20 transition-colors"
            />
          </div>
        </div>
      </header>

      {/* Tab bar */}
      <div className="flex shrink-0 gap-1 border-b border-line/50 bg-panel/90 px-5 py-2.5 overflow-x-auto">
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`shrink-0 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-ink text-panel shadow-sm"
                : "text-ink/48 hover:text-ink hover:bg-ink/5"
            }`}
          >
            {tab.label}
            {tab.key !== "all" && (
              <span className="ml-1 text-[10px] opacity-60">{tab.labelEn}</span>
            )}
          </button>
        ))}
        <span className="ml-auto self-center text-[10px] text-ink/28">
          按 {activeTab === "all" ? "平均排名" : TABS.find(t => t.key === activeTab)?.label} 排序
        </span>
      </div>

      {/* Rankings list */}
      <div className="flex-1 overflow-auto">
        <div className="mx-auto max-w-3xl divide-y divide-line/30">
          {sorted.map((uni: any, idx: number) => {
            const location = parseLocation(uni.description || "");
            const subjects = extractSubjects(uni.description || "");
            const mainRank = activeTab === "all"
              ? Math.round(sortValue(uni, "all"))
              : uni[activeTab];

            return (
              <div
                key={uni.id}
                className="flex items-start gap-4 px-5 py-3.5 transition-colors hover:bg-ink/[0.02]"
              >
                {/* Rank number */}
                <div className="flex w-10 shrink-0 flex-col items-center pt-0.5">
                  <span className={`text-lg font-bold leading-none ${rankColor(mainRank)}`}>
                    {mainRank === 9999 ? "—" : mainRank}
                  </span>
                  <span className={`mt-1 text-[9px] leading-none ${rankColor(mainRank)} opacity-60`}>
                    {rankBadge(mainRank)}
                  </span>
                </div>

                {/* University info */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <h2 className="text-sm font-semibold text-ink truncate">{uni.chineseName}</h2>
                    <span className="shrink-0 text-[10px] text-ink/32" lang="en">{uni.id}</span>
                  </div>
                  {location && (
                    <p className="mt-0.5 text-[11px] text-ink/44">{location}</p>
                  )}

                  {/* All rankings as badges */}
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {(["QS", "ARWU", "USNews", "THE"] as RankKey[]).map(k => {
                      const val = uni[k];
                      return (
                        <span
                          key={k}
                          className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] font-medium ${
                            val ? "bg-ink/5 text-ink/50" : "text-ink/20 bg-ink/[0.02]"
                          }`}
                        >
                          <span className="font-semibold">{RANK_ABBR[k]}</span>
                          {val ?? "—"}
                        </span>
                      );
                    })}
                  </div>

                  {/* Subject rankings */}
                  {subjects.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5">
                      {subjects.slice(0, 3).map((s, i) => (
                        <span key={i} className="text-[10px] text-ink/36">· {s}</span>
                      ))}
                      {subjects.length > 3 && (
                        <span className="text-[10px] text-ink/24">+{subjects.length - 3}</span>
                      )}
                    </div>
                  )}
                </div>

                {/* Right arrow */}
                <svg className="mt-1 h-3.5 w-3.5 shrink-0 text-ink/16" fill="none"
                  stroke="currentColor" strokeLinecap="round" strokeLinejoin="round"
                  strokeWidth={2} viewBox="0 0 24 24">
                  <path d="m9 18 6-6-6-6" />
                </svg>
              </div>
            );
          })}
        </div>

        {sorted.length === 0 && (
          <div className="flex items-center justify-center py-20 text-sm text-ink/36">
            未找到匹配的大学
          </div>
        )}
      </div>
    </main>
  );
}
