"""Fetch California city road GeoJSON from Caltrans All_Roads.

This fetches road geometry around California university cities instead of the
full statewide network, keeping the frontend payload usable.
Source: Caltrans CHhighway/All_Roads FeatureServer.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNIVERSITIES = ROOT / "frontend" / "src" / "data" / "universities.json"
OUT = ROOT / "frontend" / "public" / "geography" / "california-city-roads.geojson"
SERVICE = "https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/All_Roads/FeatureServer/0"
RADIUS = 0.12
PAGE_SIZE = 2000


def load_ca_cities() -> list[dict]:
    data = json.loads(UNIVERSITIES.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict]] = {}
    for uni in data["universities"]:
        if str(uni.get("stateFips")) != "06":
            continue
        city = uni.get("city") or "Unknown"
        grouped.setdefault(city, []).append(uni)

    cities = []
    for city, items in sorted(grouped.items()):
        lat = sum(float(i["latitude"]) for i in items) / len(items)
        lon = sum(float(i["longitude"]) for i in items) / len(items)
        slug = city.lower().replace(" ", "-").replace(".", "")
        cities.append({"city": city, "cityId": f"06-{slug}", "latitude": lat, "longitude": lon, "universities": len(items)})
    return cities


def query_city(city: dict, offset: int = 0) -> dict:
    lon = city["longitude"]
    lat = city["latitude"]
    envelope = f"{lon-RADIUS},{lat-RADIUS},{lon+RADIUS},{lat+RADIUS}"
    params = {
        "f": "geojson",
        "where": "1=1",
        "outFields": "OBJECTID,RouteId,Shape__Length",
        "returnGeometry": "true",
        "geometry": envelope,
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "outSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "resultOffset": str(offset),
        "resultRecordCount": str(PAGE_SIZE),
        "returnZ": "false",
        "returnM": "false",
    }
    url = f"{SERVICE}/query?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "PathOS-map-data/0.1"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cities = load_ca_cities()
    features = []
    seen = set()

    for city in cities:
        print(f"Fetching Caltrans roads around {city['city']}...")
        offset = 0
        while True:
            payload = query_city(city, offset)
            page_features = payload.get("features", [])
            for feature in page_features:
                props = feature.setdefault("properties", {})
                oid = props.get("OBJECTID") or props.get("RouteId")
                geom_key = json.dumps(feature.get("geometry"), sort_keys=True)[:160]
                key = (city["cityId"], oid, geom_key)
                if key in seen:
                    continue
                seen.add(key)
                props["roadClass"] = "all_roads"
                props["roadClassLabel"] = "All Public Roads"
                props["city"] = city["city"]
                props["cityId"] = city["cityId"]
                props["stateFips"] = "06"
                props["source"] = "Caltrans CHhighway/All_Roads FeatureServer"
                features.append(feature)
            if len(page_features) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
            time.sleep(0.15)
        time.sleep(0.15)

    out = {
        "type": "FeatureCollection",
        "metadata": {
            "name": "California university-city roads",
            "stateFips": "06",
            "generatedFrom": "Caltrans CHhighway/All_Roads FeatureServer",
            "note": "Roads are queried around California cities represented in universities.json.",
            "radiusDegrees": RADIUS,
            "cities": cities,
            "featureCount": len(features),
        },
        "features": features,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(features)} road features to {OUT}")


if __name__ == "__main__":
    main()
