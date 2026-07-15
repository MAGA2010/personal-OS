"use client";

import { useCallback, useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { CityAggregate, MetricId } from "@/lib/types";
import { cityMetricColor, getCityMetricDisplay, getCityMetricValue } from "@/lib/city-utils";
import { useMapContext } from "./MapCanvas";

const CITY_BUBBLE_SOURCE_ID = "pathos-city-bubbles";
const CITY_BUBBLE_LAYER_ID = "pathos-city-bubbles-circle";
const CITY_BUBBLE_LABEL_LAYER_ID = "pathos-city-bubbles-label";

const MIN_ZOOM = 4.0;
const MAX_ZOOM = 7.5;
const BASE_RADIUS = 12;
const RADIUS_PER_UNI = 8;
const MAX_RADIUS = 44;

interface CityLayerProps {
  /** City aggregates to display, normally filtered to the selected state. */
  visibleCities: CityAggregate[];
  /** Active choropleth metric; city bubbles use the same colour family. */
  activeMetricId: MetricId;
  /** Called when a city bubble is clicked. */
  onCityClick: (cityId: string) => void;
}

function buildGeoJSON(cities: CityAggregate[], metricId: MetricId) {
  return {
    type: "FeatureCollection" as const,
    features: cities.map((city) => {
      const metricValue = getCityMetricValue(city, metricId);
      return {
        type: "Feature" as const,
        geometry: {
          type: "Point" as const,
          coordinates: [city.longitude, city.latitude] as [number, number],
        },
        properties: {
          id: city.id,
          name: city.name,
          nameZh: city.nameZh,
          stateFips: city.stateFips,
          stateAbbr: city.stateAbbr,
          universityCount: city.universityCount,
          metricValue,
          metricDisplay: getCityMetricDisplay(city, metricId),
          label: city.nameZh + " " + getCityMetricDisplay(city, metricId),
          color: cityMetricColor(metricId, metricValue),
          radius: Math.min(MAX_RADIUS, BASE_RADIUS + city.universityCount * RADIUS_PER_UNI),
          avgAnnualCostRmb: city.avgAnnualCostRmb,
          avgSafetyScore: city.avgSafetyScore,
          avgAdmissionRate: city.avgAdmissionRate,
        },
      };
    }),
  };
}

/** MapLibre city bubble overlay used for state -> city drill-down. */
export function CityLayer({ visibleCities, activeMetricId, onCityClick }: CityLayerProps) {
  const mapContext = useMapContext();
  const map = mapContext?.map ?? null;
  const prevMetricRef = useRef<MetricId>(activeMetricId);
  const prevCityIdsRef = useRef<string>("");

  const removeLayers = useCallback(() => {
    if (!map) return;
    try {
      if (map.getLayer(CITY_BUBBLE_LABEL_LAYER_ID)) map.removeLayer(CITY_BUBBLE_LABEL_LAYER_ID);
      if (map.getLayer(CITY_BUBBLE_LAYER_ID)) map.removeLayer(CITY_BUBBLE_LAYER_ID);
      if (map.getSource(CITY_BUBBLE_SOURCE_ID)) map.removeSource(CITY_BUBBLE_SOURCE_ID);
    } catch {
      // Ignore cleanup races during style/map teardown.
    }
  }, [map]);

  const addLayers = useCallback(() => {
    if (!map) return;
    removeLayers();
    if (visibleCities.length === 0) return;

    map.addSource(CITY_BUBBLE_SOURCE_ID, {
      type: "geojson",
      data: buildGeoJSON(visibleCities, activeMetricId),
    });

    map.addLayer({
      id: CITY_BUBBLE_LAYER_ID,
      type: "circle",
      source: CITY_BUBBLE_SOURCE_ID,
      minzoom: MIN_ZOOM,
      maxzoom: MAX_ZOOM,
      paint: {
        "circle-radius": ["get", "radius"],
        "circle-color": ["get", "color"],
        "circle-opacity": 0.78,
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });

    map.addLayer({
      id: CITY_BUBBLE_LABEL_LAYER_ID,
      type: "symbol",
      source: CITY_BUBBLE_SOURCE_ID,
      minzoom: MIN_ZOOM,
      maxzoom: MAX_ZOOM,
      layout: {
        "text-field": ["get", "label"],
        "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"],
        "text-size": 11.5,
        "text-offset": [0, 0.2],
        "text-allow-overlap": true,
      },
      paint: {
        "text-color": "#ffffff",
        "text-halo-width": 1,
        "text-halo-color": "rgba(0,0,0,0.35)",
      },
    });

    prevCityIdsRef.current = visibleCities.map((city) => city.id).join("|");
  }, [activeMetricId, map, removeLayers, visibleCities]);

  useEffect(() => {
    if (!map || !mapContext?.mapReady) return;

    const metricChanged = prevMetricRef.current !== activeMetricId;
    const cityIds = visibleCities.map((city) => city.id).join("|");
    const citiesChanged = prevCityIdsRef.current !== cityIds;

    if (citiesChanged) {
      addLayers();
    } else if (metricChanged && visibleCities.length > 0) {
      const source = map.getSource(CITY_BUBBLE_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
      if (source?.setData) {
        source.setData(buildGeoJSON(visibleCities, activeMetricId));
      } else {
        addLayers();
      }
    }

    prevMetricRef.current = activeMetricId;
    prevCityIdsRef.current = cityIds;

    return () => removeLayers();
  }, [activeMetricId, addLayers, map, mapContext?.mapReady, removeLayers, visibleCities]);

  useEffect(() => {
    if (!map || !mapContext?.mapReady || visibleCities.length === 0) return;

    const handleClick = (event: maplibregl.MapMouseEvent) => {
      const features = map.queryRenderedFeatures(event.point, { layers: [CITY_BUBBLE_LAYER_ID] });
      const cityId = features[0]?.properties?.id;
      if (typeof cityId === "string") onCityClick(cityId);
    };
    const handleMouseEnter = () => {
      map.getCanvas().style.cursor = "pointer";
    };
    const handleMouseLeave = () => {
      map.getCanvas().style.cursor = "";
    };

    map.on("click", CITY_BUBBLE_LAYER_ID, handleClick);
    map.on("mouseenter", CITY_BUBBLE_LAYER_ID, handleMouseEnter);
    map.on("mouseleave", CITY_BUBBLE_LAYER_ID, handleMouseLeave);

    return () => {
      map.off("click", CITY_BUBBLE_LAYER_ID, handleClick);
      map.off("mouseenter", CITY_BUBBLE_LAYER_ID, handleMouseEnter);
      map.off("mouseleave", CITY_BUBBLE_LAYER_ID, handleMouseLeave);
    };
  }, [map, mapContext?.mapReady, onCityClick, visibleCities.length]);

  return null;
}



