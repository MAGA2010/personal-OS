"use client";

// Stage 7A — School picker dialog used by the Calculator's
// "添加更多大学对比" CTA. Keyboard-navigable, search-filtered,
// dedup'd against the currently-selected set, capped at 3 entries
// total. On mobile (< md), it slides up as a full-height sheet.

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { Search, X, Plus } from "lucide-react";
import type { UniversitySummary } from "@/domain/dataset";

export interface SchoolPickerProps {
  open: boolean;
  onClose: () => void;
  /** All candidate summaries (caller filters out already-selected). */
  candidates: ReadonlyArray<UniversitySummary>;
  /** IDs already in the compare set; used for dedup + greyed-out rows. */
  selectedIds: ReadonlyArray<string>;
  /** Hard cap; picker disables Add when count === max. */
  max: number;
  /** Called when the user picks a new school. */
  onPick: (id: string) => void;
  /** Storage key for last search query (optional). */
  storageKey?: string;
}

interface RowProps {
  s: UniversitySummary;
  isSelected: boolean;
  isFocused: boolean;
  disabled: boolean;
  onPick: (id: string) => void;
  onHover: (id: string) => void;
}

function Row({ s, isSelected, isFocused, disabled, onPick, onHover }: RowProps) {
  const cn =
    "flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left transition " +
    (isFocused
      ? "border-cobalt/45 bg-cobalt/8 ring-2 ring-cobalt/25"
      : "border-line/60 bg-white hover:border-cobalt/30 hover:bg-cobalt/5") +
    (disabled ? " opacity-40 cursor-not-allowed" : " cursor-pointer");
  return (
    <button
      type="button"
      className={cn}
      disabled={disabled}
      onClick={() => !disabled && onPick(s.id)}
      onMouseEnter={() => onHover(s.id)}
      data-picker-row-id={s.id}
    >
      <div className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-ink/8 text-[10px] font-semibold text-ink/70">
        {abbr(s)}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[12px] font-semibold text-ink">
          {s.chineseName || s.name || "未提供名称"}
        </p>
        {s.name && s.chineseName !== s.name && (
          <p className="truncate text-[10px] text-ink/55" lang="en">{s.name}</p>
        )}
        <p className="truncate text-[10px] text-ink/45">
          {(s.city ?? "未报告") + (s.state ? " · " + s.state : "")}
        </p>
      </div>
      {isSelected ? (
        <span className="rounded-full border border-jade/40 bg-jade/8 px-1.5 py-0.5 text-[10px] font-medium text-jade">
          已加入
        </span>
      ) : (
        <Plus size={14} className="text-ink/40" aria-hidden="true" />
      )}
    </button>
  );
}

