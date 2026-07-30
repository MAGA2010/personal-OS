"use client";

// React hooks that wrap the data source. Components observe resource
// state via useResource; the hooks own request lifecycle (cancel /
// timeout / error mapping).
//
// All hooks MUST NOT swallow errors silently. They surface them in
// `state.status === "error"`.

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  DatasetManifest,
  NewsArticle,
  RegionDetail,
  RegionMetricQuery,
  RegionMetricRecord,
  ResourceState,
  SourceReference,
  StatusDictionaryMap,
  UniversityDetail,
  UniversityQuery,
  UniversitySearchResult,
  UniversitySummary,
} from "@/domain/dataset";
import type { PathOSDataSource } from "@/services/pathos-data-source";

interface ResourceHook<T> {
  state: ResourceState<T>;
  reload: () => void;
}

/**
 * Generic `useResource` — exposes { state, reload } and cancels the
 * pending request on unmount.
 */
function useResource<T>(
  deps: unknown[],
  loader: (signal: AbortSignal) => Promise<T>,
  initial: ResourceState<T> = { status: "idle" },
): ResourceHook<T> {
  const [state, setState] = useState<ResourceState<T>>(initial);
  const loaderRef = useRef(loader);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    loaderRef.current = loader;
  }, [loader]);

  const run = useCallback(() => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setState({ status: "loading" });
    loaderRef.current(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ status: "ready", data });
      })
      .catch((err: Error) => {
        if (controller.signal.aborted) return;
        const code = (err as Error & { code?: string }).code;
        setState({ status: "error", message: err.message ?? "Unknown error", code });
      });
  }, []);

  useEffect(() => {
    run();
    const ourController = controllerRef.current;
    return () => {
      // Only abort if our controller is still the active one. Under React
      // 18 strict mode the effect mounts → unmounts → remounts; without
      // this guard the first mount's controller would be aborted by the
      // unmount cleanup, racing the second mount's run() and surfacing as
      // ERR_ABORTED on the wire for every initial load.
      ourController?.abort();
    };
    // The caller-supplied `deps` array is dynamic (each resource hook
    // passes a different signature). ESLint can't statically verify
    // a spread array, so we explicitly include `run` (stable callback,
    // useCallback with []) alongside the spread.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run, ...deps]);

  return { state, reload: run };
}

export function useDatasetManifest(source: PathOSDataSource | null): ResourceHook<DatasetManifest | null> {
  return useResource(
    [source],
    source ? (s) => source.getManifest(s) : async () => null,
  );
}

export function useStatusDictionary(source: PathOSDataSource | null): ResourceHook<StatusDictionaryMap> {
  return useResource(
    [source],
    async (s) => (source ? await source.getStatusDictionary(s) : {}),
    { status: "ready", data: {} },
  );
}

export function useUniversitySummaries(
  source: PathOSDataSource | null,
  query?: UniversityQuery,
  options?: { skip?: boolean },
): ResourceHook<UniversitySummary[]> {
  const queryKey = JSON.stringify(query ?? null);
  const skip = !!options?.skip || !source;
  return useResource(
    [source, queryKey, skip],
    async (s) => {
      if (!source) return [];
      return source.getUniversitySummaries(query, s);
    },
    { status: "ready", data: [] },
  );
}

export function useUniversityDetail(
  source: PathOSDataSource | null,
  universityId: string | null,
): ResourceHook<UniversityDetail | null> {
  return useResource(
    [source, universityId],
    async (s) => {
      if (!source || !universityId) return null;
      return source.getUniversityDetail(universityId, s);
    },
    { status: "idle" },
  );
}

export function useRegionMetrics(
  source: PathOSDataSource | null,
  query: RegionMetricQuery,
): ResourceHook<RegionMetricRecord[]> {
  const queryKey = JSON.stringify(query);
  return useResource(
    [source, queryKey],
    async (s) => (source ? await source.getRegionMetrics(query, s) : []),
    { status: "ready", data: [] },
  );
}

export function useRegionDetail(
  source: PathOSDataSource | null,
  fipsCode: string | null,
): ResourceHook<RegionDetail | null> {
  return useResource(
    [source, fipsCode],
    async (s) => {
      if (!source || !fipsCode) return null;
      return source.getRegionDetail(fipsCode, s);
    },
    { status: "idle" },
  );
}

export function useUniversitySearch(
  source: PathOSDataSource | null,
  query: string,
  options?: { debounceMs?: number; limit?: number },
): ResourceHook<UniversitySearchResult[]> {
  const debounce = options?.debounceMs ?? 250;
  const limit = options?.limit ?? 20;
  const [debounced, setDebounced] = useState(query);

  useEffect(() => {
    const handle = setTimeout(() => setDebounced(query), debounce);
    return () => clearTimeout(handle);
  }, [query, debounce]);

  return useResource(
    [source, debounced.trim(), limit],
    async (s) => {
      const q = debounced.trim();
      if (!source || q.length < 2) return [];
      return source.searchUniversities(q, limit, s);
    },
    { status: "ready", data: [] },
  );
}

export function useNews(
  source: PathOSDataSource | null,
  category?: string,
): ResourceHook<NewsArticle[]> {
  const key = category ?? "";
  return useResource(
    [source, key],
    async (s) => (source ? await source.getNews(key, s) : []),
    { status: "ready", data: [] },
  );
}

export function useSourceReferenceResolver(source: PathOSDataSource | null) {
  return useCallback(
    (src: SourceReference, signal?: AbortSignal) =>
      source ? source.resolveSourceReference(src, signal) : Promise.reject(new Error("数据服务暂不可用")),
    [source],
  );
}
