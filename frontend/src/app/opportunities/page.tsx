"use client";

import "./opportunities.css";

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

type CategoryTone = "neutral" | "blue" | "green" | "orange" | "red";

type CategoryMeta = {
  label: string;
  icon: LucideIcon;
  tone: CategoryTone;
};

const CATEGORY_META: Record<string, CategoryMeta> = {
  new_program: {
    label: "新项目",
    icon: GraduationCap,
    tone: "blue",
  },
  application_change: {
    label: "申请变化",
    icon: ListFilter,
    tone: "orange",
  },
  deadline: {
    label: "截止日期",
    icon: CalendarDays,
    tone: "red",
  },
  scholarship: {
    label: "奖学金",
    icon: BadgeDollarSign,
    tone: "green",
  },
  policy: {
    label: "政策动态",
    icon: Landmark,
    tone: "neutral",
  },
  campus_update: {
    label: "学校动态",
    icon: BookOpen,
    tone: "blue",
  },
};

const DEFAULT_CATEGORY_META: CategoryMeta = {
  label: "其他动态",
  icon: Radar,
  tone: "neutral",
};

const TONE_ICON_CLASS: Record<CategoryTone, string> = {
  neutral: "opp-row-icon",
  blue: "opp-row-icon is-blue",
  green: "opp-row-icon is-green",
  orange: "opp-row-icon is-orange",
  red: "opp-row-icon is-red",
};

