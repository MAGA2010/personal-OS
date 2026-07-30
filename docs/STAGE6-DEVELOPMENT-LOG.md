# PathOS Stage 6 Development Log

## Closing Runtime Lifecycle Patch — Pre-change Record

Date: 2026-07-25

Scope:

- H-1 runtime process-group identity binding
- Runtime test portability when `rg` is absent
- Root Stage 6 Demo Freeze Manifest

Explicitly excluded:

- Frontend UI and `frontend/src/`
- Preview Adapter and Preview Bundle
- Stage 4B/4C/5 artifacts and data facts
- Fixture or production export behavior
- Old Git source and linked backend writes

Backend checkpoint:

- Branch: `feature/stage6-demo-freeze-operational-readiness`
- HEAD: `b73e61ec4fda11b7c72e74c14e414fbe2c74300f`
- Worktree: clean
- Initial service state: `STOPPED`

Pre-change SHA-256:

| File | SHA-256 |
|---|---|
| `pathos-demo` | `a6879280e8d437d69675fb19a04b91263f64e244fdbab80e6211d6ffde6b3aa6` |
| `scripts/pathos-ops.mjs` | `7e3a996bed8548ba507421d5362e968a098a45215360a4357a3ac714adf0280d` |
| `scripts/pathos-process.mjs` | `9aee35dfc46d8c08ffb800db244dee4a4221785886075fffd17a6f04be1c9632` |
| `scripts/tests/process-health.test.mjs` | `d6af43b391390df7d440e58421a9236288ade62fc293d7a325aeba2e28d430a6` |
| `scripts/tests/stage6-demo-tests.sh` | `7b5f2bf9febc07adf7ae209c970ff8a0bb99d8e81629f1a459952aebe411852f` |
| `scripts/tests/freeze-reuse.test.sh` | `6983853b9018dd2efbb68eb32de35c7ab1c4529c7b6ae26dee44bf7bf2dfc0f1` |
| `docs/STAGE6-DEMO-CHANGE-MANIFEST.json` | `39784afc3d624cf7a19589ca3674e687534886795cb8b682ef4ca29ed657853c` |
| `docs/STAGE6-DEMO-FREEZE-REPORT.md` | `2a69a820e6a949e4dfcd5f2e8973808c551cc95a2a1bb113d71805f1f2b88618` |
| `docs/STAGE6-DEMO-RUNBOOK.md` | `fe6fe4149d50bd59f8188188f2f1370083da02d562ccaa8f4d1b47a649cc7276` |

Pre-change Preview artifact anchors:

| File | SHA-256 |
|---|---|
| `manifest.json` | `88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2` |
| `universities.json` | `b67e0da07525e5204a90c27fd2d8b31d301c66cd11b9df89e2da1be4efaa803f` |

Root-cause hypothesis to test:

The listener is rejected because runtime admission compares its actual PGID to
the controller PID instead of the controller's OS-reported PGID. A valid
controller/listener tree can therefore fail when the controller is not the
process-group leader. The fix must bind both identities to the recorded actual
PGID without accepting arbitrary listeners.

## Root-cause Evidence

Local pre-change process evidence:

```text
controller PID=86773 PGID=86773 command=npm run start
listener   PID=86791 PGID=86773 command=next-server
```

Gate evidence:

```text
controller PID=86016 PGID=86014
listener   PID=86035 PGID=86014
```

The listener is valid because both processes belong to recorded PGID 86014;
comparing listener PGID to controller PID 86016 is invalid.

Two additional lifecycle defects were exposed by real regression:

1. npm rewrites its visible command title without changing PID/PGID/start time.
2. After the starting control process exits, npm is safely reparented to PID 1.
3. Negative PGID existence checks cannot reuse a helper that rejects negative PID values.

## Closing Implementation

- Direct `spawn("npm", args, { detached: true, shell: false })`.
- State schema v2 records controller PID, actual PGID, start time, command, cwd,
  listener PID/identity, port, backend mode, Bundle and log paths.
- Listener admission uses recorded actual PGID, trusted Next.js command, cwd,
  port ownership and start time.
