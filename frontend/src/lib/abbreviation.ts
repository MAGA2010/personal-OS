// Stage 7A — deterministic abbreviation picker for map POIs.
//
// Falls back through: short alias → initials of English name → initials
// of Chinese name → id-derived initials → last-resort 1-char id tail.
// Always returns 1–3 ASCII characters. Always returns *something*
// (never undefined, never "N/A", never empty string) so the
// symbol-layer text-field on the map is never blank.

export function pickAbbreviation(input: {
  /** Optional explicit short name override (e.g. "Caltech", "MIT"). */
  shortName?: string | null;
  /** English display name, e.g. "Massachusetts Institute of Technology". */
  englishName?: string | null;
  /** Chinese display name, e.g. "麻省理工学院". */
  chineseName?: string | null;
  /** Stable id used as a last-resort fallback. */
  id: string;
}, maxLen = 3): string {
  const sn = (input.shortName ?? "").trim();
  if (sn) return sn.toUpperCase().slice(0, maxLen);

  const en = (input.englishName ?? "").trim();
  if (en) {
    const initials = en
      .replace(/[.,()&]/g, " ")
      .split(/\s+/)
      .filter(Boolean)
      .map((w) => w[0]!.toUpperCase())
      .join("");
    // Skip single-letter initials like "U" for "University" — use the
    // first consonant cluster instead so "Boston University" → "BU"
    // instead of "B U" rendering as "BU".
    const stops = new Set(["OF", "THE", "AND", "AT", "IN", "FOR", "OF"]);
    const tokens = en
      .replace(/[.,()&]/g, " ")
      .split(/\s+/)
      .filter((w) => w && !stops.has(w.toUpperCase()));
    const filteredInitials = tokens.map((w) => w[0]!.toUpperCase()).join("");
    if (filteredInitials.length >= 2 && filteredInitials.length <= maxLen) return filteredInitials;
    if (filteredInitials.length > maxLen) return filteredInitials.slice(0, maxLen);
    if (initials.length >= 2 && initials.length <= maxLen) return initials;
    if (initials.length > maxLen) return initials.slice(0, maxLen);
  }

  const zh = (input.chineseName ?? "").trim();
  if (zh) {
    // Strip non-Chinese characters and pick first maxLen characters.
    const cleaned = Array.from(zh).filter((ch) => /[一-鿿]/.test(ch));
    if (cleaned.length > 0) return cleaned.slice(0, maxLen).join("");
  }

  // Last resort: derive 1–2 chars from the id tail.
  const tail = input.id.split(/[-_:]/).pop() ?? input.id;
  if (tail.length >= 2) return tail.slice(0, 2).toUpperCase();
  return (tail[0] ?? "?").toUpperCase();
}