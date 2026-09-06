"use client";

import Link from "next/link";
import {
  ArrowUpRight,
  BadgeDollarSign,
  Bell,
  BookOpen,
  CalendarDays,
  Check,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  ExternalLink,
  GraduationCap,
  Inbox,
  Landmark,
  ListFilter,
  Radar,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import type { NewsArticle } from "@/domain/dataset";
import { useNews } from "@/hooks/use-data-source";
import { DataUnavailableState } from "@/components/shared/data-states";
import { useDataSource } from "@/services/data-source-provider";

const STORAGE_KEY = "pathos_followed_universities";

const LABELS: Record<string, string> = {
  new_program: "新项目",
  application_change: "申请变化",
  deadline: "截止日期",
  scholarship: "奖学金",
  policy: "政策动态",
  campus_update: "学校动态",
  admissions: "录取申请",
  visa: "签证",
  career: "职业发展",
  other: "其他动态",
};

type CategoryMeta = {
  label: string;
  icon: LucideIcon;
  iconSurface: string;
  badge: string;
};

const CATEGORY_META: Record<string, CategoryMeta> = {
  new_program: {
    label: "新项目",
    icon: GraduationCap,
    iconSurface: "bg-cobalt/10 text-cobalt",
    badge: "border-cobalt/20 bg-cobalt/10 text-cobalt",
  },
  application_change: {
    label: "申请变化",
    icon: ListFilter,
    iconSurface: "bg-persimmon/10 text-persimmon",
    badge: "border-persimmon/20 bg-persimmon/10 text-persimmon",
  },
  deadline: {
    label: "截止日期",
    icon: CalendarDays,
    iconSurface: "bg-persimmon/10 text-persimmon",
    badge: "border-persimmon/20 bg-persimmon/10 text-persimmon",
  },
  scholarship: {
    label: "奖学金",
    icon: BadgeDollarSign,
    iconSurface: "bg-jade/10 text-jade",
    badge: "border-jade/20 bg-jade/10 text-jade",
  },
  policy: {
    label: "政策动态",
    icon: Landmark,
    iconSurface: "bg-ink/8 text-ink",
    badge: "border-ink/15 bg-ink/8 text-ink",
  },
  campus_update: {
    label: "学校动态",
    icon: BookOpen,
    iconSurface: "bg-cobalt/10 text-cobalt",
    badge: "border-cobalt/20 bg-cobalt/10 text-cobalt",
  },
};

const DEFAULT_CATEGORY_META: CategoryMeta = {
  label: "其他动态",
  icon: Radar,
  iconSurface: "bg-surface-muted text-text-secondary",
  badge: "border-border-soft bg-surface-muted text-text-secondary",
};

type SortMode = "latest" | "deadline";

function categoryFor(item: NewsArticle): string {
  return item.eventType || item.category || "other";
}

function categoryMeta(category: string): CategoryMeta {
  return CATEGORY_META[category] || {
    ...DEFAULT_CATEGORY_META,
    label: LABELS[category] || category,
  };
}

function parseTimestamp(value?: string): number | null {
  if (!value) return null;
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? null : timestamp;
}

function formatDate(value?: string): string {
  if (!value) return "日期待核验";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.getFullYear() + "年" + (date.getMonth() + 1) + "月" + date.getDate() + "日";
}

function daysUntil(value?: string): number | null {
  const timestamp = parseTimestamp(value);
  if (timestamp === null) return null;

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(timestamp);
  target.setHours(0, 0, 0, 0);
  return Math.ceil((target.getTime() - today.getTime()) / 86_400_000);
}

function deadlineCopy(value?: string): string {
  const days = daysUntil(value);
  if (days === null) return "截止日待核验";
  if (days < 0) return "已过期";
  if (days === 0) return "今天截止";
  return "还有 " + days + " 天";
}

function loadFollowing(): string[] {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    const parsed: unknown = value ? JSON.parse(value) : [];
    return Array.isArray(parsed) && parsed.every((item) => typeof item === "string") ? parsed : [];
  } catch {
    return [];
  }
}

function persistFollowing(ids: string[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // Local preference storage is optional; the page remains usable when blocked.
  }
}

