// PathOS Stage 7B-A — Baidu Map JSAPI Loader
//
// Single, async, testable, AK-aware loader. Behavior contract:
//   - isBrowser(): returns false in SSR/Node, true in browser
//   - loadBaiduMap({ ak }):
//       * if !ak → reject with BaiduLoadError("ak-missing")
//       * if previously loaded → resolve the same instance promise
//       * if currently loading → return the same in-flight promise
//       * if load times out (default 15s) → reject with "script-timeout"
//       * if global onerror fires → reject with "script-load-error"
//
// Privacy guarantees:
//   - the AK is never echoed in error messages or logged
//   - the loader exposes a `state` field (loading | loaded | errored)
//     for the host UI to render status banners without leaking the AK
//
// The script tag is appended to <head> once per page lifetime. We do
// not register a window callback unless the loader also owns the
// callback so multiple components never collide.

"use client";

export type BaiduLoaderState = "idle" | "loading" | "loaded" | "errored";

export type BaiduLoadErrorCode =
  | "ak-missing"
  | "script-load-error"
  | "script-timeout";

export class BaiduLoadError extends Error {
  readonly code: BaiduLoadErrorCode;
  readonly hint: string | undefined;
  constructor(code: BaiduLoadErrorCode, message: string, hint?: string) {
    super(message);
    this.code = code;
    this.hint = hint;
    this.name = "BaiduLoadError";
  }
}

export interface BaiduLoaderOptions {
  /** Default 15s — short enough that the UI can recover quickly. */
  timeoutMs?: number;
  /**
   * Optional document (defaults to globalThis.document). Tests can
   * pass a JSDOM document; the loader will only touch real globals
   * when isBrowser() returns true.
   */
  document?: Document | null;
  /**
   * Override the JSAPI URL — defaults to the official CDN. Tests
   * can stub to verify retry behavior.
   */
  scriptSrc?: string;
}

const DEFAULT_TIMEOUT_MS = 15_000;
const BAIDU_JSAPI_SRC = "https://api.map.baidu.com/api?v=3.0&type=webgl&ak=";

/**
 * Returns true when running in a browser. SSR returns false so the
 * loader is a no-op on the server.
 */
export function isBrowser(doc?: Document | null): boolean {
  if (doc !== undefined) return !!doc;
  return typeof window !== "undefined" && typeof document !== "undefined";
}

/**
 * Module-level singleton state. The loader is intentionally global so
 * multiple consumers and React StrictMode double-mounts do not race.
 */
let inFlight: Promise<unknown> | null = null;
let lastState: BaiduLoaderState = "idle";
let lastError: BaiduLoadError | null = null;

export function getBaiduLoaderState(): BaiduLoaderState {
  return lastState;
}

export function getBaiduLoaderError(): BaiduLoadError | null {
  return lastError;
}

/** Reset the loader (used by tests). */
export function __resetBaiduLoaderForTests(): void {
  inFlight = null;
  lastState = "idle";
  lastError = null;
}

export interface BaiduGlobal {
  BMapGL: unknown;
  initCallback?: () => void;
}

declare global {
  interface Window {
    __pathosBaiduInit?: () => void;
  }
}

/**
 * Loads the Baidu JSAPI script and resolves once `window.BMapGL` is
 * defined. Rejects with a typed BaiduLoadError on failure.
 *
 * The AK value is appended to the script URL but never stored on the
 * loader instance or echoed in errors — logs/reports stay AK-free.
 */
export function loadBaiduMap(
  ak: string | null | undefined,
  options: BaiduLoaderOptions = {},
): Promise<BaiduGlobal> {
  // Reset cached state on every fresh request — required so retries
  // after a previous failure start clean.
  if (!ak || ak.trim().length === 0) {
    lastError = new BaiduLoadError(
      "ak-missing",
      "百度地图 AK 尚未配置",
      "请在 .env.local 中配置 NEXT_PUBLIC_BAIDU_MAP_AK，并在百度地图开放平台控制台将当前域名加入 Referer 白名单。",
    );
    lastState = "errored";
    return Promise.reject(lastError);
  }
  const doc = options.document ?? (typeof document !== "undefined" ? document : null);
  if (!isBrowser(doc)) {
    return Promise.reject(new BaiduLoadError("script-load-error", "百度地图加载器仅在浏览器环境可用"));
  }

  // Fast path — already loaded.
  if (lastState === "loaded" && (window as Window & { BMapGL?: unknown }).BMapGL) {
    return Promise.resolve({ BMapGL: (window as Window & { BMapGL?: unknown }).BMapGL! });
  }
  // Already in-flight — return the same promise.
  if (inFlight) return inFlight as Promise<BaiduGlobal>;

  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const src = `${options.scriptSrc ?? BAIDU_JSAPI_SRC}${encodeURIComponent(ak)}`;

  lastState = "loading";
  lastError = null;
  inFlight = new Promise<BaiduGlobal>((resolve, reject) => {
    const w = window as Window & { BMapGL?: unknown };
    let settled = false;
    const cleanup = () => {
      w.__pathosBaiduInit = undefined;
    };
    const timeoutId = window.setTimeout(() => {
      if (settled) return;
      settled = true;
      cleanup();
      const err = new BaiduLoadError(
        "script-timeout",
        "百度地图脚本加载超时",
        "请检查网络或将 timeoutMs 调高。如果使用国内 VPN，请确认出口 IP 所在地区能访问百度地图 CDN。",
      );
      lastError = err;
      lastState = "errored";
      inFlight = null;
      reject(err);
    }, timeoutMs);

    w.__pathosBaiduInit = () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeoutId);
      cleanup();
      if (!w.BMapGL) {
        const err = new BaiduLoadError(
          "script-load-error",
          "百度地图 JSAPI 加载失败",
          "请确认 Referer 白名单已包含当前域名 (例如 http://localhost:3002)。",
        );
        lastError = err;
        lastState = "errored";
        inFlight = null;
        reject(err);
        return;
      }
      lastState = "loaded";
      inFlight = null;
      resolve({ BMapGL: w.BMapGL });
    };

    const script = doc!.createElement("script");
    script.src = src;
    script.async = true;
    script.defer = true;
    script.setAttribute("data-pathos-baidu", "1");
    // Baidu loads by checking `window.BMapGL`. We do not rely on
    // script.onload — we poll for the property because Baidu's CDN
    // does not always fire onload for cross-origin script tags.
    script.onerror = () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeoutId);
      cleanup();
      const err = new BaiduLoadError(
        "script-load-error",
        "百度地图脚本加载失败",
        "请检查网络与 Referer 白名单配置。",
      );
      lastError = err;
      lastState = "errored";
      inFlight = null;
      reject(err);
    };
    doc!.head.appendChild(script);

    // Polling fallback for environments where onload never fires.
    const pollStart = Date.now();
    const poll = window.setInterval(() => {
      if (settled) {
        window.clearInterval(poll);
        return;
      }
      if (w.BMapGL) {
        window.clearInterval(poll);
        w.__pathosBaiduInit?.();
        return;
      }
      if (Date.now() - pollStart > timeoutMs) {
        window.clearInterval(poll);
      }
    }, 200);
  });

  return inFlight as Promise<BaiduGlobal>;
}