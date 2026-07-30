# Stage 5 Integration Development Log

## Scope

- Frontend root: `/Users/jiayihuang/Downloads/PathOS合并/PathOS-main/frontend`
- Backend transport: `preview_bundle_via_next_bff`
- Contract: `pathos-preview-v1`
- Source checkpoint: `ec8c66e200b566dba4de35987aa5213960749a57`
- Existing pre-change baseline reused; it was not overwritten.

## Implementation sequence

1. Reviewed the frozen frontend contract, current DataSource, runtime validators,
   BFF route, Domain model, and forbidden UI directories.
2. Added 34 required frontend contract cases before implementation. A browser-found
   encoded dynamic-route ID case and final contract review of status rejection,
   region/program/major search and all-major gap preservation increased the final
   Stage 5 suite to 38 cases.
3. Split the fixture-only BFF into an explicit fixture implementation and a mode
   dispatcher. `PATHOS_DATA_MODE` is now `fixture|backend`; missing mode defaults
   to backend, and production rejects fixture.
4. Added a backend Bundle reader that validates the manifest before every endpoint,
   reads only the configured Bundle directory, normalizes DTOs at the BFF boundary,
   and returns structured errors without fixture fallback.
5. Added Runtime Schema validation for manifest, Summary, Detail, source index,
   blocked region metrics, coordinates, duplicate IDs, pending policies, 2019
   enrollment warnings, and quarantined people.
6. Added Domain normalization. USD remains the backend fact; the legacy RMB UI
   receives the existing explicit 7.2 conversion. Missing and null values are
   never converted to zero.
7. Disabled backend-mode AI context and AI analysis with a non-retryable
   `AI_CONTEXT_DISABLED` response.
8. Ran TypeScript, frontend tests, lint, production build, real-Bundle API smoke,
   desktop/mobile browser smoke, `/calculator`, `/match`, `/assessment`,
   `/portfolio`, detail-route checks, and failure/no-fallback smoke.

## Browser findings and repairs

- Repaired a double-encoded `candidate-v2:` route parameter at the BFF boundary.
  A regression test now covers `%253A` input resolving exactly once.
- Repaired an incomplete `全国排名 #` label. The authoritative nested rank remains
  `null`; only the legacy mirror becomes `undefined` so the frozen UI takes its
  existing missing-data branch.
- Extended backend search over the real Summary contract to include region and
  top-program labels, plus Detail-level all-major labels, matching the frozen
  search contract without inflating Summary.
- Preserved the complete blocked region envelope through the BFF while the
  DataSource unwraps its empty records for the frozen UI.
- Added an explicit Runtime Status allowlist and rejected unknown Detail statuses.
- Replaced synthetic verified source placeholders with resolved, source-limited
  metadata and expanded the frozen status dictionary.
- Preserved `allMajorsStatus`/null reasons through normalization and mapped
  official/verified/source-limited Source Index states to explicit Domain
  provenance instead of treating them as review gaps.
- Confirmed ranked, not-in-scope, SAT/ACT-not-reported, partial-enrollment, and
  county-only records load from the real Bundle with no `¥0`, `¥NaN`, rank 0,
  ratio 0, or `[0,0]`.

## Frozen-UI boundary

No file in `src/components/**`, `src/app/map/**`, `src/app/university/**`,
`src/state/**`, Tailwind configuration, or public wording was modified.

Four visible or build-time behaviors require changes inside those prohibited
surfaces:

1. Parent-mode controls remain visible even though backend feature readiness marks
   parent mode disabled.
2. When backend loading fails, the map remains on its existing loading shell rather
   than rendering an explicit error panel. The request still fails closed and does
   not show fixture schools.
3. Structured admissions, enrollment, and people-gap metadata reaches the Domain
   boundary but is not fully rendered by the frozen detail component.
4. The production build succeeds, and `dynamicParams=true` serves Candidate v2
   routes at runtime, but the frozen university route still imports fixture IDs
   for `generateStaticParams`.

These are recorded as `frontend-agent-required`; no prohibited edit was made.