- Stop revalidates the controller, listener and process group before SIGTERM.
- SIGKILL is permitted only when every remaining group member is still in the
  same PGID, frontend cwd and trusted npm/Next.js command class.
- Tests use an isolated runtime root and never kill an unverified process.
- Runtime content scanning now uses Node.js and has no `rg` dependency.
- Doctor verifies process identity tooling before spawn.
- A launch guard is bound to the exact `detached: true`, `shell: false`
  ChildProcess group before controller admission. It is used only to clean a
  failed launch; normal state and listener admission still require the
  OS-reported PGID.

## Lifecycle Evidence

- Pure/runtime identity checks: PASS
- Detached controller/listener PGID: PASS
- Three consecutive start/status/12-check Smoke/stop rounds: PASS
- Repeated start and stop: PASS
- Foreign port preserved; alternate port selected: PASS
- PID reuse mismatch rejected without kill: PASS
- Forced startup failure orphan cleanup: PASS
- Missing `ps` prevents npm spawn: PASS
- Post-preflight identity probe failure removes both the test controller and
  its same-group child while preserving an external sentinel: PASS
- Verified stubborn PGID SIGKILL fallback: PASS
- Restart and one-command demo: PASS
- Final service state: STOPPED
- Residual listener/npm/next-server: 0

## Unicode Path Compatibility Closing Patch — Pre-change Record

Date: 2026-07-25

Scope:

- H-1-CONT: strict decoding and canonical comparison of macOS `lsof -Fn`
  cwd fields in a Unicode workspace.
- M-1: bind the root freeze manifest to the final post-closing inventories
  without a recursive self-hash.

Backend checkpoint:

- Branch: `feature/stage6-demo-freeze-operational-readiness`
- HEAD: `b73e61ec4fda11b7c72e74c14e414fbe2c74300f`
- Worktree: clean
- Initial managed service state: `STOPPED`

Pre-change SHA-256:

| File | SHA-256 |
|---|---|
| `pathos-demo` | `a6879280e8d437d69675fb19a04b91263f64e244fdbab80e6211d6ffde6b3aa6` |
| `scripts/pathos-ops.mjs` | `7279eb1f3a496667b706256babbc35575a20cb5a6e148a14ad7563cd3171c6e2` |
| `scripts/pathos-process.mjs` | `9aee35dfc46d8c08ffb800db244dee4a4221785886075fffd17a6f04be1c9632` |
| `scripts/tests/runtime-lifecycle.test.mjs` | `44aa4879b3e53039628ace2c2d664a0c319a3ed55c581ae41d142ede9b305591` |
| `scripts/tests/runtime-lifecycle-integration.sh` | `2b6f7b1127128b8e53213344faafa4c111363f6e47bff01fdcc53114a6de85c0` |
| `scripts/tests/prestate-cleanup.test.sh` | `64223816509d2dd12fd193af5c993e84f3bf22f7969eec46cadfee0f925e497d` |
| `scripts/tests/process-health.test.mjs` | `d6af43b391390df7d440e58421a9236288ade62fc293d7a325aeba2e28d430a6` |
| `scripts/tests/freeze-reuse.test.sh` | `6983853b9018dd2efbb68eb32de35c7ab1c4529c7b6ae26dee44bf7bf2dfc0f1` |
| `scripts/tests/no-rg-portability.test.sh` | `76f6c138ac7815d92e7cae5ab07437602c39b0fe608a79dc4e3397cbfbb76ff4` |
| `scripts/tests/stage6-demo-tests.sh` | `236773038f9b4de2f138b481cedb0607854b23b76084fe76d50d9c9e917d104d` |
| `STAGE6-DEMO-FREEZE-MANIFEST.json` | `e82e95b4b10d3725bf2ab2cc5207ca34447be04ed93535766dcfe0457d949aac` |
| `docs/STAGE6-DEMO-CHANGE-MANIFEST.json` | `78d2e2c810b683d212485e732f4cef22dfb12ee1f803bf162316cf4a4d757819` |
| `docs/STAGE6-CLOSING-RUNTIME-CHANGE-MANIFEST.json` | `3976b5f2547f5e77bcc8c6cdf4fa767cc79c12dd7773fade8f399588d470b8d0` |
| `docs/STAGE6-DEMO-FREEZE-REPORT.md` | `577ed292fac8e2b3e189897c2daa44fd257050acb5d96bf3f62fa5b29561b50d` |
| `docs/STAGE6-DEVELOPMENT-LOG.md` | `85052a555b43ed96ffb59b45caa54d133516b7be43dc9c5acdb8a407818ab32b` |
| `docs/STAGE6-DEMO-RUNBOOK.md` | `8927dabda2ec1ded09a34b0530b6bd61501a607a99fb597a0dd57052b5b80b39` |

