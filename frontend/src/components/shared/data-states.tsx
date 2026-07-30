// Shared empty / error / preview banner primitives.
//
// Why one file for all three:
//   The spec (§十) requires every empty state, error state, and
//   preview-mode banner render the same way across pages. The legacy
//   pages each rolled their own panel with slightly different copy
//   and styling, which meant a user could see "暂无数据" in one place
//   and "数据补充中" in another for the same condition. This module
//   makes the language and visual treatment singular.
//
// Invariants enforced here (from CLAUDE.md §10):
//   - "数据补充中" is the only label rendered for
//     `source_review_not_completed` (handled by ProvenanceBadge).
//   - Backend offline must show a clear reason, never fake data.
//   - Preview-mode banners must NOT claim production-ready.

import type { ReactNode } from "react";
import { AlertTriangle, Hourglass, Inbox, RefreshCw } from "lucide-react";

export type PreviewErrorKind =
  | "unavailable"
  | "not_found"
  | "invalid_contract"
  | "feature_disabled";

export interface PreviewErrorPresentation {
  kind: PreviewErrorKind;
  title: string;
  reason: string;
  retryable: boolean;
}

/** Converts internal machine codes into safe, existing public UI semantics. */
export function getPreviewErrorPresentation(
  code?: string,
): PreviewErrorPresentation {
  if (code === "UNIVERSITY_NOT_FOUND") {
    return {
      kind: "not_found",
      title: "未找到该学校",
      reason: "该学校当前不在预览数据集中。",
      retryable: false,
    };
  }
  if (
    code === "INVALID_RESPONSE" ||
    code === "INVALID_JSON" ||
    code === "BUNDLE_SCHEMA_INVALID" ||
    code === "UNSUPPORTED_CONTRACT_VERSION"
  ) {
    return {
      kind: "invalid_contract",
      title: "后端响应无法解析",
      reason: "数据格式与前端契约不一致，已停止展示。",
      retryable: false,
    };
  }
  if (code === "FEATURE_DISABLED" || code === "AI_CONTEXT_DISABLED") {
    return {
      kind: "feature_disabled",
      title: "功能暂不可用",
      reason: "该功能尚未在当前预览数据中开放。",
      retryable: false,
    };
  }
  return {
    kind: "unavailable",
    title: "后端服务暂不可用",
    reason: "无法读取当前预览数据，请稍后重试。",
    retryable:
      code === "TIMEOUT" ||
      code === "BACKEND_UNAVAILABLE" ||
      code === "BACKEND_OFFLINE" ||
      code === "HTTP_ERROR" ||
      code === undefined,
  };
}

export function PreviewErrorState({
  code,
  onRetry,
  className = "",
}: {
  code?: string;
  onRetry?: () => void;
  className?: string;
}) {
  const presentation = getPreviewErrorPresentation(code);
  return (
    <div
      role="alert"
      data-error-kind={presentation.kind}
      className={`flex flex-col gap-3 rounded-lg border border-persimmon/30 bg-persimmon/5 px-4 py-3 text-sm text-ink/70 ${className}`}
    >
      <div className="flex items-start gap-2">
        <AlertTriangle size={16} className="mt-0.5 text-persimmon" aria-hidden="true" />
        <div className="flex-1">
          <p className="font-medium text-ink">{presentation.title}</p>
          <p className="mt-0.5 text-xs text-ink/55">{presentation.reason}</p>
        </div>
      </div>
      {presentation.retryable && onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="self-start rounded-md border border-line/60 bg-panel px-2.5 py-1 text-xs font-medium text-ink/70 hover:border-cobalt/40 hover:text-cobalt"
        >
          重试
        </button>
      ) : null}
    </div>
  );
}

// ── Loading ──────────────────────────────────────────────────────────────

