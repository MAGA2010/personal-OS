"use client";
import { useCallback, useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { MetricId } from "@/lib/types";
import { METRIC_DEFINITIONS } from "@/config/metrics.config";
import { useMapContext } from "./MapCanvas";

// City choropleth (gate-bloker repair #GB-P1-7).
//
// The previous version inlined `CA_CITY_GEOJSON` — 15 California city
// polygons masquerading as the national city choropleth layer. We now
// load boundaries from the same `?endpoint=city-boundaries` endpoint as
// `CityLayer.tsx`, so no state-only hardcoded polygon reaches the
// map.
const SRC = "pathos-city-choro";
const FILL = "pathos-city-choro-fill";
const LINE = "pathos-city-choro-line";
const LABEL = "pathos-city-choro-label";
const MINZ = 5.5, MAXZ = 13;
const INTERP: Record<string, (t: number) => string> = {
  greens: (t: number) => { const r = Math.round(247 - t * 155); const g = Math.round(252 - t * 128); const b = Math.round(185 + t * 50); return "rgb(" + r + "," + g + "," + b + ")"; },
  redblue: (t: number) => { const r = Math.round(50 + t * 155); const g = Math.round(136 + t * 53); const b = Math.round(189 - t * 139); return "rgb(" + r + "," + g + "," + b + ")"; },
  tealgrn: (t: number) => { const r = Math.round(232 - t * 140); const g = Math.round(245 - t * 100); const b = Math.round(202 - t * 10); return "rgb(" + r + "," + g + "," + b + ")"; },
  oranges: (t: number) => { const r = Math.round(254 + t * 1); const g = Math.round(230 - t * 70); const b = Math.round(206 - t * 120); return "rgb(" + r + "," + g + "," + b + ")"; },
  orangered: (t: number) => { const r = Math.round(255 - t * 20); const g = Math.round(247 - t * 120); const b = Math.round(188 - t * 100); return "rgb(" + r + "," + g + "," + b + ")"; },
  ylorrd: (t: number) => { const r = Math.round(255 - t * 55); const g = Math.round(255 - t * 145); const b = Math.round(178 - t * 145); return "rgb(" + r + "," + g + "," + b + ")"; },
};
function getColor(metricId: MetricId, props: any): string {
  // Gate-bloker repair #RG-P0-H: the previous version of this
  // function coerced missing values to fake defaults — safety 70,
  // cost 400000, chineseCommunity 0.5 — and used those defaults to
  // colour every city boundary that didn't have real data. That
  // looked like a meaningful choropleth but was actually hiding the
  // absence of facts. Now we render a neutral "no data" grey when
  // the underlying record is missing.
  let v: number | null = null;
  switch (metricId) {
    case "safety": {
      const s = typeof props.safetyScore === "number" && Number.isFinite(props.safetyScore)
        ? props.safetyScore
        : null;
      v = s === null ? null : s / 100;
      break;
    }
    case "cost": {
      const c = typeof props.annualCostRmb === "number" && Number.isFinite(props.annualCostRmb) && props.annualCostRmb > 0
        ? props.annualCostRmb
        : null;
      v = c === null ? null : Math.min(1, c / 800000);
      break;
    }
    case "chinese_population": {
      const cp = typeof props.chineseCommunity === "number" && Number.isFinite(props.chineseCommunity)
        ? props.chineseCommunity
        : null;
      v = cp === null ? null : cp;
      break;
    }
  }
  if (v === null) {
    return "rgba(120, 120, 120, 0.35)"; // neutral "data pending" grey
  }
  const d = METRIC_DEFINITIONS[metricId]; const sc = d?.colorScheme || "greens"; const inv = d?.invertScale || false; const fn = INTERP[sc] || INTERP.greens; return fn(inv ? 1 - v : v);
}

type BoundaryCollection = GeoJSON.FeatureCollection<GeoJSON.Polygon | GeoJSON.MultiPolygon>;

async function loadCityBoundaries(): Promise<BoundaryCollection> {
  try {
    const res = await fetch("/api/pathos/preview?endpoint=city-boundaries");
    if (!res.ok) return { type: "FeatureCollection", features: [] };
    const json = (await res.json()) as BoundaryCollection;
    if (!json || json.type !== "FeatureCollection") {
      return { type: "FeatureCollection", features: [] };
    }
    return json;
  } catch {
    return { type: "FeatureCollection", features: [] };
  }
}

export function CityChoroplethLayer({ activeMetricId, stateFips, enabled, onCityClick }: { activeMetricId: MetricId; stateFips: string | null; enabled: boolean; onCityClick?: (cityId: string, name: string) => void }) {
  const mc = useMapContext(); const map = mc?.map ?? null; const prevMetric = useRef(activeMetricId);
  const boundariesRef = useRef<BoundaryCollection>({ type: "FeatureCollection", features: [] });
  const rm = useCallback(() => { if (!map) return; try { if (map.getLayer(LINE)) map.removeLayer(LINE); if (map.getLayer(LABEL)) map.removeLayer(LABEL); if (map.getLayer(FILL)) map.removeLayer(FILL); if (map.getSource(SRC)) map.removeSource(SRC); } catch {} }, [map]);
  const add = useCallback(() => {
    if (!map || !enabled || !stateFips) { rm(); return; }
    rm();
    const f = boundariesRef.current.features.filter((x) => {
      const cityId = (x.properties as { cityId?: string } | null)?.cityId ?? "";
      return cityId.startsWith(stateFips);
    });
    if (f.length === 0) return;
    const colored = f.map((x) => ({ ...x, properties: { ...x.properties, color: getColor(activeMetricId, x.properties as Record<string, unknown>) } }));
    map.addSource(SRC, { type: "geojson", data: { type: "FeatureCollection", features: colored } as unknown as GeoJSON.FeatureCollection });
    map.addLayer({ id: FILL, type: "fill", source: SRC, minzoom: MINZ, maxzoom: MAXZ, paint: { "fill-color": ["get", "color"], "fill-opacity": 0.65, "fill-outline-color": "rgba(21,32,37,0.2)" } });
    map.addLayer({ id: LINE, type: "line", source: SRC, minzoom: MINZ, maxzoom: MAXZ, paint: { "line-color": "rgba(21,32,37,0.5)", "line-width": 1.5, "line-opacity": 0.7, "line-dasharray": [3, 2] } });
    map.addLayer({ id: LABEL, type: "symbol", source: SRC, minzoom: MINZ, maxzoom: MAXZ, layout: { "text-field": ["get", "name"], "text-size": 11, "text-font": ["Open Sans Regular", "Noto Sans SC Regular"], "text-offset": [0, -0.5], "text-anchor": "center", "text-optional": true }, paint: { "text-color": "#152025", "text-halo-color": "#fffaf1", "text-halo-width": 2, "text-halo-blur": 1 } });
  }, [activeMetricId, enabled, map, rm, stateFips]);
  useEffect(() => {
    let cancelled = false;
    void loadCityBoundaries().then((data) => {
      if (cancelled) return;
      boundariesRef.current = data;
      if (map && mc?.mapReady && enabled && stateFips) add();
    });
    return () => { cancelled = true; };
  }, [add, enabled, map, mc?.mapReady, stateFips]);
  useEffect(() => { if (!map || !mc?.mapReady) return;
    if (enabled && stateFips) { add(); }
    else { rm(); }
  }, [add, enabled, map, mc?.mapReady, rm, stateFips]);
  useEffect(() => { if (!map || !mc?.mapReady || !enabled || !stateFips) return; if (prevMetric.current !== activeMetricId) { add(); prevMetric.current = activeMetricId; } }, [activeMetricId, add, enabled, map, mc?.mapReady, stateFips]);
  useEffect(() => { if (!map || !mc?.mapReady || !enabled || !onCityClick) return;
    const h = (e: any) => { const f2 = map.queryRenderedFeatures(e.point, { layers: [FILL] }); const id = f2[0]?.properties?.cityId; const nm = f2[0]?.properties?.name; if (typeof id === "string") onCityClick(id, nm || id); };
    map.on("click", FILL, h); return () => { map.off("click", FILL, h); };
  }, [enabled, map, mc?.mapReady, onCityClick, stateFips]);
  return null;
}