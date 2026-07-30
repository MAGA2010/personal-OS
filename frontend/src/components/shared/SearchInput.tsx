// SearchInput — single source of truth for the "搜索学校 / 城市"
// search field used by `/assessment`, `/portfolio`, and any future
// page that needs a debounced single-line search.
//
// Why a shared component:
//   The same exact JSX (icon + input + identical Tailwind classes)
//   appeared in assessment and portfolio before this was extracted
//   (see docs/UI-CONTROL-DUPLICATION-AUDIT.md §1). Centralising it
//   here means a styling tweak lands in both places at once and we
//   don't accumulate drift.
//
// Behaviour:
//   - Debounced `onChange` is the consumer's responsibility; this
//     component is a presentational wrapper. The icon, padding, and
//     focus ring are baked in.
//   - `aria-label` defaults to "搜索学校" but is overridable.

import type { InputHTMLAttributes } from "react";
import { Search } from "lucide-react";

export interface SearchInputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "onChange"> {
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
  ariaLabel?: string;
}

export function SearchInput({
  value,
  onChange,
  placeholder = "搜索学校 / 城市",
  ariaLabel = "搜索学校",
  className = "",
  ...rest
}: SearchInputProps) {
  return (
    <div className={`relative ${className}`}>
      <Search
        size={15}
        className="absolute left-3 top-1/2 -translate-y-1/2 text-ink/30"
        aria-hidden="true"
      />
      <input
        {...rest}
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel}
        className="w-full rounded-xl border border-line/60 bg-panel py-2 pl-9 pr-3 text-sm outline-none focus:border-cobalt/45"
      />
    </div>
  );
}

export default SearchInput;