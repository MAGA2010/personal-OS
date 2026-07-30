# Stage 5 Frontend–Backend Integration Report

## Result

The allowed integration layer is implemented and verified against the real
deterministic Preview Bundle. Backend mode reads 62 Summary records and 62 matching
Detail records through the Next.js BFF. Fixture mode is explicit, production mode
fails closed, and all tested backend failures avoid fixture fallback.

The final independent Integration Gate is **not yet ready** because frozen UI
behaviors require a separately authorized frontend-agent change: parent-mode
controls remain visible, the map does not render an explicit backend-error panel,
structured Preview metadata is not fully rendered, and the frozen university
route still derives build-time static parameters from fixture IDs. Data
correctness and transport readiness pass; the visible feature-gating, error-state,
and production static-route portions remain open.

## Architecture

- Adapter: deterministic, additive Stage 5 Warning-aware Preview Adapter
- Transport: `preview_bundle_via_next_bff`
- Bundle: standalone backend `data-pipeline/artifacts/stage5-warning-aware-preview`
- BFF: `/api/pathos/preview?endpoint=...`
- DataSource: `PreviewApiDataSource`
- Runtime boundary: `stage5-preview.schema.ts` → normalized Domain DTO
- Modes: explicit `fixture|backend`; production fixture prohibition
- Failure policy: structured error, no fallback

## Endpoint mapping

| Public contract | Next BFF mapping | Result |
| --- | --- | --- |
| `GET /api/v1/preview/manifest` | `endpoint=manifest` | Pass |
| `GET /api/v1/preview/universities` | `endpoint=universities` | 62 |
| `GET /api/v1/preview/universities/{id}` | `endpoint=university&id=...` | Pass/404 |
| `GET /api/v1/preview/region-metrics` | `endpoint=region-metrics` | blocked envelope, `records=[]`, five metric metadata rows |
| `GET /api/v1/preview/source-index` | `endpoint=source-index` | Pass |
| `GET /api/v1/preview/status-dictionary` | `endpoint=status-dictionary` | Pass |
| `POST /api/ai/context` | `/api/ai/context` | Disabled, 503, non-retryable |

## Data semantics

- `view=preview`; production eligibility remains false.
- 62 unique Summary IDs and 62 Detail files.
- 904 verified Stage 4B/4C records consumed.
- 12 national ranks remain null and are excluded from numeric filters.
- Rank-zero and null-island counts are zero.
- 9 SAT and 9 ACT records remain `not_reported`.
- Test policy and English policy remain `pending_external_access`.
- Enrollment uses 2019 with `stale_reference_year`; Harvey Mudd and Olin keep
  graduate/total null.
- 16 schools retain county-only scope; nearest towns are not substituted as place.
- 130 people gaps retain `source_review_not_completed` and `数据补充中`.
- Detail carries 4,693 reviewed/source-limited all-major rows; search covers
  region, top programs, and all majors without putting the complete list in Summary.
- Eleven all-major gaps remain `not_reported` with their original null reason;
  source-limited rows remain explicitly source-limited in Domain metadata.
- Source Index has no synthetic `Frozen PathOS source` placeholders; every
  referenced source retains publisher, type, scope, year/status metadata.
- Quarantined/live-invalidated people are not exposed.
- Region metrics contain no facts; choropleth eligibility is false.
- AI verified context, international applicant section, and parent mode are false.

## Verification

- Backend Stage 5: 45/45
- Full Python discovery: 393 run; 279 pass; 114 historical cache-dependent
  errors/failures because prohibited untracked cache bodies are absent
- Committed Stage 4B/4C validator results: 60/60 and 86/86 unchanged
- Live Stage 4B/4C validator replay: unavailable without prohibited cache bodies
- Frontend Stage 5: 38/38
- Frontend total: 58/58
- TypeScript: pass
- Lint: pass with eight pre-existing frozen-page warnings
- Production build: pass
- Production build static paths: build succeeds, but frozen
  `src/app/university/[id]/page.tsx` still imports fixture IDs for
  `generateStaticParams`; runtime `dynamicParams=true` serves Candidate v2 IDs
- Real Bundle BFF smoke: pass
- Desktop browser routes: `/map`, `/calculator`, `/match`, `/assessment`,
  `/portfolio`, and multiple `/university/[id]` cases pass without framework
  overlays
- Detail cases: ranked Harvard; not-in-scope/SAT-ACT-not-reported Arizona State;
  partial-enrollment Harvey Mudd; county-only Boston College
- Mobile overflow smoke: pass
- Console: no application errors; one development-only Fast Refresh warning after edits
- Failure instance: backend 503, no fixture school rendered

## Open gate items

| Severity | Item | Owner |
| --- | --- | --- |
| High | Hide/disable parent-mode controls when readiness is false | Frontend agent; prohibited map component |
| High | Render explicit backend-error UI instead of persistent loading shell | Frontend agent; prohibited map component |
| High | Replace fixture-derived `generateStaticParams` with a backend-safe strategy | Frontend agent; prohibited university route |
| Medium | Render structured admissions/enrollment/gap metadata beyond warning codes | Frontend agent; prohibited university component |

No Critical data-integrity, contract, source-resolution, or transport issue remains.
Production export is not allowed.
