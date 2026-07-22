import type { CityAggregate, ChineseCommunityLevel, MetricId, RankingTier, UniversityPOI } from "@/lib/types";
import universityData from "@/data/universities.json";

export const STATE_CENTERS: Record<string, [number, number]> = {
  "01": [-86.9023, 32.3542], "02": [-153.4937, 64.2008], "04": [-111.6704, 34.2744],
  "05": [-92.3731, 34.7465], "06": [-119.6816, 36.1162], "08": [-105.3501, 38.9972],
  "09": [-72.7553, 41.5978], "10": [-75.5071, 39.3185], "11": [-77.0369, 38.9072],
  "12": [-81.5158, 27.6648], "13": [-83.6431, 32.1656], "15": [-156.332, 20.7967],
  "16": [-114.742, 44.0682], "17": [-89.3985, 40.0837], "18": [-86.1349, 39.7684],
  "19": [-93.0977, 41.878], "20": [-98.4842, 38.5266], "21": [-85.6021, 37.8393],
  "22": [-91.9623, 30.9843], "23": [-69.4455, 45.2538], "24": [-76.6413, 39.0458],
  "25": [-71.8628, 42.1497], "26": [-84.5361, 43.3266], "27": [-93.9002, 45.6945],
  "28": [-89.6787, 32.7416], "29": [-92.2886, 38.5733], "30": [-109.5337, 46.8797],
  "31": [-99.9018, 41.4925], "32": [-116.4194, 38.6369], "33": [-71.5724, 43.1939],
  "34": [-74.4057, 39.8339], "35": [-105.8701, 34.5199], "36": [-74.9484, 42.1657],
  "37": [-79.0193, 35.6301], "38": [-100.437, 47.5515], "39": [-82.7649, 40.4173],
  "40": [-97.0929, 35.0078], "41": [-122.0709, 43.9336], "42": [-77.1945, 40.5904],
  "44": [-71.4774, 41.6803], "45": [-80.8364, 33.8361], "46": [-99.4382, 44.2998],
  "47": [-86.6302, 35.7478], "48": [-99.9018, 31.0544], "49": [-111.891, 40.6674],
  "50": [-72.5778, 44.0682], "51": [-78.1698, 37.7693], "53": [-120.4472, 47.3826],
  "54": [-80.4549, 38.5976], "55": [-89.6164, 44.6243], "56": [-107.2903, 42.7559],
};

