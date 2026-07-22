# PathOS — Map Module

> **面向中国家庭的留学数据平台 · 交互式地图子模块**
>
> Tech: Next.js 14 · TypeScript · Tailwind · MapLibre GL JS · D3
>
> Location: `D:\pathOS\`

---

## 1. What PathOS Is

PathOS is a study-abroad advisory platform for Mainland Chinese families. This repository is the **map submodule** — an interactive choropleth + POI map for exploring US universities through six data layers.

## 2. Quick Start

```bash
cd D:\pathOS\frontend
npm install
npm run dev
# → http://localhost:3000/map
```

## 3. File Structure

```
D:\pathOS\
├── AGENTS.md                           ← This file
├── README.md                           ← Map module README (Chinese)
├── MVP-Critical-Plan-Review.md         ← Product spec decisions
└── frontend/
    ├── package.json
    ├── tailwind.config.ts
    ├── tsconfig.json
    ├── next.config.mjs
    ├── public/
    │   └── geography/                  ← GeoJSON/TopoJSON boundaries
    └── src/
        ├── app/
        │   ├── layout.tsx              ← Root layout (zh-CN, metadata)
        │   ├── page.tsx                ← Landing page
        │   ├── globals.css             ← Tailwind + custom tokens
        │   └── map/
        │       ├── layout.tsx          ← Map module layout
        │       └── page.tsx            ← /map route → renders MapShell
        │
        ├── lib/
        │   ├── types.ts                ← ALL TypeScript types (583 lines)
        │   └── metrics.ts              ← 6 metric definitions + mock data (270 lines)
        │
        ├── components/
        │   └── map/
        │       ├── MapShell.tsx         ← Top-level orchestrator (711 lines)
        │       ├── MapCanvas.tsx        ← MapLibre GL init + context (403 lines)
        │       ├── MetricTabs.tsx       ← 6-layer metric switcher (110 lines)
        │       ├── MapLegend.tsx        ← Color gradient legend (224 lines)
        │       ├── GranularityBadge.tsx ← State/County/City zoom pill (125 lines)
        │       ├── UniversityMarkers.tsx← POI marker overlay (768 lines)
        │       └── UniversityCard.tsx   ← School detail card (525 lines)
        │
        └── data/                       ← ★ DATA SKELETONS — PLUG REAL DATA HERE ★
            ├── universities.json       ← School POI data (1 example record)
            ├── region-metrics.json     ← Choropleth regional metrics
            └── news.json               ← Sidebar news articles (3 examples)
