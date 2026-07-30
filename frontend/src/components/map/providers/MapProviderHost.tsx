// PathOS Stage 7B-A — Map Provider Host
//
// Top-level orchestrator that picks the right adapter based on the
// resolved config and renders it into the provided container. This
// component is the single entry point that owns:
//
//   1. resolving provider id from env
//   2. choosing the right adapter class
//   3. surfacing provider errors via onError (no AK leak)
//   4. providing a fallback banner when the requested provider is
//      blocked (e.g. AK missing)
//
// In Stage 7B-A the host is mounted in a "shadow" mode — it can be
// dropped alongside the existing MapCanvas without disrupting it. A
// future Stage 7B-B refactor will swap MapCanvas for <MapProviderHost>
// once both adapters have full visual parity.

"use client";

import { useEffect, useRef, useState } from "react";
import {
  resolveMapProviderConfig,
  type MapProviderAdapter,
  type MapProviderConfig,
  type MapProviderError,
  type MapProviderId,
  type MapViewState,
  type ThemeMode,
} from "./types";
import { MapLibreProviderAdapter } from "./maplibre/MapLibreProviderAdapter";
import { BaiduMapProviderAdapter } from "./baidu/BaiduMapProviderAdapter";
import { getBaiduLoaderError, getBaiduLoaderState } from "./baidu/load-baidu-map";
import type { StyleSpecification } from "maplibre-gl";

export interface MapProviderHostProps {
  provider: MapProviderId;
  baiduAk: string | null;
  theme: ThemeMode;
  view: MapViewState;
  lightStyle: StyleSpecification;
  darkStyle: StyleSpecification;
  /** Called once when the active adapter has fired onReady. */
  onReady?: () => void;
  /** Called whenever the provider reports an error (AK missing,
   *  Referer invalid, overseas permission, quota, timeout). */
  onError?: (err: MapProviderError) => void;
  /**
   * Called whenever an adapter needs to fall back to MapLibre
   * because the requested provider is blocked. Stage 7B-A calls
   * this when AK is missing.
   */
  onFallback?: (reason: MapProviderError) => void;
  /**
   * Optional render-prop for the host to surface its current
   * state — useful for the dev-only Provider switcher UI.
   */
  renderOverlay?: (state: MapProviderHostState) => JSX.Element | null;
}

export interface MapProviderHostState {
  activeProvider: MapProviderId;
  requestedProvider: MapProviderId;
  fallbackReason: MapProviderError | null;
  error: MapProviderError | null;
}

export function MapProviderHost(props: MapProviderHostProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const adapterRef = useRef<MapProviderAdapter | null>(null);
  const [state, setState] = useState<MapProviderHostState>({
    activeProvider: props.provider,
    requestedProvider: props.provider,
    fallbackReason: null,
    error: null,
  });

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;

    let adapter: MapProviderAdapter;
    let activeProvider: MapProviderId = props.provider;

    if (props.provider === "baidu") {
      if (!props.baiduAk) {
        const reason: MapProviderError = {
          code: "ak-missing",
          message: "百度地图 AK 尚未配置",
          hint: "请在 .env.local 中配置 NEXT_PUBLIC_BAIDU_MAP_AK。",
        };
        // Fall back to MapLibre for actual rendering. The host
        // surfaces the reason via state for the UI banner.
        adapter = new MapLibreProviderAdapter({
          lightStyle: props.lightStyle,
          darkStyle: props.darkStyle,
        });
        activeProvider = "maplibre";
        setState((s) => ({ ...s, activeProvider, requestedProvider: "baidu", fallbackReason: reason }));
        props.onFallback?.(reason);
      } else {
        adapter = new BaiduMapProviderAdapter({ ak: props.baiduAk });
        // If the Baidu loader already errored (e.g. timeout) we
        // honor that — the adapter's onError will surface it.
      }
    } else {
      adapter = new MapLibreProviderAdapter({
        lightStyle: props.lightStyle,
        darkStyle: props.darkStyle,
      });
    }

    adapterRef.current = adapter;

    const dispose = adapter.initialize(container, {
      theme: props.theme,
      view: props.view,
      onReady: () => props.onReady?.(),
      onError: (err) => {
        setState((s) => ({ ...s, error: err }));
        props.onError?.(err);
      },
      onMove: () => undefined,
      onMoveEnd: () => undefined,
      onClick: () => undefined,
    });

    return () => {
      dispose();
      adapterRef.current = null;
    };
    // We intentionally only re-init when the requested provider
    // changes; theme/view updates are forwarded below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.provider, props.baiduAk, props.lightStyle, props.darkStyle]);

  // Forward theme/view updates without re-instantiating.
  useEffect(() => {
    adapterRef.current?.setTheme(props.theme);
  }, [props.theme]);
  // Serialize the view to a primitive key so the effect only fires
  // when center/zoom actually change. We intentionally don't depend
  // on props.view itself because MapViewState is recreated on every
  // parent render.
  const viewKey = `${props.view.center[0]}|${props.view.center[1]}|${props.view.zoom}`;
  useEffect(() => {
    adapterRef.current?.flyTo(props.view, { durationMs: 0 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewKey]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" data-pathos-provider-host={state.activeProvider} />
      {props.renderOverlay?.(state)}
    </div>
  );
}

/**
 * Helper that resolves the full MapProviderConfig from
 * `process.env`. Kept tiny so it can be unit-tested without Next.
 */
export function resolveConfigFromEnv(env: Record<string, string | undefined>): MapProviderConfig {
  return resolveMapProviderConfig({
    provider: env.NEXT_PUBLIC_PATHOS_MAP_PROVIDER,
    baiduAk: env.NEXT_PUBLIC_BAIDU_MAP_AK,
  });
}

/** Used by the dev-only provider switcher UI. */
export function getCurrentLoaderState(): {
  state: ReturnType<typeof getBaiduLoaderState>;
  error: ReturnType<typeof getBaiduLoaderError>;
} {
  return { state: getBaiduLoaderState(), error: getBaiduLoaderError() };
}