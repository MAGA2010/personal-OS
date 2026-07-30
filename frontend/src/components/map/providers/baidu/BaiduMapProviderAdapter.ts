// PathOS Stage 7B-A — Baidu Map Provider Adapter
//
// Adapter stub for the Baidu Map JSAPI GL. In this round the adapter
// is intentionally conservative:
//
//   - It loads the JSAPI via loadBaiduMap() when an AK is present.
//   - When the AK is absent it never throws; it surfaces
//     `ak-missing` via the onError channel and stays inert.
//   - It does not create a `BMapGL.Map` yet — the existing MapCanvas
//     still owns the visual layer. Future refactors can plug the
//     BaiduMapProviderAdapter into MapProviderHost and let it own
//     the full lifecycle.
//
// The adapter exists so the Provider selection infrastructure is in
// place and so the AK / Referer / quota state machine is testable
// without booting a real Baidu instance.

"use client";

import type {
  MapClickEvent,
  MapMoveEvent,
  MapProviderAdapter,
  MapProviderError,
  MapMarkerSpec,
  MapViewState,
  RegionalFillSpec,
  ThemeMode,
} from "../types";
import {
  BaiduLoadError,
  getBaiduLoaderError,
  getBaiduLoaderState,
  loadBaiduMap,
  type BaiduGlobal,
} from "./load-baidu-map";

export class BaiduMapProviderAdapter implements MapProviderAdapter {
  readonly id = "baidu" as const;

  private ak: string | null;
  private theme: ThemeMode = "system";
  private disposed = false;
  private baidu: BaiduGlobal | null = null;
  private listeners: {
    onMove?: (e: MapMoveEvent) => void;
    onMoveEnd?: (e: MapMoveEvent) => void;
    onClick?: (e: MapClickEvent) => void;
    onError?: (e: MapProviderError) => void;
    onReady?: () => void;
  } = {};
  private pendingView: MapViewState | null = null;
  private pendingTheme: ThemeMode | null = null;

  constructor(opts: { ak: string | null }) {
    this.ak = opts.ak;
  }

  initialize(_container: HTMLElement, options: Parameters<MapProviderAdapter["initialize"]>[1]): () => void {
    this.theme = options.theme;
    this.pendingView = options.view;
    this.pendingTheme = options.theme;
    this.listeners = {
      onMove: options.onMove,
      onMoveEnd: options.onMoveEnd,
      onClick: options.onClick,
      onError: options.onError,
      onReady: options.onReady,
    };
    if (!this.ak) {
      const err = getBaiduLoaderError() ?? new BaiduLoadError(
        "ak-missing",
        "百度地图 AK 尚未配置",
        "请在 .env.local 中配置 NEXT_PUBLIC_BAIDU_MAP_AK。",
      );
      this.listeners.onError?.(mapProviderErrorFromBaidu(err));
      return () => this.destroy();
    }
    loadBaiduMap(this.ak).then((g) => {
      if (this.disposed) return;
      this.baidu = g;
      this.listeners.onReady?.();
    }).catch((err: unknown) => {
      if (this.disposed) return;
      this.listeners.onError?.(mapProviderErrorFromUnknown(err));
    });
    return () => this.destroy();
  }

  destroy(): void {
    this.disposed = true;
    this.baidu = null;
  }

  private ensureReady(method: string): boolean {
    if (this.disposed) return false;
    const state = getBaiduLoaderState();
    if (state !== "loaded") {
      this.listeners.onError?.({
        code: "not-implemented",
        message: `百度 Provider 尚未完成初始化（method=${method}）`,
        hint: "当前阶段 BaiduMapProviderAdapter 仅作为接口骨架，实际渲染仍由 MapLibre 处理。",
      });
      return false;
    }
    return true;
  }

  setCenter(_center: [number, number], _zoom?: number): void {
    this.ensureReady("setCenter");
  }
  setZoom(_zoom: number): void {
    this.ensureReady("setZoom");
  }
  flyTo(_view: MapViewState, _opts?: { durationMs?: number }): void {
    this.ensureReady("flyTo");
  }
  fitBounds(_bounds: [[number, number], [number, number]], _padding?: number): void {
    this.ensureReady("fitBounds");
  }
  getCenter(): [number, number] | null {
    return this.pendingView?.center ?? null;
  }
  getZoom(): number | null {
    return this.pendingView?.zoom ?? null;
  }
  setTheme(theme: ThemeMode): void {
    this.theme = theme;
    this.pendingTheme = theme;
  }
  resize(): void {
    /* no-op until BMapGL.Map is wired */
  }
  project(_lngLat: [number, number]): { x: number; y: number } | null {
    return null;
  }
  unproject(_point: { x: number; y: number }): [number, number] | null {
    return null;
  }

  addUniversityMarkers(_markers: MapMarkerSpec[]): void { /* no-op */ }
  updateUniversityMarkers(_markers: MapMarkerSpec[]): void { /* no-op */ }
  removeUniversityMarkers(_ids: string[]): void { /* no-op */ }
  setRegionalFill(_metricId: string, _specs: RegionalFillSpec[]): void { /* no-op */ }
  clearRegionalFill(): void { /* no-op */ }
  setSelectedRegion(_geoId: string | null): void { /* no-op */ }
  setHoveredRegion(_geoId: string | null): void { /* no-op */ }
}

function mapProviderErrorFromBaidu(err: BaiduLoadError): MapProviderError {
  switch (err.code) {
    case "ak-missing":
      return { code: "ak-missing", message: err.message, hint: err.hint };
    case "script-timeout":
      return { code: "script-timeout", message: err.message, hint: err.hint };
    case "script-load-error":
      return {
        code: "referer-invalid",
        message: "当前域名未加入百度地图 Referer 白名单",
        hint: err.hint,
      };
  }
}

function mapProviderErrorFromUnknown(err: unknown): MapProviderError {
  if (err instanceof BaiduLoadError) return mapProviderErrorFromBaidu(err);
  return { code: "service-disabled", message: "百度地图服务暂不可用" };
}