export default function OpportunitiesPage() {
  const source = useDataSource();
  const state = useNews(source);
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [sortMode, setSortMode] = useState<SortMode>("latest");
  const [followingOnly, setFollowingOnly] = useState(false);
  const [following, setFollowing] = useState<string[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    setFollowing(loadFollowing());
  }, []);

  const isLoading = state.state.status === "loading";
  const isError = state.state.status === "error";
  const isReady = state.state.status === "ready";
  const articles: NewsArticle[] = useMemo(
    () => (state.state.status === "ready" ? state.state.data : []),
    [state.state],
  );

  const categories = useMemo(() => {
    const seen = new Set(articles.map(categoryFor));
    const preferredOrder = [
      "new_program",
      "deadline",
      "scholarship",
      "application_change",
      "policy",
      "campus_update",
      "other",
    ];
    return Array.from(seen).sort((left, right) => {
      const leftIndex = preferredOrder.indexOf(left);
      const rightIndex = preferredOrder.indexOf(right);
      return (leftIndex < 0 ? 99 : leftIndex) - (rightIndex < 0 ? 99 : rightIndex);
    });
  }, [articles]);

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    const result = articles.filter((item) => {
      const matchesCategory = !category || categoryFor(item) === category;
      const matchesFollowing = !followingOnly || (!!item.universityId && following.includes(item.universityId));
      const searchText = [
        item.title,
        item.titleEn,
        item.summary,
        item.whatChanged,
        item.whyItMatters,
        item.universityName,
        item.universityNameZh,
        ...(item.audience || []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLocaleLowerCase();
      return matchesCategory && matchesFollowing && (!normalizedQuery || searchText.includes(normalizedQuery));
    });

    return result.sort((left, right) => {
      if (sortMode === "deadline") {
        const leftDays = daysUntil(left.actionDeadline);
        const rightDays = daysUntil(right.actionDeadline);
        if (leftDays !== null && rightDays === null) return -1;
        if (leftDays === null && rightDays !== null) return 1;
        if (leftDays !== null && rightDays !== null && leftDays !== rightDays) return leftDays - rightDays;
      }
      return (parseTimestamp(right.publishedAt) || 0) - (parseTimestamp(left.publishedAt) || 0);
    });
  }, [articles, category, following, followingOnly, query, sortMode]);

  const selectedArticle = filtered.find((item) => item.id === selectedId) || null;

  useEffect(() => {
    if (filtered.length === 0) {
      if (selectedId !== null) setSelectedId(null);
      return;
    }
    if (!selectedId || !filtered.some((item) => item.id === selectedId)) {
      setSelectedId(filtered[0].id);
    }
  }, [filtered, selectedId]);

  const metrics = useMemo(() => {
    const upcoming = articles.filter((item) => {
      const days = daysUntil(item.actionDeadline);
      return days !== null && days >= 0 && days <= 30;
    }).length;
    return {
      total: articles.length,
      newPrograms: articles.filter((item) => categoryFor(item) === "new_program").length,
      upcoming,
      scholarships: articles.filter((item) => categoryFor(item) === "scholarship").length,
    };
  }, [articles]);

  const latestPublishedAt = useMemo(() => {
    return articles.reduce<string | undefined>((latest, item) => {
      if (!latest) return item.publishedAt;
      return (parseTimestamp(item.publishedAt) || 0) > (parseTimestamp(latest) || 0) ? item.publishedAt : latest;
    }, undefined);
  }, [articles]);

  const hasFilters = !!category || !!query.trim() || followingOnly;

  function toggleFollowing(universityId: string): void {
    const next = following.includes(universityId)
      ? following.filter((id) => id !== universityId)
      : [...following, universityId];
    setFollowing(next);
    persistFollowing(next);
  }

  function clearFilters(): void {
    setCategory("");
    setQuery("");
    setFollowingOnly(false);
  }

  return (
    <main className="min-h-screen bg-surface-base">
      <div className="mx-auto max-w-page px-4 pb-16 pt-6 sm:px-6 lg:pt-8">
        <header>
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div className="max-w-2xl">
              <div className="flex items-center gap-2 text-label uppercase text-text-tertiary">
                <Radar size={13} className="text-cobalt" aria-hidden="true" />
                <span>PathOS / Opportunity Radar</span>
              </div>
              <h1 className="mt-3 text-display text-text-primary">机会动态</h1>
              <p className="mt-3 max-w-xl text-body text-text-secondary">把学校的重要变化整理成可以理解、可以核验、也可以行动的信息。</p>
            </div>
            <div className="flex items-center gap-2 text-caption text-text-tertiary">
              <span className={"h-2 w-2 rounded-full " + (isError ? "bg-danger" : isLoading ? "bg-persimmon" : "bg-jade")} />
              <span>{isLoading ? "正在同步" : isError ? "暂时不可用" : "信息状态正常"}</span>
              <span className="text-border-strong">·</span>
              <span>{latestPublishedAt ? "更新至 " + formatDate(latestPublishedAt) : "等待首条核验"}</span>
            </div>
          </div>

          <div className="mt-7 grid overflow-hidden rounded-card border border-border-soft bg-surface-1 shadow-pop sm:grid-cols-4">
            <SummaryMetric icon={Inbox} label="已收录动态" value={metrics.total} />
            <SummaryMetric icon={GraduationCap} label="新项目" value={metrics.newPrograms} />
            <SummaryMetric icon={CalendarDays} label="30天内截止" value={metrics.upcoming} />
            <SummaryMetric icon={BadgeDollarSign} label="奖学金" value={metrics.scholarships} />
          </div>
        </header>

        <section className="mt-6 overflow-hidden rounded-card border border-border-soft bg-surface-1 shadow-pop" aria-label="机会筛选工具">
          <div className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center">
            <label className="relative min-w-0 flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" size={16} aria-hidden="true" />
              <span className="sr-only">搜索机会动态</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="搜索学校、项目或关键词"
                className="h-control w-full rounded-control border border-border-soft bg-surface-base pl-9 pr-9 text-sm text-text-primary outline-none transition-colors placeholder:text-text-tertiary focus:border-cobalt"
              />
              {query && (
                <button type="button" onClick={() => setQuery("")} className="absolute right-2 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-control text-text-tertiary transition-colors hover:bg-surface-muted hover:text-text-primary" aria-label="清除搜索" title="清除搜索">
                  <X size={14} />
                </button>
              )}
            </label>

            <label className="relative flex h-control shrink-0 items-center gap-2 rounded-control border border-border-soft bg-surface-base px-3 text-sm text-text-secondary">
              <span className="sr-only">排序方式</span>
              <ListFilter size={15} className="text-text-tertiary" aria-hidden="true" />
              <select value={sortMode} onChange={(event) => setSortMode(event.target.value as SortMode)} className="appearance-none bg-transparent pr-5 text-sm outline-none" aria-label="排序方式">
                <option value="latest">最新发布</option>
                <option value="deadline">截止时间优先</option>
              </select>
              <ChevronDown size={14} className="pointer-events-none absolute right-2 text-text-tertiary" aria-hidden="true" />
            </label>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto border-t border-border-soft px-3 py-2.5 scrollbar-thin">
            <div className="flex min-w-max items-center gap-1.5" role="group" aria-label="机会类型">
              <FilterButton active={!category} onClick={() => setCategory("")}>全部</FilterButton>
              {categories.map((item) => (
                <FilterButton key={item} active={category === item} onClick={() => setCategory(item)}>
                  {categoryMeta(item).label}
                </FilterButton>
              ))}
            </div>
            <div className="ml-auto flex shrink-0 items-center gap-2 pl-2">
              <button type="button" onClick={() => setFollowingOnly((value) => !value)} className={"inline-flex h-control items-center gap-1.5 rounded-control px-3 text-xs font-semibold transition-colors " + (followingOnly ? "bg-persimmon text-paper" : "border border-border-soft bg-surface-base text-text-secondary hover:border-border-strong hover:text-text-primary")} aria-pressed={followingOnly}>
                <Bell size={14} aria-hidden="true" />
                我的学校
              </button>
              <span className="whitespace-nowrap text-caption text-text-tertiary" aria-live="polite">{filtered.length} 条结果</span>
            </div>
          </div>
        </section>

        {isLoading && <OpportunitySkeleton />}
        {isError && <div className="mt-6"><DataUnavailableState reason="机会动态暂时无法加载，请稍后重试。" onRetry={() => state.reload()} /></div>}
        {isReady && articles.length === 0 && <EmptyRadarState />}
        {isReady && articles.length > 0 && filtered.length === 0 && <NoResultsState hasFilters={hasFilters} onClear={clearFilters} />}

        {isReady && filtered.length > 0 && (
          <div className="mt-6 grid items-start gap-5 lg:grid-cols-[minmax(0,0.9fr)_minmax(360px,1.1fr)]">
            <section className="min-w-0 overflow-hidden rounded-card border border-border-soft bg-surface-1 shadow-pop" aria-labelledby="opportunity-list-title">
              <div className="flex items-center justify-between border-b border-border-soft px-4 py-4 sm:px-5">
                <div>
                  <p id="opportunity-list-title" className="text-section text-text-primary">动态列表</p>
                  <p className="mt-1 text-caption text-text-tertiary">按时间和行动优先级整理</p>
                </div>
                <span className="inline-flex items-center gap-1.5 text-caption text-text-tertiary"><ShieldCheck size={14} className="text-jade" aria-hidden="true" />来源可追溯</span>
              </div>
              <div className="divide-y divide-border-soft">
                {filtered.map((item) => (
                  <OpportunityRow key={item.id} item={item} selected={item.id === selectedId} followed={!!item.universityId && following.includes(item.universityId)} onSelect={() => setSelectedId(item.id)} />
                ))}
              </div>
            </section>

            <div className="hidden min-w-0 lg:block">
              {selectedArticle ? <OpportunityDetail item={selectedArticle} followed={!!selectedArticle.universityId && following.includes(selectedArticle.universityId)} onToggleFollowing={toggleFollowing} /> : <SelectionPlaceholder />}
            </div>
          </div>
        )}

        {selectedArticle && (
          <div className="lg:hidden">
            <button type="button" className="fixed inset-0 z-40 cursor-default bg-ink/25" onClick={() => setSelectedId(null)} aria-label="关闭机会详情" />
            <div className="fixed inset-x-0 bottom-0 z-50 max-h-[86vh] overflow-y-auto rounded-t-overlay border border-border-soft bg-surface-1 shadow-overlay scrollbar-thin">
              <OpportunityDetail item={selectedArticle} followed={!!selectedArticle.universityId && following.includes(selectedArticle.universityId)} onToggleFollowing={toggleFollowing} onClose={() => setSelectedId(null)} className="rounded-none border-0 shadow-none" />
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

function SummaryMetric({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: number }) {
  return (
    <div className="flex items-center gap-3 border-b border-border-soft px-4 py-3.5 last:border-b-0 sm:border-b-0 sm:border-r sm:last:border-r-0">
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-control bg-surface-muted text-cobalt"><Icon size={16} aria-hidden="true" /></span>
      <div className="min-w-0"><p className="text-lg font-semibold text-text-primary">{value}</p><p className="text-caption text-text-tertiary">{label}</p></div>
    </div>
  );
}

function FilterButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick} className={"h-control rounded-control px-3 text-xs font-semibold transition-colors " + (active ? "bg-ink text-paper" : "text-text-secondary hover:bg-surface-muted hover:text-text-primary")} aria-pressed={active}>
      {children}
    </button>
  );
}

