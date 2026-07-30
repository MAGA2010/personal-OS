# PathOS Stage 6 Closing Runtime Lifecycle Patch Report

## Conclusion

Status: `READY FOR FOCUSED STAGE 6 CLOSING RUNTIME LIFECYCLE RE-GATE`

- Critical: 0
- High: 0
- Blocking Medium: 0
- UI change: false
- Data semantics change: false
- Preview Adapter change: false
- Preview Bundle change: false
- Production data export generated: false

## H-1 Root Cause and Fix

The previous admission rule compared the listener PGID to the spawned npm PID.
This is invalid when the OS-reported controller PGID has another leader:

```text
Gate controller PID=86016 PGID=86014
Gate listener   PID=86035 PGID=86014
```

The runtime now:

1. directly spawns npm with `detached: true` and `shell: false`;
2. reads the controller's actual PID, PPID, PGID, start time, command and cwd;
3. records the actual PGID instead of deriving it from the controller PID;
4. accepts the listener only when its OS-reported PGID equals the recorded PGID;
5. requires backend mode, the exact Preview Bundle path, a trusted Next.js
   command, frontend cwd, exact port ownership and stable start time;
6. allows only the expected npm command-title transition and controller
   reparenting from the recorded PPID to PID 1;
7. rejects PID reuse, foreign listeners and unsafe/current-controller PGIDs;
8. verifies process identity tooling before spawn and binds an exact,
   failure-only launch guard to the `detached: true`, `shell: false` child
   group before controller admission.

The launch guard is not persisted as runtime truth and cannot admit a listener.
If controller identity discovery fails after preflight, it terminates only the
group created by that still-bound ChildProcess. This removes both npm and any
same-group child without touching an external sentinel.

## Safe Stop

Before SIGTERM, stop revalidates:

- runtime state schema and workspace scope;
- controller PID, PGID, start time, command class and cwd;
- listener PID, PGID, parent, start time, command class, cwd and port;
- `dataMode=backend`;
- process group exists and is neither 0, 1 nor the current control group.

SIGTERM is sent only to the validated negative PGID. If the group remains,
SIGKILL is allowed only when every remaining process is re-enumerated and still
has the same PGID, frontend cwd and trusted npm/Next.js command class.

EPERM continues to mean “process/group exists but is permission restricted.”
No `pkill`, `killall`, fuzzy command matching or broad Node termination is used.

## Runtime State

State schema: `pathos-demo-runtime-v2`

`status --json` exposes:

```text
status, controllerPid, listenerPid, pgid, port, url, dataMode,
bundlePath, uptime, logPath, identityVerified
```

Supported states:

- `RUNNING`
- `STARTING`
- `STOPPED`
- `STALE_STATE`
- `IDENTITY_MISMATCH`
- `PORT_OWNED_BY_FOREIGN_PROCESS`

No secret is written to runtime state.

## Test Coverage and Lifecycle Evidence

Pure and OS process-group tests:

- Gate topology with controller PID different from PGID: PASS
- listener PID different from controller PID: PASS
- listener same recorded PGID: accepted
- listener different PGID: rejected
- npm command-title transition: PASS
- controller safe reparenting to PID 1: PASS
- unsafe/current-controller PGID rejection: PASS
- negative PGID existence and EPERM semantics: PASS
- real detached controller/child process group: PASS

Three consecutive real lifecycle rounds:

- start: 3/3 PASS
- repeated start reuses the same controller: 3/3 PASS
- status: 3/3 `RUNNING`, identity verified
- Smoke: 3/3, 12/12 each
- stop: 3/3 PASS
- repeated stop: 3/3 safe
- released ports: 3/3
- residual npm/next-server: 0

Additional lifecycle cases:

- external port owner preserved: PASS
- alternate port selected: PASS
- foreign listener classified: PASS
- stale/PID-reused identity rejected without kill: PASS
- forced startup failure leaves no controller, child or state: PASS
- missing process identity tooling blocks before npm spawn: PASS
- post-preflight identity failure removes controller and child, preserves an
  external sentinel, and leaves no state: PASS
- stubborn verified PGID SIGKILL fallback: PASS
- restart: PASS
- one-command demo: PASS
- final state: `STOPPED`

## Portability

Stage 6 content scanning now uses Node.js. The Stage 6 test suite passes with
`rg` absent from `PATH`; ripgrep is not a Demo runtime dependency.

## Root Freeze Manifest

Created:

`/Users/jiayihuang/Downloads/PathOS合并/STAGE6-DEMO-FREEZE-MANIFEST.json`

It binds:

- workspace/frontend/backend checkpoint;
- Preview contract, dataset and 62/62/62/904 counts;
- Bundle manifest and artifact hash map;
- Stage 5 PASS frontend freeze and archive;
- `pathos-demo` and all Stage 6 scripts;
- startup, Smoke and stop commands;
- disabled features and Preview-only data boundaries.

It contains no secret, token, cookie, `.env.local` content or cache body.

## Full Verification

- Doctor: 41/41 PASS
- Stage 6 CLI contract tests: 8/8 PASS
- Tests without `rg`: PASS
- Frontend TypeScript: PASS
- Frontend lint: PASS with 8 unchanged warnings
- Frontend tests: 76/76 PASS
- Frontend build: PASS
- `/university/[id]`: dynamic
- Stage 5 backend tests: 49/49 PASS
- Stage 5 validator: 49/49 PASS
- deterministic generation: PASS
- network-disabled generation: PASS
- Backend `git diff --check`: PASS
- Backend worktree: clean

Browser:

- Desktop and 390×844 mobile: PASS
- `/map` and `/map?mode=parent`: parent safely degrades to student
- Harvard, Arizona State, Harvey Mudd and Boston College: PASS
- unknown university: safe 404
- fixture fallback: none
- unsafe sentinels: none
- Console application errors: 0

## Independent Focused Review

The final read-only review reproduced both pre-state failure windows and then
verified their closure. Final verdict: Critical 0, High 0. It confirmed that
the launch guard is failure-only, does not enter runtime state or listener
admission, cleans a TERM-resistant same-group child, and preserves an external
sentinel.

## Integrity

Unchanged:

- Backend HEAD `b73e61ec4fda11b7c72e74c14e414fbe2c74300f`
- Preview manifest SHA-256
  `88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`
- Universities SHA-256
  `b67e0da07525e5204a90c27fd2d8b31d301c66cd11b9df89e2da1be4efaa803f`
- Frontend UI and `frontend/src/`
- Stage 4B/4C/5 artifacts and verified facts
- Candidate v2, ranking memberships, Stage 3D people and fixture

Old Git source and linked backend were not modified. No push, tag, reset,
clean, rebase or historical cache recovery was performed.