Frontend source tree anchor:

- Algorithm: sorted relative path + NUL + bytes + NUL
- Files: 73
- SHA-256: `63689c3cbf9ee8d2c393b11f76ce6ba37217d916dcf4f77be7beb4aa702d891c`

Root-cause evidence from a controlled process whose cwd is the real frontend:

```text
UTF-8 locale:
p56439
fcwd
n/Users/jiayihuang/Downloads/PathOS合并/PathOS-main/frontend

C locale:
p56472
fcwd
n/Users/jiayihuang/Downloads/PathOS\xe5\x90\x88\xe5\xb9\xb6/PathOS-main/frontend
```

The existing parser strips only the leading `n`; it leaves the six escaped
UTF-8 bytes as literal text. Strict equality against the real frontend path
therefore fails.

External port protection anchor:

- Port: 3000
- PID: 55637
- PGID: 55617
- Start time: `Sat Jul 25 13:43:10 2026`
- Command: `next-server (v14.2.35)`
- Ownership: external; this patch must not signal, stop or adopt it.

## Unicode Path Closing Implementation and Evidence

`scripts/pathos-ops.mjs` now exports and tests:

- `decodeLsofEscapedUtf8`: exact `\xNN` bytes plus ordinary UTF-8 text are
  concatenated and decoded once with `TextDecoder("utf-8", { fatal: true })`.
- `canonicalizeIdentityPath`: strict decode, NFC, absolute `path.resolve`,
  trailing-separator normalization and `fs.realpathSync.native`, followed by NFC.
- `identityPathsEqual`: canonicalizes both operands and returns false on any
  decoding or realpath failure.
- `parseLsofCwd`: accepts only the `fcwd` / `n...` field pair and canonicalizes it.

All controller/listener cwd checks use the same strict comparison. PID, PGID,
start-time, command and port checks are unchanged.

TDD RED evidence:

- Unicode unit tests initially failed because the decoder/canonicalizer exports
  did not exist.
- Root binding test initially failed because the Unicode Closing manifest did
  not exist.
- Demo CLI test initially failed because demo output omitted the Runbook path.

TDD GREEN and integration evidence:

- Unicode path unit matrix: PASS, including malformed escape, invalid UTF-8,
  NFC/NFD, trailing slash, path prefix, missing realpath and symlink escape.
- Real macOS lsof test in a Chinese temp directory: PASS.
- Failure injection (malformed hex, invalid UTF-8, cwd mismatch, realpath
  failure, symlink escape, listener mismatch): 6/6 PASS with no residual state,
  listener, controller or port.
- Real workspace lifecycle round 1: controller 60544, listener 60655,
  PGID 60544, port 3001, Smoke 12/12, clean stop.
- Round 2: controller 61739, listener 61855, PGID 61739, port 3001,
  Smoke 12/12, clean stop.
- Round 3: controller 62941, listener 63051, PGID 62941, port 3001,
  Smoke 12/12, clean stop.
- Every raw cwd contained `PathOS\xe5\x90\x88\xe5\xb9\xb6`; every decoded and
  canonical cwd exactly matched the real frontend root.
- External PID 55637 on port 3000 remained present and was never signalled.
- Restart PASS; demo PASS; final managed state STOPPED.

One transient runtime Smoke failure was traced to concurrent `next lint` and
other frontend commands mutating `.next`. A serial `npm run build` restored the
expected dynamic university route; the lifecycle suite then passed. `.next`
is neither tracked nor frozen.
