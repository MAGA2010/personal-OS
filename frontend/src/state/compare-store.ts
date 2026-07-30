// useCompareStore — single source of truth for the cross-page
// "compare up to 3 universities" selection.
//
// Why a shared store:
//   Both `/map` (MapShell) and `/calculator` keep an independent
//   `selectedIds: string[]` capped at 3. A user who adds a school
//   to compare on the map cannot see it in the calculator's
//   comparison chart, and vice versa. The audit in
//   docs/UI-CONTROL-DUPLICATION-AUDIT.md §4 flagged this and
//   recommended merging into a single store.
//
// Persistence:
//   localStorage key `pathos_compare` (consistent with the existing
//   `pathos_portfolio` and `pathos_student_profile` keys from
//   CLAUDE.md §11). Cross-tab sync is handled by the storage event
//   so two open tabs stay in step.
//
// SSR:
//   Implementation notes:
//   - We deliberately do NOT use useSyncExternalStore here. The map
//     page is pre-rendered as a server component (output: 'export'
//     was originally in use; now dynamic with BFF), and any
//     useSyncExternalStore that returns a non-cached server snapshot
//     triggers React's "should be cached to avoid an infinite loop"
//     warning under dev. The simpler model — useState + module-level
//     bus + useEffect for hydration — is also correct and avoids the
//     hydration-mismatch dance entirely.

"use client";

import { useEffect, useState, useCallback } from "react";

const STORAGE_KEY = "pathos_compare";
const MAX_ITEMS = 3;

type Listener = (ids: string[]) => void;
type Store = { ids: string[] };

let memory: Store = { ids: [] };
let hydrated = false;
const listeners = new Set<Listener>();

function readStorage(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((x): x is string => typeof x === "string").slice(0, MAX_ITEMS);
  } catch {
    return [];
  }
}

function writeStorage(ids: string[]) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    /* quota or private mode — ignore */
  }
}

function notify() {
  listeners.forEach((fn) => fn(memory.ids));
}

function setMemory(next: string[]) {
  memory = { ids: next };
  writeStorage(next);
  notify();
}

export interface CompareApi {
  /** The current compare list (max 3, oldest first). */
  ids: string[];
  /** True after the first localStorage read has happened. */
  hydrated: boolean;
  /** Add an id. Returns false if at cap (3) or already present. */
  add: (id: string) => boolean;
  /** Remove an id. */
  remove: (id: string) => void;
  /** Toggle an id. */
  toggle: (id: string) => void;
  /** Empty the list. */
  clear: () => void;
  /** Returns true if `id` is currently in the compare list. */
  has: (id: string) => boolean;
  /** Hard cap. */
  readonly maxItems: number;
}

export function useCompareStore(): CompareApi {
  // Initial value: the module-level memory snapshot. On the server
  // this is `{ ids: [] }`; on the client, before hydration, also
  // `{ ids: [] }`. After hydration, the useEffect below updates it.
  const [ids, setIds] = useState<string[]>(() => memory.ids);
  const [ready, setReady] = useState(false);

  // Subscribe to bus events. Re-render whenever the store changes,
  // regardless of who triggered the change.
  useEffect(() => {
    const onChange: Listener = (next) => setIds(next);
    listeners.add(onChange);
    return () => {
      listeners.delete(onChange);
    };
  }, []);

  // Hydrate from localStorage on first client mount, then keep
  // in sync across tabs via the `storage` event.
  useEffect(() => {
    if (hydrated) {
      setReady(true);
      return;
    }
    const stored = readStorage();
    memory = { ids: stored };
    setIds(stored);
    hydrated = true;
    setReady(true);
    notify();

    const onStorage = (e: StorageEvent) => {
      if (e.key !== STORAGE_KEY) return;
      memory = { ids: readStorage() };
      notify();
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const add = useCallback((id: string) => {
    if (memory.ids.includes(id)) return false;
    if (memory.ids.length >= MAX_ITEMS) return false;
    setMemory([...memory.ids, id]);
    return true;
  }, []);

  const remove = useCallback((id: string) => {
    if (!memory.ids.includes(id)) return;
    setMemory(memory.ids.filter((x) => x !== id));
  }, []);

  const toggle = useCallback((id: string) => {
    if (memory.ids.includes(id)) {
      setMemory(memory.ids.filter((x) => x !== id));
    } else if (memory.ids.length < MAX_ITEMS) {
      setMemory([...memory.ids, id]);
    }
  }, []);

  const clear = useCallback(() => {
    setMemory([]);
  }, []);

  const has = useCallback((id: string) => memory.ids.includes(id), []);

  return {
    ids,
    hydrated: ready,
    add,
    remove,
    toggle,
    clear,
    has,
    maxItems: MAX_ITEMS,
  };
}