const TONE_CHIP_CLASS: Record<CategoryTone, string> = {
  neutral: "opp-chip",
  blue: "opp-chip is-blue",
  green: "opp-chip is-green",
  orange: "opp-chip is-orange",
  red: "opp-chip is-red",
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
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setFollowing(loadFollowing());
  }, []);

  useEffect(() => {
    if (!mobileOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [mobileOpen]);

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

  function selectOpportunity(id: string): void {
    setSelectedId(id);
    setMobileOpen(true);
  }

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
    <main className="opp-root min-h-screen">
      <div className="opp-page">
        <header className="opp-header">
          <div>
            <p className="opp-eyebrow">PathOS / Opportunity Radar</p>
            <h1 className="opp-title">机会动态</h1>
            <p className="opp-description">把学校的重要变化整理成可以理解、可以核验、也可以行动的信息。</p>
          </div>
          <div className="opp-sync" aria-live="polite">
            <span className={"opp-status-dot " + (isError ? "is-error" : isLoading ? "is-loading" : "")} />
            <span>{isLoading ? "正在同步" : isError ? "暂时不可用" : "已同步"}</span>
            <span>·</span>
            <span>{latestPublishedAt ? "更新至 " + formatDate(latestPublishedAt) : "等待首条核验"}</span>
          </div>
        </header>

        <section className="opp-metrics" aria-label="动态概览">
          <SummaryMetric label="已收录动态" value={metrics.total} />
          <SummaryMetric label="新项目" value={metrics.newPrograms} />
          <SummaryMetric label="30天内截止" value={metrics.upcoming} />
          <SummaryMetric label="奖学金" value={metrics.scholarships} />
        </section>

        <section className="opp-toolbar" aria-label="筛选与排序">
          <div className="opp-toolbar-row">
            <label className="opp-search">
              <Search className="opp-search-icon" size={15} aria-hidden="true" />
              <span className="sr-only">搜索机会动态</span>
              <input
                className="opp-search-input"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="搜索学校、项目或关键词"
              />
              {query && (
                <button className="opp-search-clear" type="button" onClick={() => setQuery("")} aria-label="清除搜索" title="清除搜索">
                  <X size={14} />
                </button>
              )}
            </label>
            <label className="opp-sort">
              <ListFilter size={14} aria-hidden="true" />
              <span className="sr-only">排序方式</span>
              <select
                className="opp-sort-select"
                value={sortMode}
                onChange={(event) => setSortMode(event.target.value as SortMode)}
                aria-label="排序方式"
              >
                <option value="latest">最新发布</option>
                <option value="deadline">截止时间优先</option>
              </select>
              <ChevronDown className="opp-sort-chevron" size={14} aria-hidden="true" />
            </label>
          </div>
          <div className="opp-toolbar-lower">
            <div className="opp-segment" role="tablist" aria-label="机会类型">
              <FilterButton active={!category} onClick={() => setCategory("")}>全部</FilterButton>
              {categories.map((item) => (
                <FilterButton key={item} active={category === item} onClick={() => setCategory(item)}>
                  {categoryMeta(item).label}
                </FilterButton>
              ))}
            </div>
            <div className="opp-toolbar-actions">
              <button
                className={"opp-toggle " + (followingOnly ? "is-active" : "")}
                type="button"
                onClick={() => setFollowingOnly((value) => !value)}
                aria-pressed={followingOnly}
              >
                <Bell size={13} aria-hidden="true" />
                我的学校
              </button>
              <span className="opp-result-count" aria-live="polite">{filtered.length} 条结果</span>
            </div>
          </div>
        </section>

        {isLoading && <OpportunitySkeleton />}

        {isError && (
          <div className="opp-panel" style={{ marginTop: 18 }}>
            <DataUnavailableState reason="机会动态暂时无法加载，请稍后重试。" onRetry={() => state.reload()} />
          </div>
        )}

        {isReady && articles.length === 0 && <EmptyRadarState />}

        {isReady && articles.length > 0 && filtered.length === 0 && (
          <NoResultsState hasFilters={hasFilters} onClear={clearFilters} />
        )}

        {isReady && filtered.length > 0 && (
          <div className="opp-workspace">
            <section className="opp-panel opp-list-panel" aria-labelledby="opportunity-list-title">
              <div className="opp-section-header">
                <div>
                  <p id="opportunity-list-title" className="opp-section-title">动态列表</p>
                  <p className="opp-section-note">按时间和行动优先级整理</p>
                </div>
                <span className="opp-provenance">
                  <ShieldCheck size={14} aria-hidden="true" />
                  来源可追溯
                </span>
              </div>
              <div className="opp-list">
                {filtered.map((item) => (
                  <OpportunityRow
                    key={item.id}
                    item={item}
                    selected={item.id === selectedId}
                    followed={!!item.universityId && following.includes(item.universityId)}
                    onSelect={() => selectOpportunity(item.id)}
                  />
                ))}
              </div>
            </section>

            <div className="opp-detail-column">
              {selectedArticle ? (
                <OpportunityDetail
                  item={selectedArticle}
                  followed={!!selectedArticle.universityId && following.includes(selectedArticle.universityId)}
                  onToggleFollowing={toggleFollowing}
                />
              ) : (
                <SelectionPlaceholder />
              )}
            </div>
          </div>
        )}

        {mobileOpen && selectedArticle && (
          <>
            <button className="opp-sheet-backdrop" type="button" onClick={() => setMobileOpen(false)} aria-label="关闭机会详情" />
            <div className="opp-sheet" role="dialog" aria-modal="true" aria-labelledby={"opportunity-detail-" + selectedArticle.id}>
              <div className="opp-sheet-handle" />
              <OpportunityDetail
                item={selectedArticle}
                followed={!!selectedArticle.universityId && following.includes(selectedArticle.universityId)}
                onToggleFollowing={toggleFollowing}
                onClose={() => setMobileOpen(false)}
                className="opp-sheet-detail"
              />
            </div>
          </>
        )}
      </div>
    </main>
  );
}

function SummaryMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="opp-metric">
      <p className="opp-metric-label">{label}</p>
      <p className="opp-metric-value">{value}</p>
    </div>
  );
}

function FilterButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      className={"opp-segment-item " + (active ? "is-active" : "")}
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function OpportunityRow({
  item,
  selected,
  followed,
  onSelect,
}: {
  item: NewsArticle;
  selected: boolean;
  followed: boolean;
  onSelect: () => void;
}) {
  const meta = categoryMeta(categoryFor(item));
  const Icon = meta.icon;
  const days = daysUntil(item.actionDeadline);
  const school = item.universityNameZh || item.universityName || "院校信息待补充";
  const urgent = days !== null && days >= 0 && days <= 30;

  return (
    <button
      className={"opp-row " + (selected ? "is-selected" : "")}
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      aria-label={"查看" + school + "：" + item.title}
    >
      <span className={TONE_ICON_CLASS[meta.tone]}>
        <Icon size={17} aria-hidden="true" />
      </span>
      <span className="opp-row-content">
        <span className="opp-row-meta">
          <span className={TONE_CHIP_CLASS[meta.tone]}>{meta.label}</span>
          {item.importance === "high" && (
            <span className="opp-chip is-red">
              <CircleAlert size={10} aria-hidden="true" />
              优先查看
            </span>
          )}
          {followed && (
            <span className="opp-chip is-green">
              <Bell size={10} aria-hidden="true" />
              已关注
            </span>
          )}
        </span>
        <span className="opp-row-school">{school}</span>
        <span className="opp-row-title">{item.title}</span>
        <span className="opp-row-summary">{item.whatChanged || item.summary || "这条动态正在补充解释。"}</span>
        <span className={"opp-row-time " + (urgent ? "is-urgent" : "")}>
          <span className="inline-flex items-center gap-1">
            <CalendarDays size={11} aria-hidden="true" />
            {days !== null ? deadlineCopy(item.actionDeadline) : "行动时间待核验"}
          </span>
          <span>·</span>
          <span>{formatDate(item.publishedAt)}</span>
        </span>
      </span>
      <ChevronRight className="opp-row-chevron" size={17} aria-hidden="true" />
    </button>
  );
}

