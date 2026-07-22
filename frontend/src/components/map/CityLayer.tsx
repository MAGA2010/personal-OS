"use client";

import { useCallback, useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { CityAggregate, MetricId } from "@/lib/types";
import { cityMetricColor, getCityMetricDisplay, getCityMetricValue } from "@/lib/city-utils";
import { useMapContext } from "./MapCanvas";

const CITY_BOUNDARIES: any = require("@/data/city-boundaries.json");

const CITY_BUBBLE_SOURCE_ID = "pathos-city-bubbles";
const CITY_BUBBLE_LAYER_ID = "pathos-city-bubbles-circle";
const CITY_BUBBLE_LABEL_LAYER_ID = "pathos-city-bubbles-label";
interface CityLayerProps {
  visibleCities: CityAggregate[];
  activeMetricId: MetricId;
  onCityClick: (cityId: string) => void;
  selectedCityId: string | null;
}

const BOUNDARY_SOURCE_ID = "pathos-ca-boundary";
const BOUNDARY_FILL_ID = "pathos-ca-boundary-fill";
const BOUNDARY_LINE_ID = "pathos-ca-boundary-line";

const MIN_ZOOM = 4.0;
const MAX_ZOOM = 10.0;
const BASE_RADIUS = 18;
const RADIUS_PER_UNI = 8;
const MAX_RADIUS = 40;



function buildBubbleGeoJSON(cities: CityAggregate[], metricId: MetricId) {
  return {
    type: "FeatureCollection" as const,
    features: cities.map((city) => {
      const metricValue = getCityMetricValue(city, metricId);
      return {
        type: "Feature" as const,
        geometry: { type: "Point" as const, coordinates: [city.longitude, city.latitude] as [number, number] },
        properties: {
          id: city.id, name: city.name, nameZh: city.nameZh,
          stateFips: city.stateFips, universityCount: city.universityCount,
          metricValue, metricDisplay: getCityMetricDisplay(city, metricId),
          label: city.nameZh + (city.universityCount > 1 ? " (" + city.universityCount + ")" : "") + " " + getCityMetricDisplay(city, metricId),
          color: cityMetricColor(metricId, metricValue),
          radius: Math.min(MAX_RADIUS, BASE_RADIUS + city.universityCount * RADIUS_PER_UNI),
        },
      };
    }),
  };
}

function buildBoundaryForCities(visibleCities: CityAggregate[]) {
  const cityIds = new Set(visibleCities.map((c) => c.id));
  return {
    type: "FeatureCollection" as const,
    features: CITY_BOUNDARIES.features.filter(function(f: any) { return cityIds.has(f.properties.cityId); }),
  };
}

export function CityLayer({ visibleCities, activeMetricId, onCityClick, selectedCityId }: CityLayerProps) {
  const mapContext = useMapContext();
  const map = mapContext?.map ?? null;
  const prevMetricRef = useRef<MetricId>(activeMetricId);
  const prevCityIdsRef = useRef<string>("");

  const removeLayers = useCallback(() => {
    if (!map) return;
    try {
      [BOUNDARY_LINE_ID, BOUNDARY_FILL_ID, CITY_BUBBLE_LABEL_LAYER_ID, CITY_BUBBLE_LAYER_ID].forEach(id => {
        if (map.getLayer(id)) map.removeLayer(id);
      });
      [BOUNDARY_SOURCE_ID, CITY_BUBBLE_SOURCE_ID].forEach(id => {
        if (map.getSource(id)) map.removeSource(id);
      });
    } catch { }
  }, [map]);

  const addLayers = useCallback(() => {
    if (!map) return;
    removeLayers();
    if (visibleCities.length === 0) return;

    const boundaryData = buildBoundaryForCities(visibleCities);
    if (boundaryData.features.length > 0) {
      map.addSource(BOUNDARY_SOURCE_ID, { type: "geojson", data: boundaryData });
      map.addLayer({ id: BOUNDARY_FILL_ID, type: "fill", source: BOUNDARY_SOURCE_ID, minzoom: 5.5, maxzoom: MAX_ZOOM,
        paint: { "fill-color": "#23766b", "fill-opacity": 0.06, "fill-outline-color": "#23766b" } });
      map.addLayer({ id: BOUNDARY_LINE_ID, type: "line", source: BOUNDARY_SOURCE_ID, minzoom: 5.5, maxzoom: MAX_ZOOM,
        paint: { "line-color": "#23766b", "line-width": 2, "line-opacity": 0.6, "line-dasharray": [3, 2] } });
    }

    const bubbleData = buildBubbleGeoJSON(visibleCities, activeMetricId);
    map.addSource(CITY_BUBBLE_SOURCE_ID, { type: "geojson", data: bubbleData });
    map.addLayer({ id: CITY_BUBBLE_LAYER_ID, type: "circle", source: CITY_BUBBLE_SOURCE_ID, minzoom: MIN_ZOOM, maxzoom: MAX_ZOOM,
      paint: { "circle-radius": ["get", "radius"], "circle-color": ["get", "color"], "circle-opacity": 0.9,
        "circle-stroke-width": ["case", ["==", ["get", "id"], selectedCityId || ""], 4, 3],
        "circle-stroke-color": ["case", ["==", ["get", "id"], selectedCityId || ""], "#152025", "#ffffff"] } });
    map.addLayer({ id: CITY_BUBBLE_LABEL_LAYER_ID, type: "symbol", source: CITY_BUBBLE_SOURCE_ID, minzoom: 5.2, maxzoom: MAX_ZOOM,
      layout: { "text-field": ["get", "label"], "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"], "text-size": 13,
        "text-offset": [0, 0.3], "text-allow-overlap": true },
      paint: { "text-color": "#152025", "text-halo-width": 1.5, "text-halo-color": "rgba(255,255,255,0.85)" } });

    prevCityIdsRef.current = visibleCities.map(c => c.id).join("|");
  }, [activeMetricId, map, removeLayers, selectedCityId, visibleCities]);

  useEffect(() => {
    if (!map || !mapContext?.mapReady) return;
    const metricChanged = prevMetricRef.current !== activeMetricId;
    const cityIds = visibleCities.map(c => c.id).join("|");
    const citiesChanged = prevCityIdsRef.current !== cityIds;
    if (citiesChanged) { addLayers(); }
    else if (metricChanged && visibleCities.length > 0) {
      const source = map.getSource(CITY_BUBBLE_SOURCE_ID) as any;
      if (source?.setData) source.setData(buildBubbleGeoJSON(visibleCities, activeMetricId));
      else addLayers();
    }
    prevMetricRef.current = activeMetricId;
    prevCityIdsRef.current = cityIds;
    return () => removeLayers();
  }, [activeMetricId, addLayers, map, mapContext?.mapReady, removeLayers, visibleCities]);

  useEffect(() => {
    if (!map || !mapContext?.mapReady || visibleCities.length === 0) return;
    const handleClick = (e: any) => {
      const features = map.queryRenderedFeatures(e.point, { layers: [CITY_BUBBLE_LAYER_ID] });
      const cityId = features[0]?.properties?.id;
      if (typeof cityId === "string") onCityClick(cityId);
    };
    map.on("click", CITY_BUBBLE_LAYER_ID, handleClick);
    return () => { map.off("click", CITY_BUBBLE_LAYER_ID, handleClick); };
  }, [map, mapContext?.mapReady, onCityClick, visibleCities.length]);

  return null;
}
