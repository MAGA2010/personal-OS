# PathOS Stage 5 Closing UI Compliance Patch Report

## Outcome

The three High findings identified by the Stage 5 Integration Gate are closed
within the one-time frozen-UI exception. The normal Preview data path and data
semantics are unchanged.

## Frozen UI exceptions

| File | High | Minimal behavior change |
|---|---|---|
| `src/components/map/MapShell.tsx` | Parent readiness; map backend failure | Reads manifest readiness, hides Parent Mode when unavailable, safely downgrades persisted parent state, and replaces the failed map shell with the shared fail-closed panel. |
| `src/components/university/UniversityDetailView.tsx` | University backend failure/404 | Uses the shared safe error presentation and never renders another school on error. |
| `src/components/shared/data-states.tsx` | Error presentation | Adds one small error-code classifier and panel using existing colors, spacing, retry button, and public wording. |
| `src/app/university/[id]/page.tsx` | Static route fixture dependency | Uses方案 A: request-time dynamic route; removes the fixture import and `generateStaticParams`. |

Frozen-directory files modified: **4**. No layout, map-operation, Compare,
Search, Tailwind, responsive-rule, or design-system changes were made.

## Parent Mode readiness

- Readiness comes from the active manifest `enabledFeatures` /
  `disabledFeatures`.
- Backend Preview declares `parent_mode` disabled, so the toggle is not
  rendered.
- The URL state bridge converts `mode=parent` to `mode=student` after backend
  readiness resolves and rewrites the URL without a render-time router update.
- Student Mode remains valid.
- The real fixture-mode manifest does not disable Parent Mode, so explicit
  fixture development behavior remains available.
- The toggle is hidden while readiness is unresolved, preventing a premature
  entry and keeping the server/client initial render consistent.

## Error presentation

- `TIMEOUT`, `BACKEND_UNAVAILABLE`, backend 5xx and connection failures use the
  retryable backend-unavailable state.
- `UNIVERSITY_NOT_FOUND` uses a non-retryable not-found state.
- invalid JSON, invalid schema and unsupported contract states use a
  non-retryable contract-invalid state.
- disabled features use a distinct feature-disabled state.
- Machine-readable BFF error codes are retained by the DataSource; response
  bodies, absolute paths and stack traces are not rendered.
- Backend failure continues to reject; it is never transformed into a
  successful empty dataset and never selects fixture mode.

## University route

The project does not use `output: "export"` and already requires a server
runtime for the Preview BFF. The route therefore uses方案 A:

- `dynamic = "force-dynamic"`
- `dynamicParams = true`
- no `generateStaticParams`
- no fixture import

The production/backend build reports `/university/[id]` as `ƒ` dynamic.
Runtime detail requests continue through `PathOSDataSource`. The real Bundle
contains 62 unique stable IDs; unknown IDs return the explicit not-found state.

## Automated verification

| Check | Result |
|---|---|
| Closing UI tests | 18/18 PASS |
| Existing frontend tests | 58/58 PASS |
| Total frontend tests | 76/76 PASS |
| TypeScript | PASS |
| Lint | PASS; 8 unchanged warnings in pre-existing frozen pages |
| Backend-mode Next build | PASS; dynamic university route |
| Stage 5 backend tests | 49/49 PASS |
| Stage 5 validator | 49/49 PASS |
| Deterministic regeneration | PASS; zero Git diff |
| Network-disabled generation | PASS |
| Stage 4B frozen validator | 60/60 PASS |
| Stage 4C frozen validator | 86/86 PASS |

Historical cache-dependent Python replay remains unavailable in the
self-contained clone because prohibited untracked cache bodies were not copied.
This patch does not depend on those bodies and does not treat that environment
boundary as a UI failure.

## Browser verification

Backend-mode routes:

- `/map?mode=parent`
- ranked Harvard detail
- not-in-scope and SAT/ACT-not-reported Arizona State detail
- partial-enrollment Harvey Mudd detail
- county-only Boston College detail
- nonexistent university ID

Observed:

- persisted parent URL changed to `mode=student`;
- Parent Mode control was absent and normal metric interaction remained active;
- normal map and all four representative details loaded without unsafe zero
  coercions;
- nonexistent ID showed `未找到该学校` with no other school;
- missing Bundle produced `后端服务暂不可用` with no fixture school;
- the error panel passed at desktop 1280×720 and mobile 390×844;
- after restoring the Bundle, a fresh browser tab loaded the map normally;
- no relevant application warning/error or framework overlay remained in the
  final fresh tabs.

A stale tab retained a compiled Next chunk across the deliberate dev-server
restart and logged one transient chunk syntax error. A fresh tab against the
restored server had no error and is the recovery result used for the Gate.

Read-only code review found no Critical or High issue. Its one Medium finding
was fixed before closure: a missing `source-index.json` is now retained as a
Bundle failure instead of being misclassified as a university 404. The new
regression case passes.

## Data and backend boundaries

- Data semantics changed: **false**
- Preview facts changed: **false**
- Adapter changed: **false**
- Backend Git changed: **false**
- Backend HEAD remains
  `b73e61ec4fda11b7c72e74c14e414fbe2c74300f`
- Fixture contents changed: **false**
- Production export generated: **false**
- Old repository or linked worktree accessed/modified: **false**

## Gate recommendation

- Critical: **0**
- High: **0**
- Ready for independent Frontend–Backend Integration Re-Gate: **yes**
