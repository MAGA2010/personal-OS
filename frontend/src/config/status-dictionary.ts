// Status dictionary mapping.
// The data source's `getStatusDictionary()` is the canonical source of
// truth. When the backend is unavailable, fall back to the local
// conservative mapping in `FALLBACK_STATUS_DICTIONARY`.

import type { ProvenanceStatusLabel, StatusDictionaryMap } from "@/domain/dataset";

export const FALLBACK_STATUS_DICTIONARY: StatusDictionaryMap = {
  live_verified_exact: {
    consumerLabel: "来源已实时验证",
    technicalLabel: "live_verified_exact",
    icon: "check",
    tone: "success",
  },
  live_verified_normalized: {
    consumerLabel: "来源已验证并规范化",
    technicalLabel: "live_verified_normalized",
    icon: "check",
    tone: "info",
  },
  live_unavailable: {
    consumerLabel: "实时来源暂不可用",
    technicalLabel: "live_unavailable",
    icon: "alert",
    tone: "warn",
  },
  source_review_not_completed: {
    consumerLabel: "数据补充中",
    technicalLabel: "source_review_not_completed",
    icon: "hourglass",
    tone: "neutral",
  },
  page_changed: {
    consumerLabel: "来源页面已发生变化",
    technicalLabel: "page_changed",
    icon: "alert",
    tone: "warn",
  },
  archived_source: {
    consumerLabel: "使用归档来源",
    technicalLabel: "archived_source",
    icon: "archive",
    tone: "neutral",
  },
};

export function resolveStatusLabel(
  status: string,
  dictionary?: StatusDictionaryMap,
): ProvenanceStatusLabel {
  return (
    (dictionary && dictionary[status]) ||
    FALLBACK_STATUS_DICTIONARY[status] || {
      consumerLabel: "数据补充中",
      technicalLabel: status,
      icon: "hourglass",
      tone: "neutral" as const,
    }
  );
}

export function describePersonStatus(
  status: string,
  dictionary?: StatusDictionaryMap,
): string {
  const def = resolveStatusLabel(status, dictionary);
  return def.consumerLabel;
}
