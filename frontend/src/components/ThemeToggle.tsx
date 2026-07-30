"use client";

// Theme toggle. Cycles Light → Dark → System. Sits in the global
// NavBar (one entry, no duplication). Aria-label updates per state
// so screen-reader users always hear the current mode.
//
// Hydration: `useTheme()` returns a deterministic SSR snapshot
// (`mode = "system"`, `resolved = "light"`, isHydrated = false). We
// render the same markup on both server and first client commit, then
// upgrade to the real value after `isHydrated` flips. The button
// reserves its real label in `aria-label` (not visible text) so the
// SSR/CSR first-paint markup is byte-identical.

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "@/lib/theme";

export function ThemeToggle() {
  const { mode, resolved, isHydrated, cycle } = useTheme();

  // Build the label string AFTER hydration. During SSR / first commit,
  // we return the deterministic placeholder so server and client match.
  const label = isHydrated
    ? mode === "system"
      ? `当前跟随系统（${resolved === "dark" ? "深色" : "浅色"}）— 点击切换到浅色`
      : mode === "dark"
        ? "当前深色 — 点击切换到跟随系统"
        : "当前浅色 — 点击切换到深色"
    : "切换主题"; // stable placeholder — matches SSR & first client render

  // Icon is also gated by hydration; on SSR + first paint we render
  // the System icon to match the placeholder mode.
  const Icon = isHydrated
    ? mode === "system"
      ? Monitor
      : mode === "dark"
        ? Moon
        : Sun
    : Monitor;

  return (
    <button
      type="button"
      onClick={cycle}
      aria-label={label}
      title={label}
      data-theme-mode={isHydrated ? mode : "system"}
      data-theme-resolved={isHydrated ? resolved : "light"}
      data-hydrated={isHydrated ? "true" : "false"}
      className="grid h-9 w-9 place-items-center rounded-control border border-border-soft bg-surface-1 text-text-secondary transition hover:border-cobalt/40 hover:text-cobalt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
    >
      <Icon size={15} aria-hidden="true" />
      <span className="sr-only">{label}</span>
    </button>
  );
}

export default ThemeToggle;