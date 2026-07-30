// Stage 7B-A.3.1 — FIPS normalizer.
//
// Single source of truth for converting any FIPS input to a canonical
// 2-digit zero-padded string. Used by:
//   - MapShell.handleRegionClick (URL `state=` param, click handler)
//   - useViewStateBridge (`?state=` URL param)
//   - RegionDetailSidebar (state lookup, university filter)
//   - RegionalStateLayer (selected outline filter)
//
// Rules:
//   "6"   → "06"      (1-char string → pad)
//   6     → "06"      (number → pad)
//   "06"  → "06"      (canonical, no change)
//   null  → null
//   ""    → null
//   undefined → null
//   "abc" → null      (invalid → null, not "ab")

export function normalizeStateFips(raw: string | number | null | undefined): string | null {
  if (raw === null || raw === undefined) return null;
  const s = String(raw).trim();
  if (s === "") return null;
  // 2 digits required; pad with leading zero if exactly 1 digit or numeric < 10
  if (/^\d{1,2}$/.test(s)) {
    return s.padStart(2, "0");
  }
  // Anything else (e.g. "abc", "06x", longer numeric) is invalid
  return null;
}
