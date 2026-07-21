"use client";

import { useState } from "react";
import newsData from "@/data/news.json";
import { ProductJourney } from "@/components/ProductJourney";
import { Newspaper, ExternalLink, ChevronDown, ChevronUp, Clock, Tag } from "lucide-react";

const CATEGORY_LABELS: Record<string, string> = {
  admissions: "录取申请", visa: "签证",
  ranking: "排名", life: "留学生活",
  career: "职业发展", policy: "政策动态",
};

const CAT_COLORS: Record<string,string> = {
  admissions: "bg-cobalt/10 text-cobalt", visa: "bg-persimmon/10 text-persimmon",
  ranking: "bg-jade/10 text-jade", life: "bg-emerald-500/10 text-emerald-600",
  career: "bg-purple-500/10 text-purple-600", policy: "bg-amber-500/10 text-amber-600",
};

function fmtDate(iso: string) {
  try {
    var d = new Date(iso);
    return d.getFullYear() + "年" + String(d.getMonth()+1).padStart(2,"0") + "月" + String(d.getDate()).padStart(2,"0") + "日";
  } catch { return iso; }
}

export default function NewsPage() {
  var articles = ((newsData as any).articles || []) as any[];
  var [expandedId, setExpandedId] = useState<string | null>(null);
  var [activeCategory, setActiveCategory] = useState("");

  var catSet: string[] = [];
  articles.forEach(function(a: any) {
    if (catSet.indexOf(a.category) === -1) catSet.push(a.category);
  });
  var categories = catSet;
  var filtered = activeCategory ? articles.filter(function(a: any) { return a.category === activeCategory; }) : articles;

  return (
    <div>
      <header className="border-b border-line bg-panel px-5 py-3">
        <div className="mx-auto flex max-w-6xl items-center gap-3">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-cobalt text-panel"><Newspaper size={18} /></div>
          <div><h1 className="text-base font-semibold text-ink">留学资讯</h1><p className="text-xs text-ink/52">来自 QS 和选校的最新留学动态</p></div>
        </div>
      </header>
      <div className="mx-auto max-w-6xl px-4 pt-4"><ProductJourney compact /></div>
      <main className="mx-auto max-w-4xl px-4 py-6">
        <div className="mb-6 flex flex-wrap gap-2">
          <button onClick={function() { setActiveCategory(""); }}
            className={"rounded-lg px-3 py-1.5 text-xs font-medium transition-colors " + (!activeCategory ? "bg-ink text-panel" : "bg-white/80 text-ink/60 border border-line/50 hover:bg-white")}>全部</button>
          {categories.map(function(cat: string) {
            return <button key={cat} onClick={function() { setActiveCategory(cat); }}
              className={"rounded-lg px-3 py-1.5 text-xs font-medium transition-colors " + (activeCategory === cat ? "bg-ink text-panel" : "bg-white/80 text-ink/60 border border-line/50 hover:bg-white")}>{CATEGORY_LABELS[cat] || cat}</button>;
          })}
        </div>
        <p className="mb-4 text-xs text-ink/40">共 {filtered.length} 篇文章</p>
        <div className="space-y-3">
          {filtered.map(function(article: any) {
            var isExpanded = expandedId === article.id;
            return (
              <div key={article.id} className="rounded-xl border border-line/40 bg-white/90 shadow-sm transition hover:shadow-md">
                <button onClick={function() { setExpandedId(isExpanded ? null : article.id); }}
                  className="flex w-full items-start gap-3 px-4 py-3 text-left">
                  <div className="min-w-0 flex-1">
                    <h2 className="text-sm font-semibold text-ink line-clamp-1">{article.title}</h2>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-ink/48">
                      <span className={"inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium " + (CAT_COLORS[article.category] || "bg-ink/5 text-ink/60")}>
                        <Tag size={10} /> {CATEGORY_LABELS[article.category] || article.category}
                      </span>
                      <span className="flex items-center gap-1"><Clock size={10} /> {fmtDate(article.publishedAt)}</span>
                      <span>{article.source}</span>
                    </div>
                  </div>
                  <div className="shrink-0 mt-1">{isExpanded ? <ChevronUp size={16} className="text-ink/30" /> : <ChevronDown size={16} className="text-ink/30" />}</div>
                </button>
                {isExpanded && (
                  <div className="border-t border-line/30 px-4 py-3">
                    <p className="text-xs leading-relaxed text-ink/70">{article.summary}</p>
                    <div className="mt-3 flex items-center gap-3">
                      <a href={article.url} target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 rounded-lg bg-cobalt/10 px-3 py-1.5 text-[11px] font-medium text-cobalt transition-colors hover:bg-cobalt/20">
                        <ExternalLink size={12} /> 查看原文
                      </a>
                      <span className="text-[10px] text-ink/32">来源: {article.source}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}