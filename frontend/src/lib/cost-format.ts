// Cost-presentation helpers.
// Keeps currency formatting consistent across Calculator, MapShell, and
// UniversityCard. None of the formatters synthesise a number from a
// missing field — they either show the canonical "学费数据补充中" empty
// state or the formatted value.
//
// All currency helpers accept `number | null | undefined`:
//   - finite positive number → formatted with the requested currency
//   - 0                     → treated as missing (legacy data sometimes
//                              zero-fills where the real number is absent);
//                              empty state is shown so we never claim ¥0
//                              when the backend didn't actually publish a
//                              tuition value
//   - null / undefined / NaN → empty state
//
// The empty state label is centralised here so the copy cannot drift
// between pages.

export const TUITION_EMPTY_LABEL = "学费数据补充中";

export type FormattedCost =
  | { kind: "empty"; label: string }
  | { kind: "value"; label: string };

const RMB = new Intl.NumberFormat("zh-CN", {
  style: "currency",
  currency: "CNY",
  maximumFractionDigits: 0,
});
const USD = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function isUsableNumber(n: unknown): n is number {
  return typeof n === "number" && Number.isFinite(n) && n > 0;
}

/**
 * Format a Yuan-denominated tuition value. Returns the canonical
 * "数据补充中" copy when the value is absent or zero-filled.
 *
 * @param amountRmb  Tuition in RMB (number, null, or undefined)
 * @param exchangeRate  RMB→USD multiplier (defaults to 7.2)
 */
export function formatRmb(
  amountRmb: number | null | undefined,
  exchangeRate = 7.2,
): FormattedCost {
  if (!isUsableNumber(amountRmb)) {
    return { kind: "empty", label: TUITION_EMPTY_LABEL };
  }
  const rmb = RMB.format(amountRmb);
  const usd = USD.format(amountRmb / exchangeRate);
  return { kind: "value", label: `${rmb} (${usd})` };
}

/** Shorter RMB-only formatter for compact UI rows. */
export function formatRmbShort(amountRmb: number | null | undefined): FormattedCost {
  if (!isUsableNumber(amountRmb)) {
    return { kind: "empty", label: TUITION_EMPTY_LABEL };
  }
  return { kind: "value", label: RMB.format(amountRmb) };
}

/**
 * Compute the annual total cost (RMB) for a school + tier. Returns
 * `null` when tuition is absent — callers should then exclude the
 * school from numeric comparisons rather than falling back to ¥0.
 */
export function computeAnnualTotalRmb(
  tuitionRmb: number | null | undefined,
  tierLivingRmb: number,
  costMultiplier: number,
  standardFixedRmb: number,
): number | null {
  if (!isUsableNumber(tuitionRmb)) return null;
  const living = Math.round(tierLivingRmb * costMultiplier);
  return tuitionRmb + living + standardFixedRmb;
}

/**
 * Compute cost multiplier for a region based on its income metric
 * (0..1 normalized). Returns a defensive default when no metric is
 * available; never produces a 0 multiplier that would zero out totals.
 */
export function computeCostMultiplier(incomeValue: number | null | undefined): number {
  if (typeof incomeValue !== "number" || !Number.isFinite(incomeValue)) return 0.7;
  // Same formula the Calculator used historically: 0.4 + income * 0.6.
  return 0.4 + incomeValue * 0.6;
}