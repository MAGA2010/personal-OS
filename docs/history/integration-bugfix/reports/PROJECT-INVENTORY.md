# PathOS 候选项目盘点

生成时间：2026-07-25T22:31:37+00:00

- 候选物理 Git 仓库：1 个。
- 候选版本实体：3 个（当前工作树、Git HEAD、后端 ZIP）。
- Canonical：当前稳定前端快照 + standalone Stage 5 Preview Backend。
- `lastModified` 只记录，不参与选择。

| ID | 类型 | 路由 | 组件 | 测试 | 资产 | 关系 |
|---|---:|---:|---:|---:|---:|---|
| canonical-stable-frontend | canonical-frontend-snapshot | 14 | 49 | 22 | 9 | CANONICAL |
| candidate-worktree | candidate-monorepo-worktree-snapshot | 14 | 23 | 41 | 6 | FORKED_FROM_CANDIDATE / DIRTY_UNVERIFIED |
| candidate-git-head | candidate-monorepo-committed-snapshot | 11 | 17 | 41 | 11 | OLDER_COMMITTED_VARIANT |
| candidate-backend-zip | archive-of-linked-backend-era-project | 1 | 7 | 45 | 0 | OLDER_UNVERIFIED_VERSION / ARCHIVE_ONLY |
