# Stage 3B — Demo Critical Gap Fill

## Scope

Stage 3B is a deterministic, independent overlay over immutable Stage 3 inputs and the fixed 62-school Candidate v2 universe. It is source-limited, incomplete, and not final. It does not create a final universe, official selection memberships, frontend export, or any frontend modification.

## Baseline consistency repair

Stage 3 contained six rows with five demo programs but a residual `top_5_gap_reason`. Stage 3B does not alter those artifacts. Instead, its derived view uses actual program count:

- `stale_top5_gap_reason_original_count`: 6
- `stale_top5_gap_reason_cleared_in_overlay_count`: 6
- actual original fewer-than-five gaps: 8
- gaps resolved through official undergraduate observations: 7
- remaining program gap: University of North Carolina—Chapel Hill, with three verified undergraduate observations and a retained gap reason.

## Student-faculty ratio

All 62 candidates have a direct `STUFACR` value from the official College Scorecard institution-level release dated 2025-05-19. Each ratio row retains the UNITID short evidence anchor, data-release reference, source URL, extraction notes, and definition notes.

`derived_ratio=false` for every row. No enrollment/staff formula was applied, and the values are not represented as school-published facts-page ratios. If a future release requires a derived ratio, it must expose a formula, component variables, source rows, source years, and definition caveat.

## Identity, tuition, and majors gap fill

The 11 original identity gaps are resolved only through a versioned manual-review mapping from a Candidate v2 alias to one exact `IPEDS INSTNM` value. The mapping explicitly excludes similarly named campuses and systems; the resolver refuses a UNITID without an approved mapping and a unique exact HD2024 match.

All 11 resolved identities allow the overlay to add existing official IPEDS university-level undergraduate tuition/required-fee records and reported bachelor award areas. These remain institution-level tuition and historical award areas; they are not program-level tuition or a current official catalog assertion.

## Official undergraduate program supplements

Only school-official undergraduate pages provide the 31 added demo-program observations. The following sources are represented in the versioned observation file:

- Columbia Engineering undergraduate catalog
- Ohio State undergraduate majors by college
- Olin majors and concentrations
- University of South Carolina majors and degrees
- UT Austin undergraduate catalog
- University of Virginia majors and minors
- University of Washington undergraduate degree programs
- UNC Chapel Hill undergraduate programs-of-study catalog

All supplements are `official_institutional`, `undergraduate`, and medium-confidence. They preserve `usnews_category=null` and `usnews_rank=null`; they do not write or overwrite any U.S. News ranking field. Graduate, MBA, law, medical, and professional-only names are rejected.

## Summary

| Measure | Result |
| --- | ---: |
| Candidate scope | 62 / 62 |
| Student-faculty ratios resolved | 62 |
| Identity gaps resolved / remaining | 11 / 0 |
| Tuition gaps resolved / remaining | 11 / 0 |
| Majors gaps resolved / remaining | 11 / 0 |
| Demo-program gaps resolved / remaining | 7 / 1 |
| Directly derived ratios | 0 |
| Source-policy violations | 0 |
| Ranking-field contamination | 0 |
| Demo readiness before / after | 0.629 / 0.996 |

## Remaining blockers before frontend

1. Candidate v2, Stage 3, and Stage 3B are planning/demo artifacts, not a final database or final universe.
2. UNC Chapel Hill still has fewer than five demo programs; only another directly verifiable official undergraduate source may close this gap.
3. The program-ranking corpus remains source-limited and incomplete; official program-page supplements are not ranking records.

The next safe step is a focused Stage 3B/Gate review of field-level provenance and frontend adapter requirements. Do not promote this overlay to final frontend data without that review.