function OpportunityDetail({
  item,
  followed,
  onToggleFollowing,
  onClose,
  className = "",
}: {
  item: NewsArticle;
  followed: boolean;
  onToggleFollowing: (universityId: string) => void;
  onClose?: () => void;
  className?: string;
}) {
  const meta = categoryMeta(categoryFor(item));
  const Icon = meta.icon;
  const school = item.universityNameZh || item.universityName || "院校信息待补充";
  const universityId = item.universityId;
  const audience = item.audience?.filter(Boolean) || [];
  const actionSteps = item.actionSteps?.filter(Boolean) || [];
  const days = daysUntil(item.actionDeadline);
  const urgent = days !== null && days >= 0 && days <= 30;

  return (
    <section className={"opp-detail " + className} aria-labelledby={"opportunity-detail-" + item.id}>
      <div className="opp-detail-top">
        <div className="opp-detail-heading">
          <div className="opp-detail-kicker">
            <span className={TONE_ICON_CLASS[meta.tone]}>
              <Icon size={17} aria-hidden="true" />
            </span>
            <span>{meta.label}</span>
          </div>
          {onClose && (
            <button className="opp-detail-close" type="button" onClick={onClose} aria-label="关闭详情" title="关闭详情">
              <X size={16} />
            </button>
          )}
        </div>
        <p className="opp-detail-school">{school}</p>
        <h2 id={"opportunity-detail-" + item.id} className="opp-detail-title">{item.title}</h2>
        {item.titleEn && <p className="opp-detail-title-en">{item.titleEn}</p>}
        <div className="opp-detail-facts">
          <DetailFact
            icon={CalendarDays}
            label="行动截止"
            value={item.actionDeadline ? deadlineCopy(item.actionDeadline) + " · " + formatDate(item.actionDeadline) : "日期待核验"}
            urgent={urgent}
          />
          <DetailFact
            icon={Users}
            label="适合人群"
            value={audience.length ? audience.join("、") : "适用人群待核验"}
          />
        </div>
      </div>

      <div className="opp-detail-body">
        <DetailSection title="发生了什么" text={item.whatChanged || item.summary || "这条动态正在补充解释。"} />
        <DetailSection title="为什么值得关注" text={item.whyItMatters || "请结合你的申请年份、专业和身份核对是否适用。"} />
        <section className="opp-detail-section">
          <p className="opp-detail-section-title">下一步</p>
          {actionSteps.length > 0 ? (
            <ol className="opp-steps">
              {actionSteps.map((step, index) => (
                <li key={item.id + "-step-" + index} className="opp-step">
                  <span className="opp-step-check">
                    <Check size={11} strokeWidth={2.5} aria-hidden="true" />
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="opp-detail-section-text">打开官方页面，确认资格、截止日期和申请方式。</p>
          )}
        </section>
      </div>

      <footer className="opp-detail-footer">
        <div className="opp-source">
          <ShieldCheck className="opp-source-icon" size={14} aria-hidden="true" />
          <span>
            来源：{item.source || "来源信息待补充"}
            {item.sourceStatus ? " · 来源状态已记录" : " · 请以官方页面为准"}
          </span>
        </div>
        <div className="opp-detail-actions">
          {item.url && (
            <a className="opp-button opp-button-primary" href={item.url} target="_blank" rel="noreferrer">
              <ExternalLink size={14} aria-hidden="true" />
              访问官方页面
            </a>
          )}
          {universityId && (
            <Link className="opp-button opp-button-secondary" href={"/university/" + encodeURIComponent(universityId)}>
              <ArrowUpRight size={14} aria-hidden="true" />
              查看学校
            </Link>
          )}
          {universityId && (
            <button
              className={"opp-button opp-button-quiet " + (followed ? "opp-follow-active" : "")}
              type="button"
              onClick={() => onToggleFollowing(universityId)}
              aria-pressed={followed}
            >
              <Bell size={14} aria-hidden="true" />
              {followed ? "已关注" : "关注学校"}
            </button>
          )}
        </div>
      </footer>
    </section>
  );
}

function DetailFact({ icon: Icon, label, value, urgent = false }: { icon: LucideIcon; label: string; value: string; urgent?: boolean }) {
  return (
    <div className="opp-fact">
      <Icon className={"opp-fact-icon " + (urgent ? "is-urgent" : "")} size={15} aria-hidden="true" />
      <div>
        <p className="opp-fact-label">{label}</p>
        <p className={"opp-fact-value " + (urgent ? "is-urgent" : "")}>{value}</p>
      </div>
    </div>
  );
}

function DetailSection({ title, text }: { title: string; text: string }) {
  return (
    <section className="opp-detail-section">
      <p className="opp-detail-section-title">{title}</p>
      <p className="opp-detail-section-text">{text}</p>
    </section>
  );
}

function SelectionPlaceholder() {
  return (
    <aside className="opp-placeholder">
      <span className="opp-placeholder-icon">
        <Sparkles size={22} aria-hidden="true" />
      </span>
      <h2 className="opp-placeholder-title">选择一条动态</h2>
      <p className="opp-placeholder-text">在左侧选择机会，查看影响、适用人群和下一步行动。</p>
    </aside>
  );
}

function EmptyRadarState() {
  return (
    <section className="opp-empty" role="status">
      <span className="opp-empty-icon">
        <Inbox size={25} aria-hidden="true" />
      </span>
      <p className="opp-empty-kicker">Radar status</p>
      <h2 className="opp-empty-title">目前没有新的已核验机会</h2>
      <p className="opp-empty-text">我们只在来源完成核验后发布动态。现在没有可确认的新记录，不代表学校没有变化。</p>
      <Link className="opp-button opp-button-primary opp-empty-action" href="/guides">
        浏览大学指南
        <ArrowUpRight size={14} aria-hidden="true" />
      </Link>
    </section>
  );
}

function NoResultsState({ hasFilters, onClear }: { hasFilters: boolean; onClear: () => void }) {
  return (
    <section className="opp-no-results" role="status">
      <span className="opp-empty-icon">
        <Search size={23} aria-hidden="true" />
      </span>
      <h2 className="opp-empty-title">没有找到符合条件的机会</h2>
      <p className="opp-empty-text">{hasFilters ? "试试放宽学校、日期或机会类型筛选。" : "目前还没有可以显示的动态。"}</p>
      {hasFilters && (
        <button className="opp-button opp-button-secondary opp-empty-action" type="button" onClick={onClear}>
          清除筛选
          <X size={14} aria-hidden="true" />
        </button>
      )}
    </section>
  );
}

function OpportunitySkeleton() {
  return (
    <div className="opp-skeleton" aria-label="正在加载机会动态" role="status">
      <div className="opp-skeleton-panel">
        <div className="opp-skeleton-line" style={{ width: 90 }} />
        {[0, 1, 2].map((item) => (
          <div className="opp-skeleton-row" key={item}>
            <span className="opp-skeleton-icon" />
            <span style={{ display: "grid", gap: 10 }}>
              <span className="opp-skeleton-line" style={{ width: "34%" }} />
              <span className="opp-skeleton-line" style={{ width: "86%" }} />
              <span className="opp-skeleton-line" style={{ width: "100%" }} />
              <span className="opp-skeleton-line" style={{ width: "52%" }} />
            </span>
          </div>
        ))}
      </div>
      <div className="opp-skeleton-panel">
        <span className="opp-skeleton-icon" />
        <span className="opp-skeleton-line" style={{ width: "38%", marginTop: 24 }} />
        <span className="opp-skeleton-line" style={{ width: "82%", marginTop: 12 }} />
        <span className="opp-skeleton-line" style={{ width: "100%", marginTop: 28 }} />
        <span className="opp-skeleton-line" style={{ width: "100%", marginTop: 10 }} />
      </div>
    </div>
  );
}
