"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { CityAggregate } from "@/lib/types";
import { useMapContext } from "./MapCanvas";

const SOURCE_ID = "pathos-california-city-roads";
const CASING_LAYER_ID = "pathos-california-city-roads-casing";
const LINE_LAYER_ID = "pathos-california-city-roads-line";
const CALTRANS_SERVICE = "https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/All_Roads/FeatureServer/0/query";
const RADIUS_DEGREES = 0.12;
const PAGE_SIZE = 900;

interface CaliforniaRoadLayerProps {
  enabled: boolean;
  cities: CityAggregate[];
}

type RoadFeatureCollection = GeoJSON.FeatureCollection<GeoJSON.LineString | GeoJSON.MultiLineString> & {
  metadata?: Record<string, unknown>;
};

function emptyCollection(): RoadFeatureCollection {
  return { type: "FeatureCollection", features: [], metadata: { source: "Caltrans CHhighway/All_Roads FeatureServer" } };
}

function buildQueryUrl(city: CityAggregate, offset = 0): string {
  const minLon = city.longitude - RADIUS_DEGREES;
  const minLat = city.latitude - RADIUS_DEGREES;
  const maxLon = city.longitude + RADIUS_DEGREES;
  const maxLat = city.latitude + RADIUS_DEGREES;
  const params = new URLSearchParams({
    f: "geojson",
    where: "1=1",
    outFields: "OBJECTID,RouteId,Shape__Length",
    returnGeometry: "true",
    geometry: `${minLon},${minLat},${maxLon},${maxLat}`,
    geometryType: "esriGeometryEnvelope",
    inSR: "4326",
    outSR: "4326",
    spatialRel: "esriSpatialRelIntersects",
    resultOffset: String(offset),
    resultRecordCount: String(PAGE_SIZE),
    returnZ: "false",
    returnM: "false",
  });
  return `${CALTRANS_SERVICE}?${params.toString()}`;
}

async function fetchCityRoads(cities: CityAggregate[]): Promise<RoadFeatureCollection> {
  // Prefer a generated local static file when the Python crawler has succeeded.
  try {
    const local = await fetch("/geography/california-city-roads.geojson", { cache: "force-cache" });
    if (local.ok) return (await local.json()) as RoadFeatureCollection;
  } catch {
    // Fall through to live Caltrans query.
  }

  const output = emptyCollection();
  const seen = new Set<string>();

  for (const city of cities.slice(0, 12)) {
    let offset = 0;
    while (offset <= 3600) {
      const response = await fetch(buildQueryUrl(city, offset));
      if (!response.ok) break;
      const payload = (await response.json()) as RoadFeatureCollection;
      const pageFeatures = payload.features ?? [];
      for (const feature of pageFeatures) {
        const props = (feature.properties ?? {}) as Record<string, unknown>;
        const key = `${city.id}-${props.OBJECTID ?? props.RouteId ?? JSON.stringify(feature.geometry).slice(0, 96)}`;
        if (seen.has(key)) continue;
        seen.add(key);
        output.features.push({
          ...feature,
          properties: {
            ...props,
            cityId: city.id,
            city: city.name,
            stateFips: city.stateFips,
            roadClass: "all_roads",
            source: "Caltrans CHhighway/All_Roads FeatureServer",
          },
        });
      }
      if (pageFeatures.length < PAGE_SIZE) break;
      offset += PAGE_SIZE;
    }
  }

  output.metadata = {
    ...output.metadata,
    stateFips: "06",
    cityCount: cities.length,
    featureCount: output.features.length,
    radiusDegrees: RADIUS_DEGREES,
  };
  return output;
}

/** Live California road overlay for city drill-down mode. */
export function CaliforniaRoadLayer({ enabled, cities }: CaliforniaRoadLayerProps) {
  const mapContext = useMapContext();
  const map = mapContext?.map ?? null;
  const [roads, setRoads] = useState<RoadFeatureCollection | null>(null);
  const loadedKeyRef = useRef<string>("");

  const cityKey = useMemo(() => cities.map((city) => city.id).sort().join("|"), [cities]);

  useEffect(() => {
    if (!enabled || cities.length === 0) {
      setRoads(null);
      loadedKeyRef.current = "";
      return;
    }
    if (loadedKeyRef.current === cityKey && roads) return;

    let cancelled = false;
    loadedKeyRef.current = cityKey;
    fetchCityRoads(cities)
      .then((data) => {
        if (!cancelled) setRoads(data);
      })
      .catch(() => {
        if (!cancelled) setRoads(emptyCollection());
      });

    return () => {
      cancelled = true;
    };
  }, [cities, cityKey, enabled, roads]);

  useEffect(() => {
    if (!map || !mapContext?.mapReady) return;

    const remove = () => {
      try {
        if (map.getLayer(LINE_LAYER_ID)) map.removeLayer(LINE_LAYER_ID);
        if (map.getLayer(CASING_LAYER_ID)) map.removeLayer(CASING_LAYER_ID);
        if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID);
      } catch {
        // Ignore style teardown races.
      }
    };

    remove();
    if (!enabled || !roads || roads.features.length === 0) return remove;

    map.addSource(SOURCE_ID, { type: "geojson", data: roads });
    map.addLayer({
      id: CASING_LAYER_ID,
      type: "line",
      source: SOURCE_ID,
      minzoom: 4,
      paint: {
        "line-color": "rgba(255,250,241,0.9)",
        "line-width": ["interpolate", ["linear"], ["zoom"], 4, 0.7, 7, 1.7, 10, 3.5],
        "line-opacity": 0.82,
      },
    });
    map.addLayer({
      id: LINE_LAYER_ID,
      type: "line",
      source: SOURCE_ID,
      minzoom: 4,
      paint: {
        "line-color": "#c45f36",
        "line-width": ["interpolate", ["linear"], ["zoom"], 4, 0.35, 7, 0.9, 10, 2.2],
        "line-opacity": ["interpolate", ["linear"], ["zoom"], 4, 0.25, 7, 0.55, 10, 0.82],
      },
    });

    return remove;
  }, [enabled, map, mapContext?.mapReady, roads]);

  return null;
}