/** Skeleton while a data resource is in flight. */
export function DataLoadingState({
  message = "加载中…",
  className = "",
}: {
  message?: string;
  className?: string;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex items-center gap-3 rounded-lg border border-line/40 bg-panel/70 px-4 py-3 text-sm text-ink/60 ${className}`}
    >
      <RefreshCw size={14} className="animate-spin text-ink/40" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

// ── Empty ─────────────────────────────────────────────────────────────────

/** Empty state when a resource loaded successfully with zero rows. */
export function DataEmptyState({
  title = "数据补充中",
  description,
  action,
  className = "",
}: {
  title?: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      role="status"
      className={`flex flex-col items-center gap-2 rounded-lg border border-dashed border-line/60 bg-panel/60 px-6 py-8 text-center text-ink/60 ${className}`}
    >
      <Inbox size={22} className="text-ink/30" aria-hidden="true" />
      <p className="text-sm font-medium text-ink/70">{title}</p>
      {description ? <p className="text-xs text-ink/50">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

// ── Unavailable (backend offline / 5xx / 0) ─────────────────────────────

/**
 * Rendered when the BFF is unreachable or returned a 5xx. Crucially,
 * NEVER shown with sample/fake data alongside it — the panel is the
 * only thing the user sees.
 */
export function DataUnavailableState({
  reason,
  onRetry,
  className = "",
}: {
  /** Short human-readable reason, e.g. "后端服务暂不可用". */
  reason?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={`flex flex-col gap-3 rounded-lg border border-persimmon/30 bg-persimmon/5 px-4 py-3 text-sm text-ink/70 ${className}`}
    >
      <div className="flex items-start gap-2">
        <AlertTriangle size={16} className="mt-0.5 text-persimmon" aria-hidden="true" />
        <div className="flex-1">
          <p className="font-medium text-ink">数据补充中</p>
          <p className="mt-0.5 text-xs text-ink/55">
            {reason ?? "后端服务暂不可用，正在准备数据。"}
          </p>
        </div>
      </div>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="self-start rounded-md border border-line/60 bg-panel px-2.5 py-1 text-xs font-medium text-ink/70 hover:border-cobalt/40 hover:text-cobalt"
        >
          重试
        </button>
      ) : null}
    </div>
  );
}

// ── Preview warning ──────────────────────────────────────────────────────

/**
 * Banner shown on any page whose underlying data is `previewOnly: true`.
 * The wording is deliberately neutral ("数据预览模式") so we never
 * mislead the user into thinking the values are production-verified.
 */
export function PreviewWarningBanner({
  className = "",
  detail,
}: {
  className?: string;
  detail?: ReactNode;
}) {
  return (
    <div
      role="note"
      aria-label="数据预览模式"
      className={`flex items-center gap-2 rounded-md border border-cobalt/25 bg-cobalt/5 px-3 py-1.5 text-xs text-ink/70 ${className}`}
    >
      <Hourglass size={13} className="text-cobalt" aria-hidden="true" />
      <span className="font-medium">数据预览模式</span>
      <span className="text-ink/45">·</span>
      <span className="text-ink/55">
        {detail ?? "数据由后端持续补充中,所列数字仅供结构参考。"}
      </span>
    </div>
  );
}

// ── Validation error (parse failure from the data source) ───────────────

/** Rendered when the BFF returned 200 but the payload failed schema. */
export function DataValidationError({
  issues,
  onRetry,
  className = "",
}: {
  issues?: readonly { path: string; message: string }[];
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={`flex flex-col gap-2 rounded-lg border border-persimmon/30 bg-persimmon/5 px-4 py-3 text-sm text-ink/70 ${className}`}
    >
      <div className="flex items-start gap-2">
        <AlertTriangle size={16} className="mt-0.5 text-persimmon" aria-hidden="true" />
        <div className="flex-1">
          <p className="font-medium text-ink">后端响应无法解析</p>
          <p className="mt-0.5 text-xs text-ink/55">
            数据格式与前端契约不一致,已上报给后端工程师。
          </p>
          {issues && issues.length > 0 ? (
            <ul className="mt-1 list-disc pl-4 text-[11px] text-ink/45">
              {issues.slice(0, 4).map((issue, idx) => (
                <li key={`${issue.path}-${idx}`}>
                  <code className="font-mono">{issue.path || "<root>"}</code>: {issue.message}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="self-start rounded-md border border-line/60 bg-panel px-2.5 py-1 text-xs font-medium text-ink/70 hover:border-cobalt/40 hover:text-cobalt"
        >
          重试
        </button>
      ) : null}
    </div>
  );
}
