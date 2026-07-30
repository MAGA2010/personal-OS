# PathOS Stage 5 Warning-Aware Preview 设计

## 目标与边界

在不修改 Stage 4B/4C、Candidate v2、ranking memberships、Stage 3D people
和冻结前端 UI 的前提下，把已审核数据转换为确定性的 Preview Bundle，并由
Next.js BFF 在显式 backend mode 中读取。Preview 始终保持
`sourceLimited=true`、`incomplete=true`、`notFinal=true`，禁止 production
export、fixture fallback、choropleth、parent mode、international applicant
section 和 AI verified context。

## 已审查方案

1. **独立后端 HTTP 服务**：后端没有稳定 HTTP 框架；引入 Flask/FastAPI
   会增加第二套运行时和部署面，拒绝。
2. **把 Bundle 复制到前端 public**：会复制真实数据、暴露内部文件并绕过
   BFF，拒绝。
3. **确定性 Bundle + Next.js BFF**：复用现有 Route Handler、Schema、
   Normalizer 和 DataSource，修改范围全部位于前端白名单，采用。

`transport_mode=preview_bundle_via_next_bff`

## 后端架构

`stage5_preview_adapter` 只读取显式 allowlist 中的已提交 JSON：

- Stage 4B product artifacts、verified overlay、source/provenance；
- Stage 4C overlay、cumulative view、pending/deferred、readiness、
  source/provenance；
- frozen Candidate v2 identity 和 frozen ranking semantics；
- Stage 3D approved narrative 与 program-person slot policy。

不读取 `raw/`、`staging/`、`handoff/`、cache body 或 frontend fixture。
Adapter 先建立以 Candidate v2 stable ID 为键的 62 校索引，再生成轻量
Summary、逐校 Detail、空的 blocked region metrics、公开 source index、
冻结 status dictionary、feature readiness、diagnostics 和 validation result。
所有 JSON 使用 UTF-8、排序 key、稳定数组顺序和结尾换行；manifest 的
`generatedAt` 固定为 source checkpoint 的提交时间。

## 前端架构

`PATHOS_DATA_MODE=fixture|backend` 是唯一模式开关：

- fixture：仅显式选择时读取既有 fixture；
- backend：只读取 `PATHOS_PREVIEW_BUNDLE_DIR`，任何缺失、超时、404、
  invalid JSON、schema/version failure 均返回统一错误，绝不读取 fixture；
- production：缺少显式模式时默认 backend，缺少 Bundle 配置时 fail closed。

BFF 将现有 query-style endpoint 映射到 Bundle 文件。Runtime Schema 接受
Stage 5 manifest/summary/detail 的扩展字段，并拒绝重复 ID、非法坐标、
`[0,0]`、未知 contract version 和非法状态。页面组件继续只消费 Domain
Model，不解释 backend DTO。

## 数据语义

- Enrollment 2019：值保留，带 `referenceYear=2019` 和
  `stale_reference_year`；Harvey Mudd/Olin graduate 和 total 为 null。
- National rank：50 numeric；12 个 `value=null` 且
  `status=not_in_current_national_scope`；rank 0 禁止。
- SAT/ACT：53 verified middle-50，9 `not_reported`；不推断 test policy。
- Test/English policy：62/62 `pending_external_access`、值为 null。
- Geography：46 place，16 county-only；nearest town 不作为 place。
- People：180 identified input slots，130 review gaps；gap 公开为
  `source_review_not_completed`/“数据补充中”；不可公开状态的人物不进入
  Detail/source index/AI。
- Region metrics：records 为空、choropleth disabled，不输出演示估值。
- AI context：backend mode 返回明确 disabled，不构造 advisor payload。

## 错误模型

错误响应包含 `code`、`message`、`featureStatus`、`retryable` 和无敏感信息的
`requestContext`。BFF 不暴露绝对路径、cache path、handoff 或 secret。

## 验证

后端 validator 覆盖原提示列出的 45 项 contract checks，并对两次临时目录
生成进行 byte-for-byte 比较。前端测试覆盖显式模式、成功路径、所有
no-fallback 错误、schema/normalizer、特殊字段与真实 Bundle。最终运行
Stage 4B/4C、完整 Python、tsc、lint、Vitest、Next build 和 backend-mode
浏览器回归。
