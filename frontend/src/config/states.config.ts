// PathOS — US state reference tables.
// Centralised lookup tables for state abbreviations / FIPS codes /
// Chinese and English names. The previous `state-options.json` lived
// in `src/data/` and was moved to `src/test/fixtures/` (Phase 2); this
// config file is the production replacement.

// Mapping of US state abbreviation -> 2-digit FIPS code (zero-padded).
export const ABBR_TO_FIPS: Record<string, string> = {
  AL: "01", AK: "02", AZ: "04", AR: "05", CA: "06", CO: "08", CT: "09",
  DE: "10", FL: "12", GA: "13", HI: "15", ID: "16", IL: "17", IN: "18",
  IA: "19", KS: "20", KY: "21", LA: "22", ME: "23", MD: "24", MA: "25",
  MI: "26", MN: "27", MS: "28", MO: "29", MT: "30", NE: "31", NV: "32",
  NH: "33", NJ: "34", NM: "35", NY: "36", NC: "37", ND: "38", OH: "39",
  OK: "40", OR: "41", PA: "42", RI: "44", SC: "45", SD: "46", TN: "47",
  TX: "48", UT: "49", VT: "50", VA: "51", WA: "53", WV: "54", WI: "55",
  WY: "56", DC: "11",
};

// State Chinese display names keyed by FIPS code.
export const STATE_NAME_ZH: Record<string, string> = {
  "01": "阿拉巴马州", "02": "阿拉斯加州", "04": "亚利桑那州", "05": "阿肯色州",
  "06": "加利福尼亚州", "08": "科罗拉多州", "09": "康涅狄格州", "10": "特拉华州",
  "11": "华盛顿特区", "12": "佛罗里达州", "13": "乔治亚州", "15": "夏威夷州",
  "16": "爱达荷州", "17": "伊利诺伊州", "18": "印第安纳州", "19": "爱荷华州",
  "20": "堪萨斯州", "21": "肯塔基州", "22": "路易斯安那州", "23": "缅因州",
  "24": "马里兰州", "25": "马萨诸塞州", "26": "密歇根州", "27": "明尼苏达州",
  "28": "密西西比州", "29": "密苏里州", "30": "蒙大拿州", "31": "内布拉斯加州",
  "32": "内华达州", "33": "新罕布什尔州", "34": "新泽西州", "35": "新墨西哥州",
  "36": "纽约州", "37": "北卡罗来纳州", "38": "北达科他州", "39": "俄亥俄州",
  "40": "俄克拉荷马州", "41": "俄勒冈州", "42": "宾夕法尼亚州", "44": "罗德岛州",
  "45": "南卡罗来纳州", "46": "南达科他州", "47": "田纳西州", "48": "德克萨斯州",
  "49": "犹他州", "50": "佛蒙特州", "51": "弗吉尼亚州", "53": "华盛顿州",
  "54": "西弗吉尼亚州", "55": "威斯康星州", "56": "怀俄明州",
};

// State English display names keyed by FIPS code.
export const STATE_NAME_EN: Record<string, string> = {
  "01": "Alabama", "02": "Alaska", "04": "Arizona", "05": "Arkansas",
  "06": "California", "08": "Colorado", "09": "Connecticut", "10": "Delaware",
  "11": "District of Columbia", "12": "Florida", "13": "Georgia", "15": "Hawaii",
  "16": "Idaho", "17": "Illinois", "18": "Indiana", "19": "Iowa",
  "20": "Kansas", "21": "Kentucky", "22": "Louisiana", "23": "Maine",
  "24": "Maryland", "25": "Massachusetts", "26": "Michigan", "27": "Minnesota",
  "28": "Mississippi", "29": "Missouri", "30": "Montana", "31": "Nebraska",
  "32": "Nevada", "33": "New Hampshire", "34": "New Jersey", "35": "New Mexico",
  "36": "New York", "37": "North Carolina", "38": "North Dakota", "39": "Ohio",
  "40": "Oklahoma", "41": "Oregon", "42": "Pennsylvania", "44": "Rhode Island",
  "45": "South Carolina", "46": "South Dakota", "47": "Tennessee", "48": "Texas",
  "49": "Utah", "50": "Vermont", "51": "Virginia", "53": "Washington",
  "54": "West Virginia", "55": "Wisconsin", "56": "Wyoming",
};

export function abbrFromFips(fips: string): string | undefined {
  const padded = String(fips ?? "").padStart(2, "0").slice(-2);
  for (const [abbr, code] of Object.entries(ABBR_TO_FIPS)) {
    if (code === padded) return abbr;
  }
  return undefined;
}

export function fipsFromAbbr(abbr: string): string | undefined {
  return ABBR_TO_FIPS[String(abbr ?? "").toUpperCase()];
}

export function stateNameZh(fips: string): string {
  const padded = String(fips ?? "").padStart(2, "0").slice(-2);
  return STATE_NAME_ZH[padded] ?? abbrFromFips(padded) ?? padded;
}

export function stateNameEn(fips: string): string {
  const padded = String(fips ?? "").padStart(2, "0").slice(-2);
  return STATE_NAME_EN[padded] ?? abbrFromFips(padded) ?? padded;
}