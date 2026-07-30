"use client";

import { useState } from "react";
import { useDataSource } from "@/services/data-source-provider";
import { useNews } from "@/hooks/use-data-source";
import { Newspaper, ExternalLink, ChevronDown, ChevronUp, Clock, Tag } from "lucide-react";
import { DataLoadingState, DataUnavailableState, DataEmptyState } from "@/components/shared/data-states";
import { NewsEntryHero } from "@/components/news/NewsEntryHero";

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
  var [expandedId, setExpandedId] = useState<string | null>(null);
  var [activeCategory, setActiveCategory] = useState("");

  var dataSource = useDataSource();
  var newsState = useNews(dataSource);
  var loading = newsState.state.status === "loading";
  var articles = newsState.state.status === "ready" ? newsState.state.data : [];

  var catSet: string[] = [];
  articles.forEach(function(a: any) {
    if (catSet.indexOf(a.category) === -1) catSet.push(a.category);
  });
  var categories = catSet;
  var filtered = activeCategory ? articles.filter(function(a: any) { return a.category === activeCategory; }) : articles;

  return (
    <div className="min-h-screen bg-surface-base">
      <NewsEntryHero />
      <div id="news-list" className="mx-auto max-w-page">
      <header className="border-b border-border-soft bg-surface-1/70 backdrop-blur">
        <div className="mx-auto flex max-w-page items-center gap-3 px-4 py-3 sm:px-6">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-control bg-cobalt text-paper"><Newspaper size={16} aria-hidden="true" /></div>
          <div className="min-w-0 flex-1">
            <p className="text-label uppercase tracking-[0.12em] text-cobalt">留学资讯</p>
            <h1 className="text-page text-text-primary">最新动态</h1>
          </div>
          <p className="text-caption text-text-secondary">来自 QS 与启德教育的整理</p>
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-4 py-5 sm:px-6">
        <div className="mb-6 flex flex-wrap gap-2">
          <button onClick={function() { setActiveCategory(""); }}
            className={"rounded-lg px-3 py-1.5 text-xs font-medium transition-colors " + (!activeCategory ? "bg-ink text-panel" : "bg-white/80 text-ink/60 border border-line/50 hover:bg-white")}>全部</button>
          {categories.map(function(cat: string) {
            return <button key={cat} onClick={function() { setActiveCategory(cat); }}
              className={"rounded-lg px-3 py-1.5 text-xs font-medium transition-colors " + (activeCategory === cat ? "bg-ink text-panel" : "bg-white/80 text-ink/60 border border-line/50 hover:bg-white")}>{CATEGORY_LABELS[cat] || cat}</button>;
          })}
        </div>
        <p className="mb-4 text-xs text-ink/40">共 {filtered.length} 篇文章</p>
        {loading && (
          <DataLoadingState message="正在加载留学资讯…" />
        )}
        {newsState.state.status === "error" && (
          <DataUnavailableState
            reason="资讯后端暂不可用,后端准备就绪后将自动恢复。"
            onRetry={() => newsState.reload()}
          />
        )}
        {!loading && newsState.state.status === "ready" && articles.length === 0 && (
          <DataEmptyState
            title="数据补充中"
            description="当前暂无留学资讯,后端持续补充中。"
          />
        )}
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
    </div>
  );
}