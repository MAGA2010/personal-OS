# PathOS Stage 6 Demo Freeze Report

## 结论

Stage 6 Closing Runtime Lifecycle Patch：
`READY FOR FOCUSED STAGE 6 CLOSING RUNTIME LIFECYCLE RE-GATE`。

- Critical：0
- High：0
- Blocking Medium：0
- 数据语义变化：false
- UI 变化：false
- Backend Adapter 变化：false
- Production data export：未生成，继续禁止

## Checkpoint

- Workspace root: `/Users/jiayihuang/Downloads/PathOS合并`
- Frontend root: `/Users/jiayihuang/Downloads/PathOS合并/PathOS-main/frontend`
- Standalone backend: `/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking-standalone`
- Read-only linked backend: `/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking`
- Old Git source: `/Users/jiayihuang/PathOS`
- Backend branch: `feature/stage6-demo-freeze-operational-readiness`
- Backend HEAD: `b73e61ec4fda11b7c72e74c14e414fbe2c74300f`
- Backend worktree: clean
- Backend commit created: false
- Push/tag: false/false

## Stage 5 PASS 前端冻结点

- Root: `/Users/jiayihuang/Downloads/PathOS合并-integration-baseline/stage5-pass-freeze`
- Entries: 96
- Mismatches: 0
- Archive SHA-256: `67b7ab7df6b8638dff56a39120402bea2e718ef95fc010f5229aad207ca86b2b`
- Deterministic metadata: file order、mtime=0、uid/gid=0、gzip mtime=0
- Secrets included: false
- `.env.local` included: false
- `node_modules/.next` included: false
- Archive content binding: 96/96 paths, sizes and SHA-256 values match the manifest
- Corrupt or wrong-content archive: fail closed; existing freeze is preserved and a numbered recovery freeze is created

`.claude/launch.json` 被明确分类为保留的本地启动 test harness；它不参与数据模式选择，也不进入 Stage 5 PASS archive。

## 运行控制

已提供：

```text
./pathos-demo doctor
./pathos-demo start
./pathos-demo stop
./pathos-demo restart
./pathos-demo status
./pathos-demo smoke
./pathos-demo open
./pathos-demo demo
./pathos-demo help
```

默认运行模式固定为 backend；未实现 fixture fallback。运行状态通过 Next.js listener PID、cwd 和监听端口三重确认。

停止服务前还会校验 PID、PGID、进程启动时间和完整命令身份；停止操作作用于已验证的独立进程组，不会终止未知进程。

Closing patch 后，controller 和 listener 都绑定操作系统实际返回的 PGID：

- 不再要求 listener PGID 等于 npm PID。
- npm command title 变化仍要求可信 npm-start 形态。
- controller 仅允许从已记录 PPID 安全重挂到 PID 1。
- listener 必须继续属于 controller 的 recorded PGID。
- PID 复用由 PID + PGID + start time 防护。
- stop 使用负 PGID；EPERM 继续表示“存在但无权限”。

## Doctor

- Result: PASS
- Passed: 41
- Warnings: 0
- Failed: 0
- Bundle artifact hashes: 70 verified
- Stage 5 freeze: 96 checked, 0 mismatches
- Old repository runtime dependency: none

机器 JSON 包含：`status`、`checksPassed`、`checksWarn`、`checksFailed`、`checks` 和三个实际 root。

## 自动 Smoke

- Result: 12/12 PASS
- Data mode: backend
- Contract: `pathos-preview-v1`
- Dataset: `stage5-preview-ec8c66e`
- Counts: 62 schools / 62 summaries / 62 details
- Verified records: 904
- Unique IDs: 62
- Valid detail: PASS
- Unknown ID: HTTP 404
- `/map`: HTTP 200
- Dynamic `/university/[id]`: HTTP 200
- Stage 5 validator: 49/49
- `[0,0]` and rank 0: 0

从 stopped 状态运行 Smoke 会自行 start，并只清理自己创建的服务。

## 端口与生命周期恢复

- Default port 3000: PASS
- 3000 occupied test: automatically selected 3001
- Status on 3001: RUNNING / healthy / backend
- Smoke on 3001: 12/12 PASS
- Safe stop: PASS
- Stopped status exit code: 1
- Early child failure detection: 64–88 ms in regression runs
- EPERM PID existence semantics: PASS
- Three consecutive full lifecycle rounds: PASS
- Repeated start reuses the same controller: PASS
- Repeated stop is idempotent: PASS
- Foreign port owner preserved: PASS
- Alternate port selection: PASS
- PID reuse protection without foreign-process kill: PASS
- Forced startup failure orphan cleanup: PASS
- Missing identity tooling blocks before npm spawn: PASS
- Post-preflight controller identity failure cleans the detached controller and
  child group while preserving an external sentinel: PASS
- Revalidated stubborn PGID SIGKILL path: PASS
- Restart: PASS
- One-command demo: PASS
- Final runtime status: STOPPED
- Residual npm/next-server/ports: 0