const STATE_META: Record<string, { abbr: string; nameEn: string; nameZh: string }> = {
  "01": { abbr: "AL", nameEn: "Alabama", nameZh: "阿拉巴马州" },
  "02": { abbr: "AK", nameEn: "Alaska", nameZh: "阿拉斯加州" },
  "04": { abbr: "AZ", nameEn: "Arizona", nameZh: "亚利桑那州" },
  "05": { abbr: "AR", nameEn: "Arkansas", nameZh: "阿肯色州" },
  "06": { abbr: "CA", nameEn: "California", nameZh: "加利福尼亚州" },
  "08": { abbr: "CO", nameEn: "Colorado", nameZh: "科罗拉多州" },
  "09": { abbr: "CT", nameEn: "Connecticut", nameZh: "康涅狄格州" },
  "10": { abbr: "DE", nameEn: "Delaware", nameZh: "特拉华州" },
  "11": { abbr: "DC", nameEn: "District of Columbia", nameZh: "华盛顿特区" },
  "12": { abbr: "FL", nameEn: "Florida", nameZh: "佛罗里达州" },
  "13": { abbr: "GA", nameEn: "Georgia", nameZh: "佐治亚州" },
  "15": { abbr: "HI", nameEn: "Hawaii", nameZh: "夏威夷州" },
  "16": { abbr: "ID", nameEn: "Idaho", nameZh: "爱达荷州" },
  "17": { abbr: "IL", nameEn: "Illinois", nameZh: "伊利诺伊州" },
  "18": { abbr: "IN", nameEn: "Indiana", nameZh: "印第安纳州" },
  "19": { abbr: "IA", nameEn: "Iowa", nameZh: "艾奥瓦州" },
  "20": { abbr: "KS", nameEn: "Kansas", nameZh: "堪萨斯州" },
  "21": { abbr: "KY", nameEn: "Kentucky", nameZh: "肯塔基州" },
  "22": { abbr: "LA", nameEn: "Louisiana", nameZh: "路易斯安那州" },
  "23": { abbr: "ME", nameEn: "Maine", nameZh: "缅因州" },
  "24": { abbr: "MD", nameEn: "Maryland", nameZh: "马里兰州" },
  "25": { abbr: "MA", nameEn: "Massachusetts", nameZh: "马萨诸塞州" },
  "26": { abbr: "MI", nameEn: "Michigan", nameZh: "密歇根州" },
  "27": { abbr: "MN", nameEn: "Minnesota", nameZh: "明尼苏达州" },
  "28": { abbr: "MS", nameEn: "Mississippi", nameZh: "密西西比州" },
  "29": { abbr: "MO", nameEn: "Missouri", nameZh: "密苏里州" },
  "30": { abbr: "MT", nameEn: "Montana", nameZh: "蒙大拿州" },
  "31": { abbr: "NE", nameEn: "Nebraska", nameZh: "内布拉斯加州" },
  "32": { abbr: "NV", nameEn: "Nevada", nameZh: "内华达州" },
  "33": { abbr: "NH", nameEn: "New Hampshire", nameZh: "新罕布什尔州" },
  "34": { abbr: "NJ", nameEn: "New Jersey", nameZh: "新泽西州" },
  "35": { abbr: "NM", nameEn: "New Mexico", nameZh: "新墨西哥州" },
  "36": { abbr: "NY", nameEn: "New York", nameZh: "纽约州" },
  "37": { abbr: "NC", nameEn: "North Carolina", nameZh: "北卡罗来纳州" },
  "38": { abbr: "ND", nameEn: "North Dakota", nameZh: "北达科他州" },
  "39": { abbr: "OH", nameEn: "Ohio", nameZh: "俄亥俄州" },
  "40": { abbr: "OK", nameEn: "Oklahoma", nameZh: "俄克拉荷马州" },
  "41": { abbr: "OR", nameEn: "Oregon", nameZh: "俄勒冈州" },
  "42": { abbr: "PA", nameEn: "Pennsylvania", nameZh: "宾夕法尼亚州" },
  "44": { abbr: "RI", nameEn: "Rhode Island", nameZh: "罗德岛州" },
  "45": { abbr: "SC", nameEn: "South Carolina", nameZh: "南卡罗来纳州" },
  "46": { abbr: "SD", nameEn: "South Dakota", nameZh: "南达科他州" },
  "47": { abbr: "TN", nameEn: "Tennessee", nameZh: "田纳西州" },
  "48": { abbr: "TX", nameEn: "Texas", nameZh: "得克萨斯州" },
  "49": { abbr: "UT", nameEn: "Utah", nameZh: "犹他州" },
  "50": { abbr: "VT", nameEn: "Vermont", nameZh: "佛蒙特州" },
  "51": { abbr: "VA", nameEn: "Virginia", nameZh: "弗吉尼亚州" },
  "53": { abbr: "WA", nameEn: "Washington", nameZh: "华盛顿州" },
  "54": { abbr: "WV", nameEn: "West Virginia", nameZh: "西弗吉尼亚州" },
  "55": { abbr: "WI", nameEn: "Wisconsin", nameZh: "威斯康星州" },
  "56": { abbr: "WY", nameEn: "Wyoming", nameZh: "怀俄明州" },
};

const ABBR_TO_FIPS = Object.fromEntries(
  Object.entries(STATE_META).map(([fips, meta]) => [meta.abbr, fips]),
) as Record<string, string>;

