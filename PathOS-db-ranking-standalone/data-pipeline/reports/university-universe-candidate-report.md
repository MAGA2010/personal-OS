# Stage 2D — Source-Limited University Universe Candidate

## Scope and inputs

This artifact is derived only from the validated Stage 2C 2026 Best Colleges corpus: Pilot, Batch 01, Batch 02, Batch 03, and their corpus validation summaries. No source discovery, network collection, ranking-record creation, canonical database write, selection-membership write, or frontend export occurred in Stage 2D.

The output is explicitly source-limited, incomplete, and not final. It is not an authoritative university universe and must not be used for product display or to generate `frontend/src/data/universities.json`.

## Candidate result

- Candidate universities: 7
- Atomic membership candidates: 7
- `national_top_50_candidate`: 3
- `program_top_20_candidate`: 4
- `both_candidate` display summaries: 0
- UNITIDs guessed: 0

The 24 corpus-accepted verified ranking records consolidate into 7 canonical identity candidates, so 17 additional supporting-record occurrences are deduplicated at the candidate identity level. Each candidate and each atomic membership retains source IDs plus references to its ranking-record evidence anchors.

## Inclusion and exclusion

Only verified accepted seed records enter the candidate. The two partially verified rejected observations, including Carnegie Mellon Tepper and Cornell observations from the Pilot, do not enter it. Unresolved observations and the eight streams with no verified records do not create candidates.

For a school that eventually has both kinds of evidence, this contract emits two membership candidate rows: `national_top_50_candidate` and `program_top_20_candidate`. It never writes `both` as a membership reason; any `both_candidate` value would only be a derived display summary.

## Required gap disclosure

- National Universities coverage is only the Top-3 Pilot, not Top-50.
- All 29 processed ranking streams remain incomplete.
- Eight streams have no verified record.
- The candidate represents only institutions appearing in the available verified evidence, not the full PathOS scope.

## Validation

Gate 2 independent audit accepted the Ranking Engine / Source-Limited Candidate Generation at commit `6487c138ca2c3508b08a06df987508fa72e48f7a` with **A. PASS**. The audit's M-1 backlog is hardened in the follow-up validator contract.

`generate-universe-candidate` and `validate-universe-candidate` both require a corpus root and `corpus-validation-result.json`. They revalidate the corpus, compare counts/gaps/readiness with the supplied result, then verify every candidate and membership supporting record, source ID and evidence-anchor reference against accepted verified corpus records. Partial, unresolved, no-verified, non-corpus, or hand-edited references fail closed.

Gap disclosure now requires explicit source-limited/incomplete/not-final flags, National Top-50 incompleteness, no-verified stream count, candidate count, and false permissions for frontend export, final universe, and selection memberships. Metadata has the corresponding truthful flags and false output flags. Candidate artifacts are deterministic generator output; manual edits are rejected.

Executed offline validation: 66 Python tests passed; formal `validate-universe-candidate`, corpus validation, ranking discovery validation, and fixture JSON Schema/migration validation all passed. `git diff --check` reported no whitespace errors. No frontend files were changed.

The hardening commit remains suitable for the next data phase: identity enrichment / UNITID resolution. It is not approval to create a final universe.
