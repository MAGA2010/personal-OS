# Stage 3D-Fill Bulk People v2 — Batch B Implementation Prompt

## Objective

Build an independent reviewed-source Batch B overlay for exactly 20 Candidate v2 universities. Process one reviewed notable-attendance record and one immutable Top-1 demo-program person slot per school. Program-person acceptance is provenance-first; a processed slot may remain `source_review_not_completed`.

## Corrected school scope

Virginia Tech is excluded because it is not a Candidate v2 institution. Texas A&M University replaces it. The executable school manifest is `data-pipeline/data/stage3d-fill-bulk-people-v2-batch-b/school-manifest.json` and must satisfy all of the following:

- exactly 20 distinct candidate IDs;
- every candidate ID belongs to Candidate v2;
- `candidate-v2:virginia-tech` is absent;
- `candidate-v2:texas-a-and-m-university` is present.

The manifest uses Candidate v2 canonical display names and IDs. It must not create aliases as new schools or expand the universe.

## Inputs and immutability

Read only:

- Candidate v2 candidate universities;
- Stage 3D-Fill Bulk People v2 Top-1 slot inventory;
- Stage 3D-Fill Bulk People v1 reviewed attendance, source, and cache manifests;
- Batch A committed artifacts for cumulative A+B statistics;
- Batch B reviewed program-person observations and source/cache manifests.

Do not modify Candidate v2, Stage 3/3B/3C/3C2/3D, earlier Stage 3D-Fill artifacts, Bulk People v1, Batch A, or frontend. Do not generate a final universe, formal memberships, or frontend export.

## Positive evidence rules

- Attendance relationships: `graduated`, `alumnus_unspecified`, or `attended_no_degree` only.
- Identified program person: reviewed attendance plus a source-stated `direct_program_match` or `direct_related_program_match`.
- No profession, employer, fame, achievement, or research-area inference.
- Canonical person IDs must include normalized name, candidate context, and a source-backed disambiguator.
- All direct quotes use `local_cache_substring_check`; cache SHA-256 and quote substring verification are mandatory.
- `no_qualifying_person_found` requires non-empty `reviewed_scope` and `reviewed_source_ids`; otherwise preserve `source_review_not_completed`.

## Cumulative accounting

Batch A and Batch B both contain University of Michigan—Ann Arbor. Report both:

- batch occurrences: 30;
- unique A+B universities: derived dynamically from the union (expected 29).

Never hard-code cumulative identified/gap counts. Derive them from committed Batch A artifacts plus the generated Batch B overlay, applying slot-status precedence for duplicate slot keys.

## Deliverables and verification

Add the independent Batch B module, CLI commands, tests, data inputs, nine required JSON artifacts, report, and development-log entry. Run Batch B tests, all Python tests, Batch B validator, schema/migration validation, byte-identical regeneration, `git diff --check`, and final `git status`. Commit once with `feat(data): add stage3d bulk people v2 batch b`; do not tag or push.