const CITY_ZH: Record<string, string> = {
  "Berkeley": "伯克利", "Boston": "波士顿", "Cambridge": "剑桥", "Chicago": "芝加哥",
  "Durham": "达勒姆", "Ithaca": "伊萨卡", "Los Angeles": "洛杉矶", "New Haven": "纽黑文",
  "New York": "纽约", "Pasadena": "帕萨迪纳", "Philadelphia": "费城", "Pittsburgh": "匹兹堡",
  "Princeton": "普林斯顿", "Providence": "普罗维登斯", "Stanford": "斯坦福", "Ann Arbor": "安娜堡",
  "Austin": "奥斯汀", "Champaign": "香槟", "Madison": "麦迪逊", "Seattle": "西雅图", "Evanston": "埃文斯顿",
  "Baltimore": "巴尔的摩", "Houston": "休斯敦", "Atlanta": "亚特兰大", "St. Louis": "圣路易斯",
};

const RANKING_WEIGHT: Record<RankingTier, number> = { top20: 4, top50: 3, top100: 2, other: 1 };
const COMMUNITY_WEIGHT: Record<ChineseCommunityLevel, number> = { low: 1, medium: 2, high: 3 };

function slugify(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "unknown";
}

function average(values: number[]): number {
  const clean = values.filter((value) => Number.isFinite(value));
  if (clean.length === 0) return 0;
  return clean.reduce((sum, value) => sum + value, 0) / clean.length;
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}

function stateFipsForUniversity(university: UniversityPOI & { state?: string; stateFips?: string }): string {
  if (university.stateFips) return university.stateFips.padStart(2, "0");
  if (university.state && ABBR_TO_FIPS[university.state]) return ABBR_TO_FIPS[university.state];
  return "00";
}

function dominantCommunity(levels: ChineseCommunityLevel[]): ChineseCommunityLevel {
  const avg = average(levels.map((level) => COMMUNITY_WEIGHT[level]));
  if (avg >= 2.5) return "high";
  if (avg >= 1.5) return "medium";
  return "low";
}

function bestRankingTier(tiers: RankingTier[]): RankingTier {
  return tiers.reduce<RankingTier>((best, tier) => (
    RANKING_WEIGHT[tier] > RANKING_WEIGHT[best] ? tier : best
  ), "other");
}

export function getStateAbbr(fipsCode: string): string {
  return STATE_META[fipsCode]?.abbr ?? fipsCode;
}

export function getStateNameEn(fipsCode: string): string {
  return STATE_META[fipsCode]?.nameEn ?? fipsCode;
}

export function getStateNameZh(fipsCode: string): string {
  return STATE_META[fipsCode]?.nameZh ?? getStateNameEn(fipsCode);
}

export function getStateCenter(fipsCode: string): [number, number] | undefined {
  return STATE_CENTERS[fipsCode];
}

