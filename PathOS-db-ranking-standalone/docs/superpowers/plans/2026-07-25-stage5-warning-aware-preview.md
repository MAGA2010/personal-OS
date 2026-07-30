# PathOS Stage 5 Warning-Aware Preview 实现计划

> **面向 AI 代理的工作者：** 在当前会话内逐任务执行；每个行为先写失败测试，
> 再写最小实现，验证后提交。

**目标：** 生成确定性的 62 校 Warning-Aware Preview Bundle，并让冻结前端
在显式 backend mode 中通过 Next.js BFF 消费，失败时绝不回退 fixture。

**架构：** 后端离线 adapter 从冻结 artifacts 生成 versioned Bundle；前端
BFF 按模式读取 fixture 或 Bundle，Runtime Schema/Normalizer 将 DTO 转成
现有 Domain Model。

**技术栈：** Python 3.9+、unittest、Next.js 14、TypeScript、Vitest。

---

### 任务 1：固定契约与测试入口

**文件：**
- 创建：`data-pipeline/data/stage5-warning-aware-preview/contract-mapping-matrix.json`
- 创建：`data-pipeline/tests/stage5/test_preview_adapter.py`

- [ ] 编写 mapping matrix schema/coverage 失败测试。
- [ ] 运行 `PYTHONPATH="data-pipeline/src" python3 -m unittest data-pipeline/tests/stage5/test_preview_adapter.py -v`，确认因 Stage 5 module 缺失失败。
- [ ] 创建最小 package exports，使测试进入 contract failure。
- [ ] 重跑目标测试并保持预期红灯。

### 任务 2：实现离线 loader 与 transformation

**文件：**
- 创建：`data-pipeline/src/pathos_data/stage5_preview_adapter/config.py`
- 创建：`data-pipeline/src/pathos_data/stage5_preview_adapter/loader.py`
- 创建：`data-pipeline/src/pathos_data/stage5_preview_adapter/transform.py`

- [ ] 为 62 stable IDs、来源 allowlist、status/null/warning 映射写失败测试。
- [ ] 实现 `load_stage5_inputs(repo_root)`，拒绝 raw/staging/handoff/cache body/frontend fixture。
- [ ] 实现 `build_summaries(inputs)` 和 `build_details(inputs)`。
- [ ] 验证 62/62 identity、coordinates、Summary/Detail 一致性和特殊语义。

### 任务 3：生成、校验和报告 Bundle

**文件：**
- 创建：`data-pipeline/src/pathos_data/stage5_preview_adapter/generator.py`
- 创建：`data-pipeline/src/pathos_data/stage5_preview_adapter/validator.py`
- 创建：`data-pipeline/src/pathos_data/stage5_preview_adapter/reports.py`
- 修改：`data-pipeline/src/pathos_data/__main__.py`

- [ ] 为 10 类 artifact、manifest、source resolution、determinism 写失败测试。
- [ ] 实现 `build_preview_bundle`、`write_preview_bundle` 和
  `validate_preview_bundle`。
- [ ] 增加 `stage5-warning-aware-preview --mode generate|validate` CLI。
- [ ] 两个临时目录生成并逐文件 SHA-256 对照，确认 byte-identical。
- [ ] 生成正式 artifacts/reports 并提交后端 checkpoint。

### 任务 4：前端模式与 BFF

**文件：**
- 创建：`frontend/src/server/pathos-data-mode.ts`
- 创建：`frontend/src/server/preview-bundle-reader.ts`
- 修改：`frontend/src/server/pathos-preview.ts`
- 修改：`frontend/src/app/api/ai/context/route.ts`
- 修改：`frontend/.env.local.example`
- 创建：`frontend/.env.example`
- 创建：`frontend/src/test/unit/pathos-data-mode.test.ts`
- 创建：`frontend/src/test/unit/preview-bundle-reader.test.ts`

- [ ] 写 backend/fixture 显式选择及 production fail-closed 失败测试。
- [ ] 写 Bundle success、404/500/timeout/invalid JSON/missing file/no-fallback 失败测试。
- [ ] 实现模式解析、Bundle reader、统一错误响应和 query endpoint mapping。
- [ ] backend mode AI context 返回 disabled，fixture mode 保持开发行为。

### 任务 5：Runtime Schema 与 Domain adapter

**文件：**
- 修改：`frontend/src/domain/dataset.ts`
- 修改：`frontend/src/schemas/dataset.schema.ts`
- 修改：`frontend/src/services/preview-api-data-source.ts`
- 创建：`frontend/src/test/unit/stage5-contract.test.ts`

- [ ] 使用正式 Stage 5 Bundle 写失败的真实 contract tests。
- [ ] 扩展 manifest、field wrapper、ranking/enrollment/policy/geography/people-gap 类型。
- [ ] 拒绝 duplicate ID、invalid coordinates、`[0,0]`、未知 version/status。
- [ ] 保持 legacy mapper 与页面消费者兼容。

### 任务 6：完整自动化验证

- [ ] 运行 Stage 5 adapter tests/validator/deterministic/network-disabled。
- [ ] 运行 Stage 4B 60/60 与 Stage 4C 86/86。
- [ ] 运行完整 Python tests 和 schema/migration validation。
- [ ] 运行 `npx tsc --noEmit`、`npm run lint`、`npm run test`、`npm run build`。
- [ ] 对失败执行 systematic debugging，修复后重跑完整验证。

### 任务 7：浏览器回归

- [ ] 以 backend mode 启动 Next.js。
- [ ] 检查 `/map`、`/calculator`、`/match`、`/assessment`、`/portfolio` 和六类学校详情。
- [ ] 断开/破坏 Bundle 配置验证无 fixture fallback。
- [ ] 保存截图、console 与网络结果到 Stage 5 report 临时目录。

### 任务 8：报告和 change manifest

**文件：**
- 创建：`frontend/docs/STAGE5-INTEGRATION-DEVELOPMENT-LOG.md`
- 创建：`frontend/docs/STAGE5-FRONTEND-BACKEND-INTEGRATION-REPORT.md`
- 创建：`frontend/docs/STAGE5-FRONTEND-CHANGE-MANIFEST.json`

- [ ] 对 baseline 的 87 个前端文件和新增文件计算 before/after SHA。
- [ ] 确认 forbidden directory modification count 为 0。
- [ ] 完成原提示 95 项最终报告和 44 项完成审计。
- [ ] `git diff --check`、最终 status/tag/push/linked-worktree 检查。
