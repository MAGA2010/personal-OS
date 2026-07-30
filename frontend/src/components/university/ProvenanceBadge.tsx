"use client";

// ProvenanceBadge — small inline label that renders a ProvenanceStatus with
// its dictionary-supplied consumer label (e.g. "数据补充中", "来源已实时验证").
//
// Data path:
//   1. Component receives a `status` (ProvenanceStatus key).
//   2. Looks up the matched entry in a `StatusDictionaryMap`.
//   3. Falls back to the raw status key when no dictionary entry exists
//      (e.g. when the backend is offline and the dictionary fetch failed).
//
// Constraints (encoded as tests / manual review):
//   - The key `source_review_not_completed` must always render "数据补充中"
//     and never "无人物" / "待核实" / fabricated copy.
//   - Status badges are visible to all audiences including free users;
//     quarantined-person records are filtered *upstream* (see quarantine
//     policy in `docs/QUARANTINE-POLICY.md`), not hidden here.
//   - Reads from dictionary but never writes — the dictionary is owned by
//     the backend and surfaced via `useStatusDictionary`.

import type { ProvenanceStatus, StatusDictionaryMap } from "@/domain/dataset";

const FALLBACK_LABEL: Record<ProvenanceStatus, string> = {
  live_verified_exact: "来源已实时验证",
  live_verified_normalized: "来源已验证并规范化",
  live_unavailable: "实时来源暂不可用",
  source_review_not_completed: "数据补充中",
  page_changed: "来源页面已发生变化",
  archived_source: "使用归档来源",
};

const TONE_BG: Record<string, string> = {
  neutral: "bg-ink/8 text-ink/68 border-ink/12",
  info: "bg-cobalt/10 text-cobalt border-cobalt/20",
  warn: "bg-persimmon/10 text-persimmon border-persimmon/20",
  danger: "bg-persimmon/15 text-persimmon border-persimmon/30",
  success: "bg-jade/10 text-jade border-jade/20",
};

export interface ProvenanceBadgeProps {
  status: ProvenanceStatus;
  dictionary?: StatusDictionaryMap;
  /** Optional className for inline placement. */
  className?: string;
  /** When true, renders as a tiny pill — useful in tight list rows. */
  compact?: boolean;
  /** When true, renders icon + label side-by-side (otherwise icon-only). */
  withLabel?: boolean;
}

export function ProvenanceBadge({
  status,
  dictionary,
  className,
  compact = false,
  withLabel = true,
}: ProvenanceBadgeProps) {
  const entry = dictionary?.[status];
  const label = entry?.consumerLabel ?? FALLBACK_LABEL[status];
  const tone = entry?.tone ?? "neutral";
  const palette = TONE_BG[tone] ?? TONE_BG.neutral;

  const padding = compact ? "px-1.5 py-[1px] text-[10px]" : "px-2 py-[2px] text-[11px]";
  const gap = withLabel ? "gap-1" : "gap-0";

  return (
    <span
      role="status"
      aria-label={`${label} (${status})`}
      className={`inline-flex items-center rounded-full border ${padding} ${gap} ${palette} ${className ?? ""}`}
      data-provenance-status={status}
    >
      {/* Icon dot — keeps the badge legible even when the dictionary
          label is empty, and signals verification state at a glance. */}
      <span
        aria-hidden="true"
        className="block h-1.5 w-1.5 shrink-0 rounded-full bg-current opacity-80"
      />
      {withLabel && <span className="font-medium">{label}</span>}
    </span>
  );
}

export default ProvenanceBadge;
