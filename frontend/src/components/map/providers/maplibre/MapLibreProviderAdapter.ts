// PathOS Stage 7B-A — MapLibre Provider Adapter
//
// Thin wrapper over `maplibregl.Map` that satisfies MapProviderAdapter.
// In this round the adapter delegates to the existing MapCanvas
// implementation as little as possible — it provides the canonical
// surface so MapProviderHost can plug either adapter in.
//
// The actual visual / data layer logic still lives in MapCanvas.tsx
// (choropleth fills, university markers, tooltip); this adapter is
// a stub-shape that future refactors can flesh out. For Stage 7B-A
// the goal is contract + feature flag, not a full migration.

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
import type { StyleSpecification } from "maplibre-gl";

export interface MapLibreAdapterOptions {
  lightStyle: StyleSpecification;
  darkStyle: StyleSpecification;
}

export class MapLibreProviderAdapter implements MapProviderAdapter {
  readonly id = "maplibre" as const;

  private map: import("maplibre-gl").Map | null = null;
  private theme: ThemeMode = "system";
  private opts: MapLibreAdapterOptions;
  private listeners: {
    onMove?: (e: MapMoveEvent) => void;
    onMoveEnd?: (e: MapMoveEvent) => void;
    onClick?: (e: MapClickEvent) => void;
    onError?: (e: MapProviderError) => void;
    onReady?: () => void;
  } = {};

  constructor(opts: MapLibreAdapterOptions) {
    this.opts = opts;
  }

  initialize(container: HTMLElement, options: Parameters<MapProviderAdapter["initialize"]>[1]): () => void {
    // The adapter is intentionally narrow at this stage — the
    // existing MapCanvas continues to own the visual + data layer
    // lifecycle. This constructor is the contract surface only;
    // it does not actually instantiate maplibre-gl (that would
    // duplicate MapCanvas). Tests can verify the surface area; the
    // full migration lands in Stage 7B-B.
    this.theme = options.theme;
    this.listeners = {
      onMove: options.onMove,
      onMoveEnd: options.onMoveEnd,
      onClick: options.onClick,
      onError: options.onError,
      onReady: options.onReady,
    };
    return () => this.destroy();
  }

  destroy(): void {
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
  }

  setCenter(center: [number, number], zoom?: number): void {
    if (!this.map) return;
    this.map.jumpTo({ center, zoom: zoom ?? this.map.getZoom() });
  }

  setZoom(zoom: number): void {
    if (!this.map) return;
    this.map.setZoom(zoom);
  }

  flyTo(view: MapViewState, opts?: { durationMs?: number }): void {
    if (!this.map) return;
    this.map.flyTo({
      center: view.center,
      zoom: view.zoom,
      bearing: view.bearing,
      pitch: view.pitch,
      duration: opts?.durationMs ?? 600,
    });
  }

  fitBounds(bounds: [[number, number], [number, number]], padding = 32): void {
    if (!this.map) return;
    this.map.fitBounds(bounds, { padding });
  }

  getCenter(): [number, number] | null {
    if (!this.map) return null;
    const c = this.map.getCenter();
    return [c.lng, c.lat];
  }

  getZoom(): number | null {
    return this.map?.getZoom() ?? null;
  }

  setTheme(theme: ThemeMode): void {
    if (!this.map) return;
    if (theme === this.theme) return;
    this.theme = theme;
    this.map.setStyle(theme === "dark" ? this.opts.darkStyle : this.opts.lightStyle);
  }

  resize(): void {
    this.map?.resize();
  }

  project(lngLat: [number, number]): { x: number; y: number } | null {
    if (!this.map) return null;
    const p = this.map.project(lngLat);
    return { x: p.x, y: p.y };
  }

  unproject(point: { x: number; y: number }): [number, number] | null {
    if (!this.map) return null;
    const ll = this.map.unproject([point.x, point.y]);
    return [ll.lng, ll.lat];
  }

  addUniversityMarkers(_markers: MapMarkerSpec[]): void {
    // Implemented by MapCanvas today; the host remains responsible
    // for routing marker data into MapCanvas until the choropleth
    // refactor lands. This stub is the contract surface for the
    // upcoming refactor.
  }

  updateUniversityMarkers(_markers: MapMarkerSpec[]): void {
    /* same note as add */
  }

  removeUniversityMarkers(_ids: string[]): void {
    /* same note as add */
  }

  setRegionalFill(_metricId: string, _specs: RegionalFillSpec[]): void {
    /* same note as add */
  }

  clearRegionalFill(): void {
    /* same note as add */
  }

  setSelectedRegion(_geoId: string | null): void {
    /* same note as add */
  }

  setHoveredRegion(_geoId: string | null): void {
    /* same note as add */
  }
}