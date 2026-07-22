# Stage 3C — Academic + Geo Enrichment Report

## Scope and boundary

Stage 3C is an independent deterministic overlay over the fixed 62-university Candidate v2, Stage 3 MVP Detail Pack, and Stage 3B gap-fill overlay. It is source-limited, incomplete, and not final. It does not modify those inputs, create a final universe, create official selection memberships, export frontend data, or modify `frontend/`.

## Readiness at a glance

- Academic/program readiness: complete.
- Region readiness: complete.
- Nearest towns readiness: 0/62.
- Stage 3C is an Academic + partial Geo overlay: region classification is complete, while nearest-town enrichment remains unavailable in this execution environment.
- `demo_program_readiness_after=1.0` does not mean nearest towns are complete. The retained `demo_readiness_after=1.0` field is legacy program-only wording, not an overall Geo-completion signal.

## Academic enrichment

- UNC Chapel Hill’s 2026 official **Undergraduate Programs of Study: Majors and Minors** catalog directly supports `Computer Science Major, B.S.` and `Economics Major, B.A.`. Together with its three Stage 3B official undergraduate demo programs, UNC now has five demo programs.
- The two additions are official undergraduate detail/demo records. Their U.S. News category and rank fields are null; they are not represented as U.S. News ranking records.
- Official-major coverage is best-effort: one reviewed official undergraduate-program source is included. The remaining 61 universities retain `only_ipeds_award_areas_available`, explicitly described as federal reported bachelor-degree award areas rather than a current school catalog.

## Tuition deepening and highest/lowest basis

- All 62 universities retain provenance-backed institution-level undergraduate tuition confirmation.
- No new official college-level surcharge, required program-level fee, or mixed undergraduate differential was added. No fee difference was inferred merely to produce a highest/lowest program.
- 51 universities have `university_level_same_for_all` highest/lowest output. Equal displayed values mean the demo programs share a published university-level undergraduate amount, not that each major has its own tuition.
- Eleven universities have no validated comparable undergraduate display amount and retain `not_published`/null highest-lowest outputs.
- COA, living costs, books, transportation, personal expenses, graduate, MBA, law, medical, and professional tuition were excluded from calculations.

## Geography

- All 62 universities use the controlled U.S. Census four-region taxonomy: Northeast, Midwest, South, or West. Stage 3C does not create a subregion field.
- Campus longitudes are present in the Stage 3C overlay because the overlay reads existing IPEDS `LONGITUD` field-level evidence from Stage 3B; it does not change prior artifact values.
- The normal official Census 2024 National Places Gazetteer download returned HTTP 403 in this execution environment; a normal public Census TigerWeb query was also rejected. No bypass, alternative scraper, or fabricated place data was used.
- Consequently, all 62 `nearest_towns` arrays are empty and disclose `source_unavailable_in_execution_environment`; nearest towns readiness remains 0/62. No bypass, guessing, fabricated distance, county, campus, neighborhood, or driving-distance claim is emitted.

## Validation and policy

- Generator and formal validator check Candidate v2 scope, immutable Stage 3/3B SHA-256 fingerprints, direct official undergraduate evidence, U.S. News ranking isolation, tuition exclusions, fixed region taxonomy, and final-output prohibitions.
- `source_policy_violations = 0`.
- `ranking_field_contamination = 0`.
- Generated outputs are deterministic; validation result is produced by the CLI, not hand-authored.

## Remaining gaps and recommended follow-up

1. Re-run only the nearest-place portion when a normal official Census Gazetteer cache becomes accessible; retain `haversine_straight_line` and eligible place-type rules.
2. Continue official majors/tuition observation collection opportunistically. Do not treat IPEDS award areas as official catalogs and do not infer college/program tuition differences.
3. Submit Stage 3C to independent review before Stage 3D People + Narrative Enrichment. Candidate v2 and all detail overlays remain source-limited/not-final.
