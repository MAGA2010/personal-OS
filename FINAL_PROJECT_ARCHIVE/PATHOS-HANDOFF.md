# PathOS 未来开发交接

## 1. 阅读顺序

恢复开发前，按以下顺序阅读：

1. `FINAL_PROJECT_ARCHIVE/` 全部文档。
2. `FINAL_PROJECT_ARCHIVE/PATHOS-KNOWN-LIMITATIONS.md`。
3. `PathOS-db-ranking-standalone/docs/` 与 Backend `README.md`。
4. `PathOS-db-ranking-standalone/data-pipeline/` 的 Stage 4B / 4C / 5 文档和 validators。
5. `docs/` 中 Stage 6、Stage 7R、Stage 7A / 7B 报告。
6. `docs/history/integration-bugfix/` 中的耦合与 Bugfix 审计报告。
7. `frontend/src/services/`、`frontend/src/server/`、`frontend/src/domain/`、`frontend/src/regional/` 和 tests。

## 2. 冻结标识

- Backend HEAD：`b73e61ec4fda11b7c72e74c14e414fbe2c74300f`
- Backend branch：`feature/stage7-post-demo-development`
- Stage 6 annotated tag：`pathos-stage6-demo-freeze-operational-readiness-pass`
- Preview manifest SHA-256：`88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`
- Regional workbook SHA-256：`409ed47b5153725914b463ae3421ad51e5d3d34e5918144f001f341b9894b096`

## 3. 唯一正式前端

`frontend/` 是清理后唯一正式前端。它由最终 Vercel / integration 源按排除规则复制，并通过 317 个文件的 aggregate SHA 对照。历史候选、旧稳定前端、构建产物和临时工作副本不再属于当前仓库结构。

## 4. 不要直接修改的内容

- Stage 4B / 4C artifacts、Candidate v2、ranking memberships 和 Stage 3D people。
- Stage 5 Preview Bundle、manifest 和 904 条 verified facts。
- `resource/PathOS_美国各州留学数据矩阵.xlsx` 与生成后的 204 条区域记录。
- 62 个 stable university IDs。
- Stage 6 tag 和外部 checkpoint。
- 旧 Git source `/Users/jiayihuang/PathOS` 与 linked backend。
- 任何 `.env.local`、密钥、地图 AK 或用户私有数据。

## 5. 恢复开发的第一批任务

1. 复制选定源到新的隔离目录，并生成 before manifest。
2. 核对 Backend HEAD、Bundle SHA、workbook SHA 和 62/62/62/904。
3. 重跑 TypeScript、Lint、563 项测试和 Build。
4. 真实浏览器复核 Map Marker、Choropleth、metric retention 和主题切换。
5. 只修复已确认 Bug；不要同时扩展功能。
6. 为变更创建新的计划、日志、change manifest 和独立 Gate。

## 6. 数据与产品原则

- Backend mode 不回退 fixture。
- `null` 不变成 0，pending / deferred 不变成事实。
- 区域指标 `usedForMatch=false`。
- AI 不得使用 quarantined、fixture 或未经验证的上下文。
- Preview / Demo 不构成录取保证。
- Production Data Export 保持禁止，除非另有书面授权和数据 Gate。