function abbr(s: UniversitySummary): string {
  const raw = (s.chineseName ?? s.name ?? s.id ?? "").trim();
  if (!raw) return "?";
  // For Chinese, take the first 2 chars; for English, take initials.
  const first = raw.charCodeAt(0);
  const isCJK = first >= 0x3400 && first <= 0x9fff;
  if (isCJK) return raw.slice(0, 2);
  const parts = raw.split(/[\s,·.\-()]+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return raw.slice(0, 2).toUpperCase();
}

export function SchoolPicker({
  open,
  onClose,
  candidates,
  selectedIds,
  max,
  onPick,
  storageKey,
}: SchoolPickerProps) {
  const headingId = useId();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const [query, setQuery] = useState("");
  const [focusedIdx, setFocusedIdx] = useState(0);

  // Hydrate last query from storage.
  useEffect(() => {
    if (!open || !storageKey || typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (raw) setQuery(raw);
    } catch { /* ignore */ }
  }, [open, storageKey]);

  // Persist query.
  useEffect(() => {
    if (!open || !storageKey || typeof window === "undefined") return;
    try {
      window.localStorage.setItem(storageKey, query);
    } catch { /* ignore */ }
  }, [query, open, storageKey]);

  // Filtered list — includes dedupe vs selectedIds.
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const out: Array<{ s: UniversitySummary; isSelected: boolean }> = [];
    for (const s of candidates) {
      const isSel = selectedSet.has(s.id);
      if (q) {
        const hay = [
          s.chineseName ?? "",
          s.name ?? "",
          s.nameZh ?? "",
          ...(s.aliases ?? []),
          s.city ?? "",
          s.state ?? "",
        ].join(" ").toLowerCase();
        if (!hay.includes(q)) continue;
      }
      out.push({ s, isSelected: isSel });
    }
    return out;
  }, [candidates, query, selectedSet]);

  // Clamp focused index when the filter narrows.
  useEffect(() => {
    setFocusedIdx((idx) => Math.min(Math.max(0, idx), Math.max(0, filtered.length - 1)));
  }, [filtered.length]);

  // Autofocus + close on Escape.
  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => inputRef.current?.focus(), 30);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      clearTimeout(t);
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  // Reset query when dialog re-opens.
  useEffect(() => {
    if (open) setQuery("");
  }, [open]);

  const handleListKey = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
    if (filtered.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setFocusedIdx((i) => Math.min(filtered.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setFocusedIdx((i) => Math.max(0, i - 1));
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      const row = filtered[focusedIdx];
      if (row && !selectedSet.has(row.s.id) && selectedIds.length < max) {
        onPick(row.s.id);
        onClose();
      }
    } else if (e.key === "Home") {
      e.preventDefault();
      setFocusedIdx(0);
    } else if (e.key === "End") {
      e.preventDefault();
      setFocusedIdx(filtered.length - 1);
    }
  }, [filtered, focusedIdx, onPick, onClose, selectedSet, selectedIds, max]);

  // Scroll focused row into view.
  useEffect(() => {
    const root = listRef.current;
    if (!root) return;
    const el = root.querySelector(`[data-picker-row-id]`);
    // Note: we use a simple selector for the focused row.
    const focused = root.querySelectorAll('[data-picker-row-id]')[focusedIdx] as HTMLElement | undefined;
    focused?.scrollIntoView({ block: "nearest" });
    void el;
  }, [focusedIdx]);

  if (!open) return null;
  const cap = selectedIds.length >= max;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={headingId}
      className="fixed inset-0 z-[80] flex items-end md:items-center justify-center bg-ink/40 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="relative flex h-[92vh] w-full md:h-auto md:max-h-[80vh] md:w-[640px] flex-col overflow-hidden rounded-t-2xl md:rounded-2xl border border-line/60 bg-panel text-ink shadow-2xl">
        {/* Header */}
        <header className="flex shrink-0 items-center gap-3 border-b border-line/50 px-4 py-3">
          <h2 id={headingId} className="flex-1 truncate text-sm font-semibold text-ink">
            选择大学加入对比
          </h2>
          <span className={"shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium " + (cap ? "border border-persimmon/40 bg-persimmon/8 text-persimmon" : "border border-line/60 bg-paper text-ink/55")}>
            {selectedIds.length} / {max}
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭选择器"
            className="grid h-7 w-7 place-items-center rounded text-ink/40 hover:bg-line/30 hover:text-ink"
          >
            <X size={14} />
          </button>
        </header>

        {/* Search */}
        <div className="flex shrink-0 items-center gap-2 border-b border-line/50 px-4 py-2">
          <Search size={14} className="text-ink/40" aria-hidden="true" />
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleListKey}
            placeholder="按名称、城市、州搜索…"
            aria-label="搜索大学"
            className="min-w-0 flex-1 bg-transparent text-[13px] text-ink placeholder:text-ink/35 focus:outline-none"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              aria-label="清空搜索"
              className="grid h-6 w-6 place-items-center rounded text-ink/40 hover:bg-line/30"
            >
              <X size={12} />
            </button>
          )}
        </div>

        {/* List */}
        <div
          ref={listRef}
          role="listbox"
          aria-label="大学候选"
          className="flex-1 overflow-y-auto overscroll-contain p-3"
          onKeyDown={handleListKey}
        >
          {cap && (
            <div className="mb-2 rounded-lg border border-persimmon/30 bg-persimmon/8 p-2.5 text-[11px] text-persimmon">
              已达到 {max} 所上限。请先移除已选项再添加。
            </div>
          )}
          {filtered.length === 0 ? (
            <div className="flex h-32 flex-col items-center justify-center text-center text-[12px] text-ink/45">
              <Search size={20} className="mb-1.5 text-ink/30" aria-hidden="true" />
              <p>未找到匹配的大学</p>
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery("")}
                  className="mt-1.5 text-[11px] text-cobalt hover:underline"
                >
                  清空搜索
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-1.5">
              {filtered.map((row, idx) => (
                <Row
                  key={row.s.id}
                  s={row.s}
                  isSelected={row.isSelected}
                  isFocused={idx === focusedIdx}
                  disabled={cap && !row.isSelected}
                  onPick={onPick}
                  onHover={() => setFocusedIdx(idx)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer hint */}
        <footer className="flex shrink-0 items-center justify-between gap-2 border-t border-line/50 bg-paper/60 px-4 py-2 text-[10px] text-ink/50">
          <span>↑↓ 选择 · Enter 添加 · Esc 关闭</span>
          <span>{filtered.length} 个候选</span>
        </footer>
      </div>
    </div>
  );
}

export default SchoolPicker;