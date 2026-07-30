# PathOS Stage 6 Demo Freeze 实现计划

> **面向 AI 代理的工作者：** 在当前会话内执行本计划。所有运行时控制必须默认使用真实 backend Preview Bundle；不得修改 UI 或数据事实。

**目标：** 将 Stage 5 PASS checkpoint 冻结为可用单一命令诊断、启动、停止、检查、冒烟测试和恢复的本地 Demo。

**架构：** 工作区根目录提供 `pathos-demo` 稳定入口，模块化 shell wrapper 统一启用严格模式，Node.js 运维核心负责无当前目录依赖的诊断、进程状态和 HTTP Smoke。Stage 5 前端 PASS 通过外部、确定性快照保存；Stage 6 change manifest 只记录运维文件，不触碰前端 UI 和后端数据。

**技术栈：** Bash、Node.js 20、Next.js 14、npm、SHA-256、deterministic tar/gzip、Vitest、Python Stage 5 validators。

---

## 文件职责

- `pathos-demo`：用户唯一入口和命令分发。
- `scripts/pathos-lib.sh`：shell wrapper 共用的根目录解析和 Node 调用。
- `scripts/pathos-ops.mjs`：doctor、start、stop、status、smoke、open 和 demo 的运维核心。
- `scripts/pathos-{doctor,start,stop,status,smoke,freeze-check}.sh`：严格模式模块接口。
- `scripts/pathos-freeze-stage5.mjs`：创建或校验 Stage 5 PASS 确定性前端快照。
- `scripts/tests/stage6-demo-tests.sh`：Stage 6 CLI 合同、Bundle 事实和 fail-closed 回归测试。
- `docs/STAGE6-DEMO-RUNBOOK.md`：正常演示流程。
- `docs/STAGE6-DEMO-RECOVERY-RUNBOOK.md`：端口、进程、构建、Bundle 和错误恢复。
- `docs/STAGE6-DEMO-FREEZE-REPORT.md`：验证证据和 Gate 交接。
- `docs/STAGE6-DEMO-CHANGE-MANIFEST.json`：Stage 6 变更与保留 harness 审计。

### 任务 1：Preflight 与分支

- [x] 验证 standalone 后端 HEAD 为 `b73e61ec4fda11b7c72e74c14e414fbe2c74300f`。
- [x] 验证 Stage 5 分支、clean worktree、自包含 `.git` 和 Closing Patch SHA。
- [x] 验证 Preview manifest 的 62/62/62、904、Preview flags 和 disabled features。
- [x] 创建 `feature/stage6-demo-freeze-operational-readiness`，不 reset、rebase、push 或 tag。

### 任务 2：先写 CLI 合同测试

- [ ] 创建测试，断言 9 个公开命令、严格 shell 模式、backend 默认模式、禁止 fixture、doctor JSON 字段、Bundle 计数与错误退出码。
- [ ] 运行测试并确认因 Stage 6 CLI 尚不存在而失败。
- [ ] 保留失败输出到 Stage 6 报告的 TDD 证据中。

### 任务 3：实现只读 doctor

- [ ] 实现不写入 runtime 目录的 `doctor` 和 `doctor --json`。
- [ ] 检查工作区、后端 checkpoint、clean 状态、Bundle、contract、62/62/62、904、Preview flags、禁用功能、Node/npm、lockfile、依赖、`.env.local`、端口、临时目录、Stage 5 PASS freeze 和旧仓库运行时依赖。
- [ ] 固定退出码：0=PASS，1=FAIL，2=WARN。
- [ ] 运行合同测试，确认 doctor 部分转绿。

### 任务 4：创建 Stage 5 PASS 前端快照

- [ ] 以稳定文件顺序收集 `src/`、`docs/`、`public/` 和运行配置，排除 secret、cache、build、日志与截图。
- [ ] 生成 snapshot tree、JSON manifest、SHA-256 清单、固定 metadata 的 tar.gz 和报告。
- [ ] 对已有同名快照只校验不覆盖；内容不一致时使用带序号目录。
- [ ] 再运行 doctor，确认 freeze check 通过。

### 任务 5：实现进程生命周期

- [ ] `start` 在 backend 模式下注入 Bundle 路径；端口 3000 占用时选择安全备用端口；缺 build 时确定性构建。
- [ ] `status` 同时核对 PID、HTTP manifest 和运行模式。
- [ ] `stop` 只终止由 Stage 6 状态文件记录且命令身份匹配的进程组。
- [ ] `restart` 组合安全 stop/start；异常时不得遗留失控进程。
- [ ] `open` 打开已记录 URL；`demo` 顺序运行 doctor、start、smoke 和 status。

### 任务 6：实现自动 Smoke

- [ ] 验证 manifest、62 条 summary、有效 detail、未知 ID 404、`/map` 和动态 university 页面。
- [ ] 验证 ID 唯一、verified=904、quarantine=0、无 `[0,0]`、rank 0 和 fixture fallback。
- [ ] 若服务未运行，Smoke 临时启动并在结束时只停止自己创建的实例。
- [ ] 测试恢复后再次 Smoke，确认状态文件和服务可重复使用。

### 任务 7：Runbook、恢复和审计

- [ ] 写正常演示、演示前 5 分钟检查、关键路线、关闭流程。
- [ ] 写端口占用、stale PID、陈旧 `.next`、缺依赖、Bundle 缺失/损坏、错误页面和外部地图网络依赖恢复步骤。
- [ ] 记录 `.claude/launch.json` 为保留的测试 harness，不作为真实数据模式来源。
- [ ] 生成相对路径、before/after SHA、角色、数据语义变化=false 的 Stage 6 change manifest。

### 任务 8：完整验证

- [ ] 运行 Stage 6 CLI 测试。
- [ ] 运行 `doctor` 与 `doctor --json`。
- [ ] 运行 `start/status/smoke/stop` 和自动端口恢复场景。
- [ ] 运行 TypeScript、lint、76 项以上前端测试和 backend-mode build。
- [ ] 运行 Stage 5 backend tests、validator 与 deterministic/network-disabled generation。
- [ ] 浏览器检查 `/map`、有效学校、特殊学校、未知 ID、断开与恢复；检查 Console。
- [ ] 运行 freeze-check 和 change-manifest SHA 校验。
- [ ] 确认后端数据与 UI 无变更、无 production export、无 push/tag、旧目录未写入。