export function buildCityAggregates(inputUniversities?: UniversityPOI[]): CityAggregate[] {
  const universities = inputUniversities ?? (universityData.universities as unknown as UniversityPOI[]);
  const groups = new Map<string, UniversityPOI[]>();

  universities.forEach((university) => {
    if (!Number.isFinite(university.latitude) || !Number.isFinite(university.longitude)) return;
    const stateFips = stateFipsForUniversity(university as UniversityPOI & { state?: string; stateFips?: string });
    const cityName = university.city?.trim() || "Unknown";
    const id = `${stateFips}-${slugify(cityName)}`;
    const group = groups.get(id) ?? [];
    group.push(university);
    groups.set(id, group);
  });

  return Array.from(groups.entries())
    .map(([id, items]) => {
      const first = items[0] as UniversityPOI & { admissionRate?: number; employmentScore?: number; state?: string; stateFips?: string };
      const stateFips = stateFipsForUniversity(first);
      const name = first.city?.trim() || "Unknown";
      const admissionRates = items
        .map((u) => (u as UniversityPOI & { admissionRate?: number }).admissionRate)
        .filter((rate): rate is number => typeof rate === "number" && Number.isFinite(rate));
      const employmentScores = items
        .map((u) => (u as UniversityPOI & { employmentScore?: number }).employmentScore)
        .filter((score): score is number => typeof score === "number" && Number.isFinite(score));

      return {
        id,
        name,
        nameZh: CITY_ZH[name] ?? name,
        stateFips,
        stateAbbr: getStateAbbr(stateFips),
        latitude: average(items.map((u) => u.latitude)),
        longitude: average(items.map((u) => u.longitude)),
        universityCount: items.length,
        universities: [...items].sort((a, b) => RANKING_WEIGHT[b.rankingTier] - RANKING_WEIGHT[a.rankingTier] || a.name.localeCompare(b.name)),
        avgAnnualCostRmb: average(items.map((u) => u.annualCostRmb)),
        avgSafetyScore: average(items.map((u) => u.safetyScore)),
        avgRecognitionScore: average(items.map((u) => u.recognitionScore)),
        avgAdmissionRate: admissionRates.length > 0 ? average(admissionRates) : undefined,
        avgEmploymentScore: employmentScores.length > 0 ? average(employmentScores) : undefined,
        dominantChineseCommunity: dominantCommunity(items.map((u) => u.chineseCommunity)),
        directFlightCount: items.filter((u) => u.directFlight).length,
        topRankingTier: bestRankingTier(items.map((u) => u.rankingTier)),
      } satisfies CityAggregate;
    })
    .sort((a, b) => b.universityCount - a.universityCount || a.name.localeCompare(b.name));
}

export function getCitiesByState(stateFips: string, cities = buildCityAggregates()): CityAggregate[] {
  return cities.filter((city) => city.stateFips === stateFips);
}

export function getCityById(cityId: string, cities = buildCityAggregates()): CityAggregate | undefined {
  return cities.find((city) => city.id === cityId);
}

export function getCityMetricValue(city: CityAggregate, metricId: MetricId): number {
  switch (metricId) {
    case "safety":
      return clamp01(city.avgSafetyScore / 100);
    case "cost":
      return clamp01(city.avgAnnualCostRmb / 800000);
    case "employment":
      return clamp01((city.avgEmploymentScore ?? city.avgRecognitionScore) / 100);
    case "chinese_population":
      return city.dominantChineseCommunity === "high" ? 0.9 : city.dominantChineseCommunity === "medium" ? 0.55 : 0.25;
    case "income":
    default:
      return clamp01(city.avgRecognitionScore / 100);
  }
}

export function cityMetricColor(metricId: MetricId, value = 0.62): string {
  const t = clamp01(value);
  const ramps: Record<MetricId, [string, string, string]> = {
    income: ["#d9f0d3", "#74c476", "#238b45"],
    safety: ["#d73027", "#fee08b", "#4575b4"],
    employment: ["#d9f0e6", "#66c2a4", "#238b45"],
    cost: ["#fee6ce", "#fdae6b", "#e6550d"],
    chinese_population: ["#ffffb2", "#fecc5c", "#e31a1c"],
    admission_rate: ["#fee8d8", "#fb6a4a", "#cb181d"],  };
  const [low, mid, high] = ramps[metricId];
  if (t < 0.33) return low;
  if (t < 0.66) return mid;
  return high;
}

export function getCityMetricDisplay(city: CityAggregate, metricId: MetricId): string {
  switch (metricId) {
    case "safety":
      return `${Math.round(city.avgSafetyScore)}/100`;
    case "cost":
      return `¥${(city.avgAnnualCostRmb / 10000).toFixed(1)}万`;
    case "employment":
      return typeof city.avgEmploymentScore === "number" ? `${Math.round(city.avgEmploymentScore)}/100` : `${Math.round(city.avgRecognitionScore)}/100`;
    case "chinese_population":
      return city.dominantChineseCommunity === "high" ? "高" : city.dominantChineseCommunity === "medium" ? "中" : "低";
    case "income":
    default:
      // Current project data does not yet include real ACS city income rows.
      // Use an explicit index label rather than pretending this is real income.
      return `指数 ${Math.round(getCityMetricValue(city, metricId) * 100)}`;
  }
}
