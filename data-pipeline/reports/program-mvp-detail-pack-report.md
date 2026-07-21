# Stage 3 — Program-Centric MVP Detail Pack

## Status and scope

This deterministic, source-limited MVP detail pack covers all **62 Candidate v2 universities**. Candidate v2 remains a provenance-validated planning artifact with 67 atomic memberships; neither it nor this pack is a final university universe, final database, formal selection-membership output, or frontend export.

The pack supports demo-oriented program cards, undergraduate tuition display, high/low tuition explanation, student-faculty-ratio gaps, and reported undergraduate areas of study. It does not collect admissions, history, people, or any frontend data.

## Inputs and provenance policy

The generator reads only Candidate v2, accepted program-ranking records already present in the local corpus, and cached official NCES/IPEDS inputs:

- `HD2024`: exact institution identity matches, homepage, city/state, coordinates, and region.
- `IC2023_AY`: institution-level undergraduate tuition and required-fee fields for academic year 2023-24.
- `C2023_A` plus NCES CIP titles: reported 2022-23 bachelor-degree award areas, presented as `areas_of_study`, not as a current catalog assertion.

The source manifest in `program-mvp-gap-disclosure.json` records each source and field-level provenance requirements. The generator calls `validate_source_policy_use("IPEDS", "detail", has_field_provenance=True)` before building outputs. No CollegeData, THE, QS, xuanxiao, or other non-U.S.-News ranking source enters any U.S. News ranking field. `source_policy_violations=0` and `ranking_field_contamination=0`.

## Coverage summary

| Measure | Result |
| --- | ---: |
| Candidate universities represented | 62 / 62 |
| Universities with five provenance-backed demo programs | 54 |
| Universities with fewer than five demo programs and a gap reason | 8 |
| Exact IPEDS identity matches | 51 |
| Exact-match identity gaps retained without guessing | 11 |
| Universities with public in-state/out-of-state undergraduate tuition | 18 |
| Universities with private single undergraduate rate | 33 |
| Universities with university-level tuition data | 51 |
| Universities with tuition not published / identity unresolved | 11 |
| Universities with reported undergraduate areas-of-study list | 51 |
| Universities missing that list | 11 |
| Universities with student-faculty ratio | 0 |
| Universities with explicit student-faculty-ratio gap | 62 |

## Tuition model and high/low display

Tuition fields separate base tuition, mandatory fees, college surcharge, program extra fee, calculated tuition-plus-required-fees totals, and estimated cost of attendance. This Stage 3 pack contains **no** college surcharge and **no** program extra fee because the selected official datasets do not directly prove either.

- Public institutions retain both in-state and out-of-state tuition. The demo comparison uses the out-of-state total and says so explicitly; the in-state value is retained.
- Private institutions use a single undergraduate rate.
- All 255 displayable demo-program tuition rows use university-level tuition with `program_specific=false` and a label that says it is not program-specific.
- 51 universities have identical high/low display amounts because every demo program uses the same university-level undergraduate rate. This is labelled `university_level_same_for_all`, not a claim about program-specific tuition differences.
- 11 universities have null high/low values because no comparable official tuition record was available after exact identity matching.
- Estimated cost of attendance is not present in the tuition calculation input. Graduate, MBA, law, medical, and professional-school tuition are rejected by the validator before display calculation.

American undergraduate tuition commonly varies by residency or institution rather than by major. When no official program-level price exists, this demo applies university-level undergraduate tuition to a program and never describes it as a program-only charge.

## Known gaps

- Student-faculty ratios were deliberately not inferred from unrelated enrollment/staff data. All 62 records disclose `official_student_faculty_ratio_not_collected_in_stage3_mvp`.
- The 11 identity gaps remain unresolved because matching is exact only; no UNITID, campus, or system identity was guessed.
- IPEDS completions are historical reported award areas, not a replacement for an official current undergraduate catalog.
- Candidate v2’s ranking corpus remains source-limited: program streams are incomplete and Economics remains manual-seed-needed. This Stage 3 pack does not change ranking corpus status.

## Validation

The Stage 3 validator checks deterministic regeneration, all 62 candidate IDs across artifacts, top-program provenance or gap reasons, honest tuition/residency models, no COA or graduate/professional tuition, university-level disclosure, majors provenance, source-policy results, and final-output prohibitions. It confirms that no final universe, formal selection memberships, frontend export, or frontend file is generated.

Next recommended work: review this pack as an MVP detail artifact, then separately enrich unresolved identities and collect official student-faculty-ratio, current-catalog, and tuition-page evidence. Do not promote this pack to final product data without a dedicated audit.