```

## 4. The Six Metric Layers

| ID | Label | Color | Data Source |
|----|-------|-------|-------------|
| `income` | 收入水平 | Green gradient | Census ACS 5-Year |
| `safety` | 安全系数 | Blue→Red (diverging) | FBI UCR |
| `toefl` | 托福成绩 | Blue gradient | University websites |
| `sat` | SAT分数 | Purple gradient | IPEDS / College Scorecard |
| `admission_rate` | 录取率 | Orange-Red gradient | IPEDS |
| `chinese_population` | 华人水平 | Yellow→Red | Census ACS |

## 5. Data Architecture

### 5.1 How Data Plugs In

The project has a **strict separation**: components are complete, data is empty. You do NOT modify components to add data. You ONLY modify these three files:

```
src/data/
├── universities.json      ← Replace with real school data
├── region-metrics.json    ← Replace with real regional metrics
└── news.json              ← Replace with real news articles
```

Or place Python crawler scripts in a `data-pipeline/` directory at the project root. Components import directly from these JSON files.

### 5.2 universities.json Shape

```json
{
  "_instructions": "...",
  "universities": [
    {
      "id": "harvard",
      "name": "Harvard University",
      "chineseName": "哈佛大学",
      "country": "United States",
      "city": "Cambridge",
      "state": "Massachusetts",
      "stateFips": "25",
      "latitude": 42.3736,
      "longitude": -71.1097,
      "rankingBand": "Global Top 5",
      "rankingTier": "top20",
      "annualCostRmb": 580000,
      "safetyScore": 78,
      "recognitionScore": 98,
      "chineseCommunityRating": "high",
      "admissionRate": 3.4,
      "toeflMin": 100,
      "satMedian": 1520,
      "programs": ["Computer Science", "..."],
      "parentHighlights": ["..."],
      "studentHighlights": ["..."],
      "directFlight": true,
      "postStudyVisa": "OPT / STEM OPT",
      "streetviewPanoId": null,
      "logoUrl": null,
      "campusImages": [],
      "nearby": {
        "subwayStations": 1,
        "chineseRestaurants": 28,
        "asianGroceries": 4,
        "avgRentRmb": 12000
      },
      "verifiedAt": "2026-07-01",
      "sourceCount": 12
    }
  ]
}
```

**Required fields**: id, name, chineseName, country, city, latitude, longitude, rankingBand, rankingTier
**Optional fields**: streetviewPanoId, logoUrl, campusImages, nearby (null or empty array OK)

### 5.3 region-metrics.json Shape

```json
{
  "_instructions": "...",
  "meta": {
    "availableGranularities": ["state", "county", "city"],
    "availableMetrics": [
      {"id": "income", "label": "收入水平"},
      ...
    ]
  },
  "metrics": [
    {
      "fipsCode": "06",
      "granularity": "state",
      "name": "加利福尼亚州",
      "nameEn": "California",
      "metricId": "income",
      "value": 0.9,
      "rawValue": 135000,
      "displayValue": "$135k",
      "year": 2025,
      "source": "ACS 2024 5-Year"
    }
  ]
}
```

`value` is the 0–1 normalized value for choropleth coloring. `rawValue` and `displayValue` are for tooltips. `fipsCode` is the FIPS geographic code (2-digit state, 5-digit county).

### 5.4 news.json Shape

```json
{
  "_instructions": {...},
  "articles": [
    {
      "id": "news-001",
      "title": "2026年H-1B签证新规解读",
      "titleEn": "2026 H-1B Visa Changes",
      "summary": "...",
      "source": "EIC Education",
      "url": "#",
      "publishedAt": "2026-07-08T10:00:00Z",
      "category": "visa"
    }
  ]
}
```

Categories: `admissions`, `visa`, `ranking`, `life`, `career`, `policy`.

## 6. Coding Conventions

### Tailwind Color Tokens

| Token | Hex | Usage |
|-------|-----|-------|
| `ink` | `#152025` | Body text, active states |
| `paper` | `#f6f3ed` | Page background |
| `panel` | `#fffaf1` | Card/panel background |
| `line` | `#d9d1c3` | Borders, dividers |
| `jade` | `#23766b` | Success, positive |
| `persimmon` | `#c45f36` | Warning, highlight |
| `cobalt` | `#315d9f` | Info, link, accent |

### Language Convention

- **Chinese primary**, English secondary: all UI labels use `label` (Chinese) + `labelEn` (English fallback)
- `lang="zh-CN"` on the root `<html>`
- Map labels from tile source (currently English; Chinese tiles TBD)

### Component Patterns

- `"use client"` directive only on components that need browser APIs (state, effects, MapLibre instance)
- Pure/presentational components stay server-compatible (no directive)
- MapLibre map instance lives in `MapCanvas` and is shared via React Context
- Data flows down from `MapShell` (orchestrator) → child components via props
- All components have JSDoc headers describing responsibility and data dependencies

## 7. What NOT to Do

- **Do NOT run port tests** — the system has no real data yet, so the map won't render a choropleth. TypeScript compilation (`npx tsc --noEmit`) is the only verification needed.
- **Do NOT modify component architecture** — components are complete. Data changes happen only in `src/data/*.json` or via `data-pipeline/` scripts.
- **Do NOT change the type definitions** — `types.ts` defines the contract between data and UI. If your data doesn't fit, the data format should change, not the types (consult first).

## 8. Providing Real Data

You have two paths:

### Option A: Fill in the JSON files directly
Replace the contents of `src/data/universities.json`, `src/data/region-metrics.json`, and `src/data/news.json` with real data following the shapes described in Section 5.

### Option B: Python crawler scripts
Create a `data-pipeline/` directory at `D:\pathOS\data-pipeline\` with Python scripts that:
1. Call public APIs (Census ACS, FBI UCR, IPEDS/College Scorecard)
2. Scrape university websites for TOEFL/SAT requirements
3. Transform and normalize the data to match the JSON shapes in Section 5
4. Output directly to `frontend/src/data/*.json`

The crawler scripts should follow this structure:
```
data-pipeline/
├── requirements.txt
├── fetch_census.py        ← Income + Chinese population
├── fetch_crime.py         ← FBI UCR violent crime
├── fetch_ipeds.py         ← Admission rates, SAT, tuition
├── scrape_toefl.py        ← TOEFL requirements
└── normalize.py           ← Value normalization to 0-1
```

Once the data is in place, `npm run dev` and the map will render with real data — no code changes needed.
