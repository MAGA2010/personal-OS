# Stage 2E — University Universe Completion Strategy

## Decision and boundary

The current seven-school artifact is a **source-limited candidate**, not a completed ranking universe. The next target is a **completed ranking universe candidate v1**: every scope ranking cutoff must be processed, but it remains non-final until an independent Gate audit. It is still not the full PathOS database; majors, tuition, ratio, geography, people, history, and frontend export remain out of scope.

This planning stage creates no seed batch, ranking record, final universe, selection membership, canonical university, or frontend export.

## Current gap baseline

| Metric | Current state |
| --- | ---: |
| Scope streams | 29 (National Universities plus 28 included undergraduate program categories) |
| Verified records | 24 |
| Source-limited candidate universities | 7 |
| Incomplete streams | 29 / 29 |
| No-verified streams | 8 |
| National Universities coverage | Top-3 pilot only |

National Universities lacks numeric ranks 4–50 and every relevant tie group. Batch 1 and Batch 2 generally have one verified record per stream; Batch 3 has one verified Marketing record and eight no-verified streams. The current seven schools therefore cannot estimate the completed union size or be extrapolated into it.

## Phase A — National Universities Top 50

The Stage 2F manual-seed import supersedes the original numeric-rank cutoff wording for this source: process the first 50 U.S.-domestic entries and the complete tie group containing the fiftieth entry. In the supplied PDF that boundary is University of Rochester at original rank 46; rank 51 is excluded. This is intentionally not `numeric_rank <= 50`.

Use U.S. News public ranking pages or official release material first. A university official page can support a record only if it directly establishes the 2026 edition, National Universities category, and numeric rank. Each verified record requires direct edition evidence, short evidence anchors, preserved source display name, numeric/displayed rank, and tie state. Ambiguous or inferred edition evidence is partial/unresolved and never closes a gap.

Coverage completion is checked by numeric rank and tie group, not by `records == 50`. Identity mapping remains explicit and source-name-preserving; UNITID work is deferred.

## Phase B — High-yield program streams

The initial ten priority streams are selected because they are broad undergraduate subjects, degree-structure categories, or high-demand business specialties likely to identify schools outside National Universities Top 50. “Expected added schools” is deliberately qualitative: a numeric forecast would be unsupported before verified cutoff records exist.

| Stream | Expected union contribution | Difficulty | Main risk |
| --- | --- | --- | --- |
| Undergraduate Business Programs | High | Medium | Ties and school-level names |
| Entrepreneurship | Medium | High | Sparse specialty evidence |
| Finance | Medium | High | Missing direct edition labels |
| International Business | Medium | High | Incomplete category context |
| Marketing | Medium | Medium | One current record is not cutoff coverage |
| Engineering Programs (No Doctorate) | High | High | Doctorate-category confusion |
| Undergraduate Computer Science | High | High | Graduate ranking contamination |
| Undergraduate Nursing | Medium | High | Graduate nursing contamination |
| Undergraduate Economics | Medium | High | Department/program naming |
| Undergraduate Psychology | Medium | High | Graduate psychology contamination |

For each stream, use U.S. News official public material first and school/college official 2026 rank announcements only as direct-evidence supplements. A priority stream becomes complete only when all numeric ranks through 20 and associated ties are covered or when lawful direct-source routes are exhausted and the resulting gap is explicitly recorded.

### Stage 2G incremental official-source collection

Because the public U.S. News program pages were not a stable complete-cutoff feed, Stage 2G uses separate official-source incremental batches. A batch may collect roughly 15 individual records across the ten priority streams, but every stream remains `incomplete` unless its full first-20-entry-plus-boundary-tie group is independently evidenced. A stream with no record must remain represented as `not_collected_in_batch`; it must not receive a guessed rank or fabricated candidate. Official university or college pages must directly state the institution, undergraduate category, numeric rank, and 2026 Best Colleges context. These incremental artifacts do not by themselves authorize a completed candidate, final universe, selection memberships, or frontend export.

## Phase C — Remaining program streams

The remaining 18 included streams are: Accounting, Analytics, Management, Management Information Systems, Production/Operations Management, Real Estate, Supply Chain Management/Logistics, Engineering Programs (Doctorate), and Aerospace, Biomedical, Chemical, Civil, Computer, Electrical, Environmental, Industrial, Materials, and Mechanical Engineering.

Process six streams per batch. Every batch has its own full artifact bundle and coverage matrix. Keep partial/unresolved observations as auditable candidates only; do not stage them or create candidate universities from them. Stop a stream only at complete Top-20-with-ties coverage or a documented lawful-source exhaustion condition.

## Source policy for completed universe work

1. U.S. News official public page or official release.
2. University or college official page that directly states edition, category, and rank.
3. Trusted public institution only as a supplementary cross-check.

Search snippets, AI memory, unofficial reposts, forums, and prestige-based inference are never final evidence. The pipeline must not bypass login, paywalls, CAPTCHA, robots controls, or other access restrictions. Without direct edition evidence, a finding remains partial/unresolved and cannot enter a completed universe candidate.

## Future artifact layout

Future collection phases use separate, non-overwriting bundles:

```text
data/ranking-seeds/2026-best-colleges/
  completion-national/
  completion-programs-priority/
  completion-programs-remaining/
data/university-universe/2026-best-colleges/
  completed-candidate/
```

Every collection bundle will contain seed batches, source manifest, identity mappings, candidate observations, coverage matrix, validation result, and gap report. The `completed-candidate` is generated only after completed-corpus validation; it is never the final database universe or a frontend source.

## Universe Completion Accepted

Universe Completion Accepted requires all of the following:

1. National Universities has a Gate-approved first-50-U.S.-domestic-entry corpus with the boundary tie group processed.
2. All 28 in-scope undergraduate program streams through rank 20 and ties processed.
3. Only verified records enter the completed candidate; partial/unresolved remain excluded.
4. No-verified streams are documented without fake records or schools.
5. Duplicate identities resolved; Global and Graduate contamination remains zero.
6. Completed corpus validation passes and generates the completed ranking universe candidate.
7. An independent Gate audit passes.

Even then, the result is only a completed ranking-universe candidate. It does not accept the full PathOS database until downstream school-detail phases are complete and audited.
