# Stage 3D-Fill Bulk People v2 Cross-Batch Deduplication Report

## Combined result

- batches: **2**
- input attendance records: **30**
- unique people after merge: **29**
- duplicate person keys detected in immutable inputs: **1**
- duplicate people: **James Earl Jones**
- duplicates remaining after merge: **0**

The deduplication key is `(candidate_id, canonical_person_id)`. Duplicate input records are not deleted or rewritten. The combined layer emits one logical attendance record and preserves all origin batches and source provenance. Same names at different institutions are not merged.

## Boundaries

- source policy violations: **0**
- ranking field contamination: **0**
- final universe generated: **false**
- formal memberships generated: **false**
- frontend export generated: **false**

This combined layer remains `source_limited`, `incomplete`, and `not_final`.