function OpportunityRow({ item, selected, followed, onSelect }: { item: NewsArticle; selected: boolean; followed: boolean; onSelect: () => void }) {
  const meta = categoryMeta(categoryFor(item));
  const Icon = meta.icon;
  const days = daysUntil(item.actionDeadline);
  const school = item.universityNameZh || item.universityName || "院校信息待补充";

  return (
    <button type="button" onClick={onSelect} className={"group relative block w-full text-left transition-colors duration-200 motion-safe:transition-transform motion-safe:duration-200 " + (selected ? "bg-cobalt/8" : "hover:bg-surface-muted/55")} aria-pressed={selected} aria-label={"查看" + school + "：" + item.title}>
      <span className={"absolute inset-y-0 left-0 w-0.5 transition-colors " + (selected ? "bg-cobalt" : "bg-transparent")} />
      <div className="flex gap-3 px-4 py-4 sm:px-5">
        <span className={"grid h-9 w-9 shrink-0 place-items-center rounded-control " + meta.iconSurface}><Icon size={17} aria-hidden="true" /></span>
        <span className="min-w-0 flex-1">
          <span className="flex items-start justify-between gap-3">
            <span className="min-w-0">
              <span className="flex flex-wrap items-center gap-1.5">
                <span className={"inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold " + meta.badge}>{meta.label}</span>
                {item.importance === "high" && <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-persimmon"><CircleAlert size={11} aria-hidden="true" />优先查看</span>}
                {followed && <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-jade"><Bell size={10} aria-hidden="true" />已关注</span>}
              </span>
              <span className="mt-2 block truncate text-xs font-semibold text-cobalt">{school}</span>
              <span className="mt-1 block text-sm font-semibold leading-6 text-text-primary">{item.title}</span>
            </span>
            <ChevronRight size={17} className={"mt-1 shrink-0 text-text-tertiary transition-transform duration-200 " + (selected ? "translate-x-0.5 text-cobalt" : "group-hover:translate-x-0.5")} aria-hidden="true" />
          </span>
          <span className="mt-1.5 block line-clamp-2 text-xs leading-5 text-text-secondary">{item.whatChanged || item.summary || "这条动态正在补充解释。"}</span>
          <span className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-text-tertiary">
            <span className={days !== null && days >= 0 && days <= 30 ? "inline-flex items-center gap-1 font-semibold text-persimmon" : "inline-flex items-center gap-1"}><CalendarDays size={12} aria-hidden="true" />{days !== null ? deadlineCopy(item.actionDeadline) : "行动时间待核验"}</span>
            <span aria-hidden="true">·</span>
            <span>发布于 {formatDate(item.publishedAt)}</span>
          </span>
        </span>
      </div>
    </button>
  );
}

function OpportunityDetail({ item, followed, onToggleFollowing, onClose, className = "" }: { item: NewsArticle; followed: boolean; onToggleFollowing: (universityId: string) => void; onClose?: () => void; className?: string }) {
  const meta = categoryMeta(categoryFor(item));
  const Icon = meta.icon;
  const school = item.universityNameZh || item.universityName || "院校信息待补充";
  const universityId = item.universityId;
  const audience = item.audience?.filter(Boolean) || [];
  const actionSteps = item.actionSteps?.filter(Boolean) || [];
  const days = daysUntil(item.actionDeadline);

  return (
    <section className={"overflow-hidden rounded-card border border-border-soft bg-surface-1 shadow-panel " + className} aria-labelledby={"opportunity-detail-" + item.id}>
      <div className="border-b border-border-soft p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className={"grid h-10 w-10 place-items-center rounded-control " + meta.iconSurface}><Icon size={19} aria-hidden="true" /></span>
            <div><p className="text-label uppercase text-text-tertiary">当前选中</p><p className="mt-1 text-xs font-semibold text-text-secondary">{meta.label}</p></div>
          </div>
          {onClose && <button type="button" onClick={onClose} className="grid h-control w-control place-items-center rounded-control text-text-tertiary transition-colors hover:bg-surface-muted hover:text-text-primary" aria-label="关闭详情" title="关闭详情"><X size={17} /></button>}
        </div>
        <p className="mt-5 text-sm font-semibold text-cobalt">{school}</p>
        <h2 id={"opportunity-detail-" + item.id} className="mt-2 text-xl font-semibold leading-8 text-text-primary">{item.title}</h2>
        {item.titleEn && <p className="mt-1 text-xs leading-5 text-text-tertiary">{item.titleEn}</p>}
        <div className="mt-5 grid gap-2 sm:grid-cols-2">
          <DetailFact icon={CalendarDays} label="行动截止" value={item.actionDeadline ? deadlineCopy(item.actionDeadline) + " · " + formatDate(item.actionDeadline) : "日期待核验"} urgent={days !== null && days >= 0 && days <= 30} />
          <DetailFact icon={Users} label="适合人群" value={audience.length ? audience.join("、") : "适用人群待核验"} />
        </div>
      </div>

      <div className="divide-y divide-border-soft">
        <DetailSection title="发生了什么" text={item.whatChanged || item.summary || "这条动态正在补充解释。"} />
        <DetailSection title="为什么值得关注" text={item.whyItMatters || "请结合你的申请年份、专业和身份核对是否适用。"} />
        <section className="px-5 py-5 sm:px-6">
          <p className="text-label uppercase text-text-tertiary">下一步</p>
          {actionSteps.length > 0 ? (
            <ol className="mt-3 space-y-2.5">
              {actionSteps.map((step, index) => <li key={item.id + "-step-" + index} className="flex gap-2.5 text-sm leading-6 text-text-secondary"><span className="mt-1 grid h-4 w-4 shrink-0 place-items-center rounded-full bg-jade/10 text-jade"><Check size={11} strokeWidth={2.5} aria-hidden="true" /></span><span>{step}</span></li>)}
            </ol>
          ) : <p className="mt-3 text-sm leading-6 text-text-secondary">打开官方页面，确认资格、截止日期和申请方式。</p>}
        </section>
      </div>

      <div className="border-t border-border-soft px-5 py-4 sm:px-6">
        <div className="flex items-start gap-2 text-xs leading-5 text-text-tertiary"><ShieldCheck size={15} className="mt-0.5 shrink-0 text-jade" aria-hidden="true" /><span>来源：{item.source || "来源信息待补充"}{item.sourceStatus ? " · 来源状态已记录" : " · 请以官方页面为准"}</span></div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          {item.url && <a href={item.url} target="_blank" rel="noreferrer" className="inline-flex h-control items-center gap-1.5 rounded-control bg-cobalt px-3 text-xs font-semibold text-paper transition-colors hover:bg-cobalt/85"><ExternalLink size={14} aria-hidden="true" />访问官方页面</a>}
          {universityId && <Link href={"/university/" + encodeURIComponent(universityId)} className="inline-flex h-control items-center gap-1.5 rounded-control border border-border-soft px-3 text-xs font-semibold text-text-secondary transition-colors hover:border-border-strong hover:text-text-primary"><ArrowUpRight size={14} aria-hidden="true" />查看学校</Link>}
          {universityId && <button type="button" onClick={() => onToggleFollowing(universityId)} className={"ml-auto inline-flex h-control items-center gap-1.5 rounded-control px-3 text-xs font-semibold transition-colors " + (followed ? "bg-jade/10 text-jade" : "text-text-secondary hover:bg-surface-muted hover:text-text-primary")} aria-pressed={followed}><Bell size={14} aria-hidden="true" />{followed ? "已关注" : "关注学校"}</button>}
        </div>
      </div>
    </section>
  );
}

function DetailFact({ icon: Icon, label, value, urgent = false }: { icon: LucideIcon; label: string; value: string; urgent?: boolean }) {
  return <div className="flex min-w-0 gap-2.5 rounded-control bg-surface-muted px-3 py-2.5"><Icon size={15} className={"mt-0.5 shrink-0 " + (urgent ? "text-persimmon" : "text-text-tertiary")} aria-hidden="true" /><div className="min-w-0"><p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-text-tertiary">{label}</p><p className={"mt-1 text-xs leading-5 " + (urgent ? "font-semibold text-persimmon" : "text-text-secondary")}>{value}</p></div></div>;
}

function DetailSection({ title, text }: { title: string; text: string }) {
  return <section className="px-5 py-5 sm:px-6"><p className="text-label uppercase text-text-tertiary">{title}</p><p className="mt-3 text-sm leading-7 text-text-secondary">{text}</p></section>;
}

function SelectionPlaceholder() {
  return <aside className="sticky top-6 overflow-hidden rounded-card border border-border-soft bg-surface-1 shadow-pop"><div className="flex min-h-[26rem] flex-col items-center justify-center px-8 py-12 text-center"><span className="grid h-12 w-12 place-items-center rounded-card bg-cobalt/10 text-cobalt"><Sparkles size={21} aria-hidden="true" /></span><p className="mt-5 text-label uppercase text-text-tertiary">查看详情</p><h2 className="mt-2 text-section text-text-primary">选择一条动态</h2><p className="mt-2 max-w-xs text-sm leading-6 text-text-secondary">在左侧选择机会，查看影响、适用人群和下一步行动。</p></div></aside>;
}

function EmptyRadarState() {
  return <section className="mt-6 overflow-hidden rounded-card border border-border-soft bg-surface-1 shadow-pop" role="status"><div className="grid lg:grid-cols-[1.15fr_0.85fr]"><div className="p-6 sm:p-8"><span className="grid h-12 w-12 place-items-center rounded-card bg-cobalt/10 text-cobalt"><Inbox size={22} aria-hidden="true" /></span><p className="mt-6 text-label uppercase text-text-tertiary">Radar status</p><h2 className="mt-2 text-xl font-semibold leading-8 text-text-primary">目前没有新的已核验机会</h2><p className="mt-3 max-w-xl text-sm leading-7 text-text-secondary">我们只在来源完成核验后发布动态。现在没有可确认的新记录，不代表学校没有变化。</p><Link href="/guides" className="mt-6 inline-flex h-control items-center gap-1.5 rounded-control bg-ink px-3 text-xs font-semibold text-paper transition-colors hover:bg-ink/85">浏览大学指南<ArrowUpRight size={14} aria-hidden="true" /></Link></div><div className="border-t border-border-soft p-6 sm:p-8 lg:border-l lg:border-t-0"><p className="text-label uppercase text-text-tertiary">这里会看到</p><div className="mt-5 space-y-4"><EmptyItem icon={GraduationCap} title="新课程与新项目" text="学校发布了新的学习机会。" /><EmptyItem icon={CalendarDays} title="申请时间变化" text="截止日期或申请要求发生变化。" /><EmptyItem icon={BadgeDollarSign} title="奖学金机会" text="值得关注的资助和费用信息。" /></div></div></div></section>;
}

function EmptyItem({ icon: Icon, title, text }: { icon: LucideIcon; title: string; text: string }) {
  return <div className="flex gap-3"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-control bg-surface-muted text-cobalt"><Icon size={15} aria-hidden="true" /></span><div><p className="text-sm font-semibold text-text-primary">{title}</p><p className="mt-1 text-xs leading-5 text-text-secondary">{text}</p></div></div>;
}

function NoResultsState({ hasFilters, onClear }: { hasFilters: boolean; onClear: () => void }) {
  return <section className="mt-6 rounded-card border border-border-soft bg-surface-1 px-6 py-12 text-center shadow-pop" role="status"><span className="mx-auto grid h-11 w-11 place-items-center rounded-card bg-surface-muted text-text-secondary"><Search size={19} aria-hidden="true" /></span><h2 className="mt-4 text-section text-text-primary">没有找到符合条件的机会</h2><p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-text-secondary">{hasFilters ? "试试放宽学校、日期或机会类型筛选。" : "目前还没有可以显示的动态。"}</p>{hasFilters && <button type="button" onClick={onClear} className="mt-5 inline-flex h-control items-center gap-1.5 rounded-control border border-border-soft px-3 text-xs font-semibold text-text-secondary transition-colors hover:border-border-strong hover:text-text-primary">清除筛选<X size={14} aria-hidden="true" /></button>}</section>;
}

function OpportunitySkeleton() {
  return <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,0.9fr)_minmax(360px,1.1fr)]" aria-label="正在加载机会动态" role="status"><div className="overflow-hidden rounded-card border border-border-soft bg-surface-1 p-5 shadow-pop"><div className="h-5 w-24 animate-pulse rounded bg-surface-muted" /><div className="mt-5 space-y-5">{[0, 1, 2].map((item) => <div key={item} className="flex gap-3 border-b border-border-soft pb-5 last:border-b-0 last:pb-0"><div className="h-9 w-9 shrink-0 animate-pulse rounded-control bg-surface-muted" /><div className="min-w-0 flex-1 space-y-2"><div className="h-3 w-20 animate-pulse rounded bg-surface-muted" /><div className="h-4 w-3/4 animate-pulse rounded bg-surface-muted" /><div className="h-3 w-full animate-pulse rounded bg-surface-muted" /><div className="h-3 w-1/2 animate-pulse rounded bg-surface-muted" /></div></div>)}</div></div><div className="hidden min-h-[26rem] animate-pulse rounded-card border border-border-soft bg-surface-1 p-6 shadow-pop lg:block"><div className="h-10 w-10 rounded-control bg-surface-muted" /><div className="mt-7 h-4 w-1/3 rounded bg-surface-muted" /><div className="mt-3 h-7 w-4/5 rounded bg-surface-muted" /><div className="mt-8 h-20 rounded-control bg-surface-muted" /><div className="mt-5 h-20 rounded-control bg-surface-muted" /></div></div>;
}
