# PathOS Stage 5 Closing UI Compliance Patch Plan

## Scope

This patch closes only the three High findings from the Stage 5 Integration Gate:

1. Parent Mode remains visible or reachable while backend Preview readiness disables `parent_mode`.
2. Map and university routes do not present a sufficiently explicit, safe error state after backend failure.
3. `/university/[id]` still imports fixture IDs through `generateStaticParams`.

The user has granted a one-time exception for the minimum frozen UI files that directly own these behaviors.

## Before-state evidence

| File | Start-of-patch SHA-256 | Baseline SHA-256 |
|---|---|---|
| `src/components/map/MapShell.tsx` | `71e0aed9bd53643d4670f802cae3faf74554b5090b5764bcd1a7e63db9d2b069` | same |
| `src/components/university/UniversityDetailView.tsx` | `aab9921ea3eec2d118dd2c97be9a08694b56f84c4026a0a0e56312995de0037f` | same |
| `src/components/shared/data-states.tsx` | `9880581ccac945966943806d6475ffb1f2619ac834ef06ebc2bde8328b7023de` | same |
| `src/app/university/[id]/page.tsx` | `8a4d5f216228bc977e83f8c4294102e4e67136540bb7d0e022a1705d4743d59c` | same |
| `src/domain/dataset.ts` | `d312788bbaf584a46ae63ecd73c7e9ae1cd8faa19526f47fae15fd869fe5beac` | `0b9beacd57961b91b33b30177f9f3f346b68c156d6231c650b64c822d9dc3c4e` |
| `src/schemas/dataset.schema.ts` | `5fb3624b1e1f79ebf44a0207fbc72a180d8d713a2df074cb613c29afa5039d06` | `81638f19a1f2d0b4722aa60ef300cc68742b03bc19395fba359c637803af5ad8` |
| `src/hooks/use-view-state-bridge.ts` | `114774533fc6f57274f89f00155922740e89fcb9970224ba99cec61dde22acdd` | same |
| `src/hooks/use-data-source.ts` | `9bdb73c7b0a535dd8f1996a4e13187f835518f3d89cdf7ee6b7e60e84883a03c` | same |
| `src/services/preview-api-data-source.ts` | `5bfdb5b44e5a7bef20086cea18d0def21123cdd9b580fa0b0d039b6b5bf5deed` | `6280497d91f43e170028ecfb4fc3d94668dc327979874349bc6bc491ef6822fa` |
| `src/server/backend-preview.ts` | `f58a82e3afebaa8dda6b9c14e7402798af5798d75eca3c35b35c008ca8c34e5c` | not present |

## Minimal file plan

### High 1 — Parent readiness gating

- Modify `src/domain/dataset.ts` and `src/schemas/dataset.schema.ts` to retain manifest `enabledFeatures` and `disabledFeatures`.
- Modify `src/hooks/use-view-state-bridge.ts` to expose a pure allowed-mode resolver and safely coerce persisted `parent` state to `student` when parent readiness becomes false.
- Modify frozen `src/components/map/MapShell.tsx` to load the real manifest, hide the toggle until readiness is known, hide it when `parent_mode` is disabled, and pass readiness to the URL-state bridge.

This leaves fixture behavior enabled when its legacy manifest does not disable parent mode, keeps Student Mode available, and avoids hard-coding backend facts.

### High 2 — Explicit backend error presentation

- Modify `src/services/preview-api-data-source.ts` to preserve safe machine-readable BFF codes while never exposing response bodies to UI.
- Modify `src/server/backend-preview.ts` to scope university-not-found conversion to the Detail file only; missing shared Bundle dependencies remain Bundle errors.
- Modify frozen `src/components/shared/data-states.tsx` to add one small reusable error-state policy/component using existing colors, spacing, and wording.
- Modify frozen `src/components/map/MapShell.tsx` and `src/components/university/UniversityDetailView.tsx` to render that state and retry the same backend request.

The success layout is unchanged. Backend errors remain fail-closed and cannot show fixture universities.

### High 3 — Dynamic university route

- Modify frozen `src/app/university/[id]/page.tsx`.
- Use方案 A because `next.config.mjs` has no `output: "export"` and the project already requires a server runtime for BFF routes.
- Remove the fixture import and `generateStaticParams`; mark the route `force-dynamic`.

No remote API or Bundle parsing occurs in the page component, and runtime detail continues through the existing DataSource.

## TDD sequence

1. Add `src/test/unit/stage5-closing-ui.test.ts`.
2. Verify red failures for:
   - readiness parsing and parent-to-student coercion;
   - safe error classification and BFF machine code preservation;
   - dynamic route having no fixture/static-param dependency;
   - real Bundle retaining 62 unique IDs and failing closed for missing/unsupported Bundle inputs.
3. Implement only the code needed to pass.
4. Run the closing tests, then all existing frontend tests.

## Verification

- `npx tsc --noEmit`
- `npm run lint`
- `npm run test`
- backend-mode `npm run build`
- Stage 5 backend 49-test suite
- Stage 5 deterministic/network-disabled regeneration
- browser checks for success, failure, 404, persisted parent URL state, desktop and mobile

## Explicitly out of scope

- Adapter, Bundle facts, Stage 4B/4C, Candidate v2, rankings, Stage 3D people.
- Fixture contents.
- Map controls, Compare, Search, layout, responsive rules, Tailwind design system, public trust semantics.
- Historical cache-dependent Python replay.
- Production export.
