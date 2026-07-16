"use client";

import { useCallback, useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { CityAggregate, MetricId } from "@/lib/types";
import { cityMetricColor, getCityMetricDisplay, getCityMetricValue } from "@/lib/city-utils";
import { useMapContext } from "./MapCanvas";

const CITY_BUBBLE_SOURCE_ID = "pathos-city-bubbles";
const CITY_BUBBLE_LAYER_ID = "pathos-city-bubbles-circle";
const CITY_BUBBLE_LABEL_LAYER_ID = "pathos-city-bubbles-label";
const CITY_BOUNDARY_SOURCE_ID = "pathos-city-boundary";
const CITY_BOUNDARY_LAYER_ID = "pathos-city-boundary-fill";
const CITY_BOUNDARY_LINE_LAYER_ID = "pathos-city-boundary-line";

const MIN_ZOOM = 4.0;
const MAX_ZOOM = 10.0;
const BASE_RADIUS = 14;
const RADIUS_PER_UNI = 6;
const MAX_RADIUS = 40;

interface CityLayerProps {
  visibleCities: CityAggregate[];
  activeMetricId: MetricId;
  onCityClick: (cityId: string) => void;
  selectedCityId: string | null;
}

function buildBubbleGeoJSON(cities: CityAggregate[], metricId: MetricId) {
  return {
    type: "FeatureCollection" as const,
    features: cities.map((city) => {
      const metricValue = getCityMetricValue(city, metricId);
      return {
        type: "Feature" as const,
        geometry: { type: "Point" as const, coordinates: [city.longitude, city.latitude] as [number, number] },
        properties: {
          id: city.id,
          name: city.name,
          nameZh: city.nameZh,
          stateFips: city.stateFips,
          universityCount: city.universityCount,
          metricValue,
          metricDisplay: getCityMetricDisplay(city, metricId),
          label: city.nameZh + (city.universityCount > 1 ? " (" + city.universityCount + ")" : "") + " " + getCityMetricDisplay(city, metricId),
          color: cityMetricColor(metricId, metricValue),
          radius: Math.min(MAX_RADIUS, BASE_RADIUS + city.universityCount * RADIUS_PER_UNI),
        },
      };
    }),
  };
}

function buildBoundaryGeoJSON(cities: CityAggregate[], metricId: MetricId) {
  const features: any[] = [];
  cities.forEach((city) => {
    const metricValue = getCityMetricValue(city, metricId);
    const color = cityMetricColor(metricId, metricValue);
    const radius = Math.min(MAX_RADIUS, BASE_RADIUS + city.universityCount * RADIUS_PER_UNI);
    const segments = 16;
    const coords: number[][] = [];
    for (let i = 0; i <= segments; i++) {
      const angle = (i / segments) * Math.PI * 2;
      const kmRadius = radius * 0.6;
      const dLat = kmRadius / 111;
      const dLng = kmRadius / (111 * Math.cos((city.latitude * Math.PI) / 180));
      coords.push([city.longitude + dLng * Math.cos(angle), city.latitude + dLat * Math.sin(angle)]);
    }
    features.push({
      type: "Feature" as const,
      geometry: { type: "Polygon" as const, coordinates: [coords] },
      properties: { id: city.id, name: city.name, nameZh: city.nameZh, color: color, metricValue },
    });
  });
  return { type: "FeatureCollection" as const, features };
}

export function CityLayer({ visibleCities, activeMetricId, onCityClick, selectedCityId }: CityLayerProps) {
  const mapContext = useMapContext();
  const map = mapContext?.map ?? null;
  const prevMetricRef = useRef<MetricId>(activeMetricId);
  const prevCityIdsRef = useRef<string>("");
  const prevSelectedRef = useRef<string | null>(null);

  const removeLayers = useCallback(() => {
    if (!map) return;
    try {
      [CITY_BOUNDARY_LINE_LAYER_ID, CITY_BOUNDARY_LAYER_ID, CITY_BUBBLE_LABEL_LAYER_ID, CITY_BUBBLE_LAYER_ID].forEach(id => {
        if (map.getLayer(id)) map.removeLayer(id);
      });
      [CITY_BOUNDARY_SOURCE_ID, CITY_BUBBLE_SOURCE_ID].forEach(id => {
        if (map.getSource(id)) map.removeSource(id);
      });
    } catch { }
  }, [map]);

  const addLayers = useCallback(() => {
    if (!map) return;
    removeLayers();
    if (visibleCities.length === 0) return;

    const boundaryData = buildBoundaryGeoJSON(visibleCities, activeMetricId);
    map.addSource(CITY_BOUNDARY_SOURCE_ID, { type: "geojson", data: boundaryData });
    map.addLayer({
      id: CITY_BOUNDARY_LAYER_ID,
      type: "fill",
      source: CITY_BOUNDARY_SOURCE_ID,
      minzoom: 5.5,
      maxzoom: MAX_ZOOM,
      paint: { "fill-color": ["get", "color"], "fill-opacity": 0.18 },
    });
    map.addLayer({
      id: CITY_BOUNDARY_LINE_LAYER_ID,
      type: "line",
      source: CITY_BOUNDARY_SOURCE_ID,
      minzoom: 5.5,
      maxzoom: MAX_ZOOM,
      paint: { "line-color": ["get", "color"], "line-width": 1.5, "line-opacity": 0.5, "line-dasharray": [2, 2] },
    });

    const bubbleData = buildBubbleGeoJSON(visibleCities, activeMetricId);
    map.addSource(CITY_BUBBLE_SOURCE_ID, { type: "geojson", data: bubbleData });
    map.addLayer({
      id: CITY_BUBBLE_LAYER_ID,
      type: "circle",
      source: CITY_BUBBLE_SOURCE_ID,
      minzoom: MIN_ZOOM,
      maxzoom: MAX_ZOOM,
      paint: {
        "circle-radius": ["get", "radius"],
        "circle-color": ["get", "color"],
        "circle-opacity": 0.82,
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });
    map.addLayer({
      id: CITY_BUBBLE_LABEL_LAYER_ID,
      type: "symbol",
      source: CITY_BUBBLE_SOURCE_ID,
      minzoom: 5.2,
      maxzoom: MAX_ZOOM,
      layout: {
        "text-field": ["get", "label"],
        "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"],
        "text-size": 12,
        "text-offset": [0, 0.3],
        "text-allow-overlap": false,
      },
      paint: { "text-color": "#152025", "text-halo-width": 1.5, "text-halo-color": "rgba(255,255,255,0.85)" },
    });

    prevCityIdsRef.current = visibleCities.map(c => c.id).join("|");
  }, [activeMetricId, map, removeLayers, visibleCities]);

  const updateHighlight = useCallback(() => {
    if (!map || !map.getLayer(CITY_BUBBLE_LAYER_ID)) return;
    if (selectedCityId) {
      map.setPaintProperty(CITY_BUBBLE_LAYER_ID, "circle-stroke-width", ["case", ["==", ["get", "id"], selectedCityId], 4, 2]);
      map.setPaintProperty(CITY_BUBBLE_LAYER_ID, "circle-stroke-color", ["case", ["==", ["get", "id"], selectedCityId], "#152025", "#ffffff"]);
      map.setPaintProperty(CITY_BUBBLE_LAYER_ID, "circle-opacity", ["case", ["==", ["get", "id"], selectedCityId], 0.95, 0.7]);
    } else {
      map.setPaintProperty(CITY_BUBBLE_LAYER_ID, "circle-stroke-width", 2);
      map.setPaintProperty(CITY_BUBBLE_LAYER_ID, "circle-stroke-color", "#ffffff");
      map.setPaintProperty(CITY_BUBBLE_LAYER_ID, "circle-opacity", 0.82);
    }
    prevSelectedRef.current = selectedCityId;
  }, [map, selectedCityId]);

  useEffect(() => {
    if (!map || !mapContext?.mapReady) return;
    const metricChanged = prevMetricRef.current !== activeMetricId;
    const cityIds = visibleCities.map(c => c.id).join("|");
    const citiesChanged = prevCityIdsRef.current !== cityIds;

    if (citiesChanged) {
      addLayers();
    } else if (metricChanged && visibleCities.length > 0) {
      const source = map.getSource(CITY_BUBBLE_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
      if (source?.setData) {
        source.setData(buildBubbleGeoJSON(visibleCities, activeMetricId));
        const bs = map.getSource(CITY_BOUNDARY_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
        if (bs?.setData) bs.setData(buildBoundaryGeoJSON(visibleCities, activeMetricId));
      } else { addLayers(); }
    }
    prevMetricRef.current = activeMetricId;
    prevCityIdsRef.current = cityIds;
    return () => removeLayers();
  }, [activeMetricId, addLayers, map, mapContext?.mapReady, removeLayers, visibleCities]);

  useEffect(() => {
    if (!map || !mapContext?.mapReady) return;
    if (selectedCityId !== prevSelectedRef.current) updateHighlight();
  }, [map, mapContext?.mapReady, selectedCityId, updateHighlight, visibleCities]);

  useEffect(() => {
    if (!map || !mapContext?.mapReady || visibleCities.length === 0) return;
    const handleClick = (e: maplibregl.MapMouseEvent) => {
      const features = map.queryRenderedFeatures(e.point, { layers: [CITY_BUBBLE_LAYER_ID] });
      const cityId = features[0]?.properties?.id;
      if (typeof cityId === "string") onCityClick(cityId);
    };
    const handleEnter = () => { map.getCanvas().style.cursor = "pointer"; };
    const handleLeave = () => { map.getCanvas().style.cursor = ""; };
    map.on("click", CITY_BUBBLE_LAYER_ID, handleClick);
    map.on("mouseenter", CITY_BUBBLE_LAYER_ID, handleEnter);
    map.on("mouseleave", CITY_BUBBLE_LAYER_ID, handleLeave);
    return () => {
      map.off("click", CITY_BUBBLE_LAYER_ID, handleClick);
      map.off("mouseenter", CITY_BUBBLE_LAYER_ID, handleEnter);
      map.off("mouseleave", CITY_BUBBLE_LAYER_ID, handleLeave);
    };
  }, [map, mapContext?.mapReady, onCityClick, visibleCities.length]);

  return null;
}