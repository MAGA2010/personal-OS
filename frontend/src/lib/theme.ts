"use client";

// PathOS theme controller.
//
// Three modes — Light / Dark / System — persisted to localStorage,
// applied as a `dark` class on <html>, and synchronised with
// `prefers-color-scheme` when in System mode.
//
// No-flash strategy: an inline script in `app/layout.tsx` reads
// localStorage BEFORE React mounts, so the correct theme class is
// already on <html> when the first paint happens. This avoids the
// white-flash that a normal React-only approach would produce on a
// dark-mode reload.
//
// Hydration strategy: `useTheme()` returns a stable SSR snapshot
// (`mode = "system"`, `resolved = "light"`, stable label & icon) and
// only resolves to the real client value after the first commit, via
// `useSyncExternalStore` with an explicit `getServerSnapshot`. This
// guarantees server-rendered markup matches the first client commit
// for every route, so React 18 hydration reports zero warnings.
//
// The toggle button (`ThemeToggle`) additionally guards its dynamic
// label & icon with `mounted` so even if the external store hasn't
// notified yet, the rendered markup matches SSR.

import { useCallback, useEffect, useSyncExternalStore } from "react";

export type ThemeMode = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "pathos:theme";

/**
 * The values rendered on the SERVER and the FIRST client commit must
 * be identical. We deliberately use `"system"` + `"light"` here so the
 * toggle button markup is deterministic across all OS / browser combos.
 */
const SSR_SNAPSHOT: ThemeSnapshot = {
  mode: "system",
  resolved: "light",
  isHydrated: false,
};

export type ThemeSnapshot = {
  mode: ThemeMode;
  resolved: ResolvedTheme;
  isHydrated: boolean;
};

/** Resolve the system preference; safe to call on the server. */
function systemPrefersDark(): ResolvedTheme {
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** Apply the resolved theme to <html>. */
function applyTheme(resolved: ResolvedTheme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.dataset.theme = resolved;
  root.style.colorScheme = resolved;
}

/** Read persisted mode with safe fallback. */
function readStoredMode(): ThemeMode {
  if (typeof window === "undefined") return "system";
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === "light" || raw === "dark" || raw === "system") return raw;
    // Anything else — corrupted value, foreign key, JSON blob —
    // gracefully reset to "system" rather than throw.
  } catch {
    /* ignore (e.g. private mode localStorage access throws) */
  }
  return "system";
}

function persist(mode: ThemeMode) {
  try {
    if (mode === "system") {
      // Don't keep an explicit preference; let the OS decide.
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, mode);
    }
  } catch {
    /* ignore */
  }
}

// ---------------------------------------------------------------------------
// External store — useSyncExternalStore.
// ---------------------------------------------------------------------------
//
// Subscribers are React components; the store fires `notify()` after any
// mutation. We intentionally keep the store tiny so the SSR snapshot
// (returned by `getServerSnapshot`) is byte-identical to the first
// client commit.

let currentSnapshot: ThemeSnapshot = SSR_SNAPSHOT;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

function setSnapshot(next: ThemeSnapshot) {
  if (
    next.mode === currentSnapshot.mode &&
    next.resolved === currentSnapshot.resolved &&
    next.isHydrated === currentSnapshot.isHydrated
  ) {
    return;
  }
  currentSnapshot = next;
  emit();
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

/** `getServerSnapshot` is what React uses during SSR / first commit. */
function getServerSnapshot(): ThemeSnapshot {
  return SSR_SNAPSHOT;
}

/** `getSnapshot` runs on the client; lazily resolves to real value. */
function getSnapshot(): ThemeSnapshot {
  return currentSnapshot;
}

// One-shot boot — fires once on the client, right after hydration,
// to populate the store with the real localStorage + OS preference.
let booted = false;
function bootClient() {
  if (booted || typeof window === "undefined") return;
  booted = true;
  const mode = readStoredMode();
  const resolved: ResolvedTheme = mode === "system" ? systemPrefersDark() : mode;
  applyTheme(resolved);
  setSnapshot({ mode, resolved, isHydrated: true });
  // OS preference changes (only meaningful while in System mode).
  if (window.matchMedia) {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (readStoredMode() !== "system") return;
      const next: ResolvedTheme = mq.matches ? "dark" : "light";
      applyTheme(next);
      setSnapshot({ mode: "system", resolved: next, isHydrated: true });
    };
    mq.addEventListener("change", onChange);
  }
}

// ---------------------------------------------------------------------------
// Public hook.
// ---------------------------------------------------------------------------

export function useTheme() {
  // `useSyncExternalStore` guarantees no tearing and a stable SSR markup.
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  // Schedule the boot exactly once on the client.
  useEffect(() => {
    bootClient();
  }, []);

  const setMode = useCallback((mode: ThemeMode) => {
    persist(mode);
    const resolved: ResolvedTheme = mode === "system" ? systemPrefersDark() : mode;
    applyTheme(resolved);
    setSnapshot({ mode, resolved, isHydrated: true });
  }, []);

  const cycle = useCallback(() => {
    setMode(
      currentSnapshot.mode === "light"
        ? "dark"
        : currentSnapshot.mode === "dark"
          ? "system"
          : "light",
    );
  }, [setMode]);

  return {
    mode: snapshot.mode,
    resolved: snapshot.resolved,
    isHydrated: snapshot.isHydrated,
    setMode,
    cycle,
  };
}

/**
 * Inline script string to embed in <head> so the theme is applied
 * before React mounts and the first paint is already correct.
 * Keep this function tiny — it runs on every page load.
 */
export const THEME_INIT_SCRIPT = `
(function () {
  try {
    var k = "pathos:theme";
    var raw = window.localStorage.getItem(k);
    var mode = (raw === "light" || raw === "dark") ? raw : "system";
    var resolved = mode;
    if (mode === "system") {
      resolved = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    var root = document.documentElement;
    root.classList.toggle("dark", resolved === "dark");
    root.dataset.theme = resolved;
    root.style.colorScheme = resolved;
  } catch (_) { /* private mode / disabled storage */ }
})();
`.trim();