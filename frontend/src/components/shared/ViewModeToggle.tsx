"use client";

// ViewModeToggle — parent vs student mode toggle.
//
// Constraint: this is a *UI hint* only. It does not change which data
// fields appear or what the backend serves — both audiences can see the
// same canonical record. The toggle changes:
//   1. Which Profile sections are open by default (parents see Cost +
//      Ranking first; students see Programs + Location first).
//   2. Which "highlights" card sections on the map marker card are
//      emphasized.
//
// Storage: URL search param `mode=parent|student`. Persisted across
// reloads so users see the same view they left.

import { useCallback } from "react";
import type { UrlBridgeState } from "@/hooks/use-view-state-bridge";
import { Baby, Users } from "lucide-react";

export interface ViewModeToggleProps {
  mode: UrlBridgeState["viewMode"];
  onChange: (mode: UrlBridgeState["viewMode"]) => void;
}

export function ViewModeToggle({ mode, onChange }: ViewModeToggleProps) {
  const select = useCallback(
    (next: UrlBridgeState["viewMode"]) => () => {
      if (next !== mode) onChange(next);
    },
    [mode, onChange],
  );

  return (
    <div
      role="radiogroup"
      aria-label="查看视角"
      className="inline-flex items-center rounded-full border border-line bg-white/85 p-0.5 shadow-xs backdrop-blur"
    >
      <button
        type="button"
        role="radio"
        aria-checked={mode === "parent"}
        onClick={select("parent")}
        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors ${
          mode === "parent" ? "bg-cobalt text-white" : "text-ink/60 hover:text-ink"
        }`}
      >
        <Users size={11} aria-hidden="true" />
        <span>家长视角</span>
      </button>
      <button
        type="button"
        role="radio"
        aria-checked={mode === "student"}
        onClick={select("student")}
        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors ${
          mode === "student" ? "bg-jade text-white" : "text-ink/60 hover:text-ink"
        }`}
      >
        <Baby size={11} aria-hidden="true" />
        <span>学生视角</span>
      </button>
    </div>
  );
}

export default ViewModeToggle;
