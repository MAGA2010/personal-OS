# PathOS Stage 6 Unicode Path Compatibility Closing Patch Report

Date: 2026-07-25
Scope: H-1-CONT and M-1 only
Result: PASS — ready for final focused Stage 6 Re-Gate

## Outcome

The macOS `lsof -Fn` cwd path is now decoded as UTF-8 bytes and compared only
after strict canonicalization of both operands. Cwd, PID, PGID, start time,
command, listener and port identity checks remain fail closed. The Root Freeze
Manifest now binds the final cumulative, Closing Runtime and Unicode Closing
inventories without a recursive hash dependency.

No frontend source, UI, backend tracked file, Preview Adapter, Preview Bundle,
Stage 4B/4C/5 artifact, fixture or data fact changed.

## H-1-CONT Evidence

Representative raw controller/listener lsof field from the real workspace:

```text
n/Users/jiayihuang/Downloads/PathOS\xe5\x90\x88\xe5\xb9\xb6/PathOS-main/frontend
```

Decoded and canonical cwd:

```text
/Users/jiayihuang/Downloads/PathOS合并/PathOS-main/frontend
```

Canonical frontend root:

```text
/Users/jiayihuang/Downloads/PathOS合并/PathOS-main/frontend
```

The values match exactly. `\xNN` tokens are accumulated as bytes, ordinary text
is UTF-8 encoded, and the combined buffer is decoded once with
`TextDecoder("utf-8", { fatal: true })`. Both sides then use NFC,
`path.resolve`, trailing-separator normalization and `fs.realpathSync.native`,
followed by NFC again.

Malformed hex, truncated escape, invalid UTF-8, missing path, cwd mismatch,
realpath failure, symlink escape and listener-only mismatch fail closed.
No `includes`, `endsWith`, basename or prefix matching was introduced.

## Real Unicode Workspace Lifecycles

External port 3000 owner remained PID 55637 throughout. PathOS selected port
3001 and never signalled or adopted the external process.

| Round | Controller | Listener | Recorded/controller/listener PGID | Start | Identity | Smoke | Stop | Residual |
|---|---:|---:|---|---:|---|---|---:|---|
| 1 | 86766 | 86876 | 86766 / 86766 / 86766 | 0 | verified | 12/12 | 0 | none |
| 2 | 87974 | 88084 | 87974 / 87974 / 87974 | 0 | verified | 12/12 | 0 | none |
| 3 | 89168 | 89278 | 89168 / 89168 / 89168 | 0 | verified | 12/12 | 0 | none |

Each raw cwd contained the escaped Chinese bytes. Each decoded controller cwd,
decoded listener cwd and canonical frontend root matched exactly. Every stop
released 3001 and left no managed controller, npm or next-server process.

Restart passed with controller 91114 / listener 91224 / PGID 91114 and Smoke
12/12. `./pathos-demo demo` passed doctor, start, Smoke 12/12 and status; it
printed both the actual URL and the Stage 6 Runbook. Final managed status is
`STOPPED`.

## Automated Regression

- Unicode unit and topology matrix: PASS.
- Real macOS lsof Unicode integration: PASS.
- Unicode failure injection: 6/6 PASS.
- Runtime identity unit test: PASS.
- Runtime lifecycle integration: PASS, including three rounds, foreign port,
  stale PID, startup cleanup and verified SIGKILL.
- Process health: PASS.
- Prestate cleanup: PASS.
- Freeze reuse: PASS.
- Stage 6 CLI: 9/9 PASS.
- No-rg PATH: PASS.
- Doctor: 40 PASS, 1 expected external-port warning, 0 FAIL.
- Doctor JSON: valid and read only.

## Frontend, Backend and Browser

Frontend:

- TypeScript: PASS.
- Lint: PASS with 8 unchanged warnings.
- Vitest: 76/76 PASS.
- Build: PASS.
- `/university/[id]`: dynamic server route.
- Frontend source tree: 73 files,
  `63689c3cbf9ee8d2c393b11f76ce6ba37217d916dcf4f77be7beb4aa702d891c`
  using bytewise-sorted relative path + NUL + file bytes + NUL.

Backend:

- Stage 5 tests: 49/49 PASS.
- Stage 5 validator: 49/49 PASS.
- Deterministic generation: PASS.
- Network-disabled generation: PASS.
- Stage 4B frozen validator: 60/60 PASS.
- Stage 4C frozen validator: 86/86 PASS.
- Git diff check: PASS.
- Worktree: clean at
  `b73e61ec4fda11b7c72e74c14e414fbe2c74300f`.

Browser, backend mode on port 3001:

- Desktop: `/map`, `/map?mode=parent`, Harvard, Arizona State, Harvey Mudd,
  Boston College and nonexistent ID passed.
- Mobile 390×844: parent URL downgrade, map and Harvey Mudd passed.
- 62 schools loaded; Parent, Choropleth, AI and International stayed disabled.
- Preview warning/data supplementation states remained visible.
- ASU did not show rank 0; Harvey Mudd missing values did not become 0.
- 404 remained safe; no fixture fallback.
- No NaN, ¥0, 第 0 名, 0/100, 0:1 or `[0,0]`.
- Console application errors/warnings: 0.

## Bundle and Data Invariants

- Bundle manifest SHA-256:
  `88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`
- Universities SHA-256:
  `b67e0da07525e5204a90c27fd2d8b31d301c66cd11b9df89e2da1be4efaa803f`
- Schools/summaries/details: 62/62/62.
- Verified records: 904.
- `sourceLimited=true`, `incomplete=true`, `notFinal=true`.
- Production data export remains prohibited.

## M-1 and Final Inventory Hashes

- Root Freeze Manifest:
  `8a585fe76130493253b6b8db97ec021f891814e25d7d329255127e671fc59fc7`
- Cumulative Change Manifest:
  `b28d52dde030af9d0a0a2c67088e5e1fc1cbcc3348adc5213dac98cd51b8db87`
- Closing Runtime Change Manifest:
  `3976b5f2547f5e77bcc8c6cdf4fa767cc79c12dd7773fade8f399588d470b8d0`
- Unicode Path Closing Change Manifest:
  `8a9d5372692eaea9d2e6c2412ca0f634ba695930f4cecc43e483e3d5216497df`

The Root manifest binds all three inventory hashes above. The cumulative
inventory entries for Root, cumulative itself, Unicode Closing manifest and
this final report use `afterSha256: null`, `selfDescribing: true` and
`hashParticipation: excluded_to_avoid_recursive_binding`. The Unicode Closing
manifest applies the same rule to its Root, self and final-report entries.
Therefore no manifest claims an impossible self-hash and no hash cycle exists.

## Final Gate Answers

1. Raw lsof: `n/.../PathOS\xe5\x90\x88\xe5\xb9\xb6/PathOS-main/frontend`.
2. Decoded cwd: `/Users/jiayihuang/Downloads/PathOS合并/PathOS-main/frontend`.
3. Canonical frontend root: the same absolute path.
4. Strict match: yes.
5. `\xNN` decoding: byte-based, not per-character.
6. Strict UTF-8 decoder: yes, fatal mode.
7. Invalid UTF-8: fail closed.
8. NFC/NFD: normalized to NFC on both sides.
9. Realpath: required on both sides.
10. Strict cwd safety check: retained.
11. PGID/listener checks: unchanged and not relaxed.
12. Three starts: 3/3 PASS.
13. Three Smokes: 3 × 12/12 PASS.
14. Three stops: 3/3 PASS, no residual.
15. Restart: PASS.
16. Demo: PASS.
17. External 3000 process: preserved.
18. No-rg: PASS.
19. Unicode tests: PASS.
20. Doctor: no FAIL; one expected foreign-port WARN.
21. Frontend tests: 76/76 PASS.
22. Backend tests: 49/49 PASS.
23. Build: PASS.
24. Browser: desktop and 390×844 mobile PASS; console 0.
25. Bundle hash: unchanged, as recorded above.
26. Frontend source hash: unchanged, as recorded above.
27. Root manifest SHA: recorded above.
28. Cumulative manifest SHA: recorded above.
29. Closing Runtime manifest SHA: recorded above.
30. Unicode Closing manifest SHA: recorded above.
31. Root binds final cumulative SHA: yes.
32. Hash cycle: none.
33. Critical: 0.
34. High: 0.
35. Blocking Medium: 0.
36. Ready for final focused Re-Gate: yes.