## Root Freeze Manifest

- Path: `/Users/jiayihuang/Downloads/PathOS合并/STAGE6-DEMO-FREEZE-MANIFEST.json`
- Path scope: `local_demo_workspace`
- Preview contract and counts: bound
- Bundle manifest and artifact map hashes: bound
- Stage 5 PASS frontend freeze: bound
- `pathos-demo` and Stage 6 script hashes: bound
- Secret / `.env.local` content / cache bodies: absent
- Production data export allowed: false

## 独立实现审查闭环

初次独立审查发现 1 个 High 和 2 个 Medium，已全部关闭：

- High：归档现已逐文件绑定 freeze manifest，并验证准确 entry set、size 与 SHA-256。
- Medium：托管服务现以 PID、PGID、启动时间、命令、cwd 和监听端口共同确认。
- Medium：测试不再删除可能对应运行中服务的 runtime state；doctor 只读性通过 before/after hash 验证。

最终审查：Critical 0、High 0、Blocking Medium 0。

Closing Runtime focused 独立复审还覆盖了 controller identity 在 doctor
之后失效的窗口：failure-only launch guard 会清理本次 detached group，
不会进入正常 listener admission，并保留外部 sentinel。最终为 Critical 0、
High 0。

## 前端验证

- TypeScript: PASS
- Lint: PASS with 8 unchanged warnings
- Vitest: 76/76 PASS
- Build: PASS
- `/university/[id]`: dynamic server route (`ƒ`)

Stage 6 未修改 `frontend/src/`、页面布局、设计、地图交互、Compare、Search、公开中文语义或 fixture 内容。

## Backend 验证

- Stage 5 backend tests: 49/49 PASS
- Stage 5 validator: 49/49 PASS
- Deterministic generation: PASS
- Network-disabled generation: PASS
- Stage 4B frozen validator: 60/60 remains PASS
- Stage 4C frozen validator: 86/86 remains PASS
- Historical cache-dependent replay: standalone clone 中仍不可运行；旧 untracked cache body 未复制，且 Stage 6 不依赖该 replay。

## Browser QA

环境：

- In-app Browser
- Desktop default viewport
- Mobile 390×844
- URL: `http://127.0.0.1:3000`

已检查：

- `/map?mode=parent` 自动变为 `mode=student`
- Parent control 不可见，student 路径正常
- Safety 指标点击后 `aria-pressed=true`
- Harvard 有效详情和 Preview 标识
- Harvey Mudd partial warning
- ASU not-reported/out-of-scope 数据路径
- Boston College county-only 路径
- 不存在 ID 显示「未找到该学校」
- 未发现 fixture 学校泄露
- 未发现 NaN、¥0、第 0 名、0/100、0:1、`[0,0]`
- Framework overlay：0
- Console error/warn：0

移动端保持 Stage 5 冻结布局；Stage 6 未进行 UI 调整。

## 数据边界

保持：

- `sourceLimited=true`
- `incomplete=true`
- `notFinal=true`
- `previewOnly=true`
- production eligibility=false
- parent mode、choropleth、international applicant、AI context disabled
- 2019 enrollment reference year + stale warning
- test/English policy 62/62 pending
- SAT/ACT 9 所 not_reported
- national rank 12 所 out of current scope
- county-only 16 所
- program-person gaps 130
- quarantine exposed=0

## Gate handoff

Stage 6 Gate 前未创建 tag。只有独立 Stage 6 Demo Readiness Gate PASS 后，才允许按单独授权创建本地 checkpoint tag。

## Unicode Path Compatibility Closing Patch

H-1-CONT 已以严格身份比较关闭。真实 C locale `lsof -Fn` 证据为：

```text
n/Users/jiayihuang/Downloads/PathOS\xe5\x90\x88\xe5\xb9\xb6/PathOS-main/frontend
```

byte-level UTF-8 解码、NFC、`path.resolve` 和 `realpath.native` 后为：

```text
/Users/jiayihuang/Downloads/PathOS合并/PathOS-main/frontend
```

该值与同样 canonicalize 的 `frontendRoot` 完全相等。非法 hex、截断 escape、
非法 UTF-8、cwd mismatch、realpath failure、symlink escape 和 listener-only
mismatch 均 fail closed；PGID 与 listener admission 未放宽。

真实中文工作区三轮 lifecycle 全部通过，均在外部 3000 listener 保持存活时选择
3001：start 0、identity verified、Smoke 12/12、stop 0、端口释放、npm/next-server
残留 0。Restart、demo、no-rg、真实 lsof Unicode 测试均通过。最终 managed
service 为 STOPPED。

M-1 通过无循环 inventory 结构关闭：Root manifest 绑定最终 cumulative、
Closing Runtime 和 Unicode Closing manifests；cumulative 中 Root、cumulative
自身和 Unicode Closing manifest 的 hash participation 明确排除，Root 自身完整
SHA-256 仅记录在 closing report。
