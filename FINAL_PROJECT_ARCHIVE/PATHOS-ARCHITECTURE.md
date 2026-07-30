# PathOS 技术架构

## 1. 总体链路

```text
Browser
  → Next.js App Router
  → Client DataSource
  → Next.js BFF (/api/pathos/preview)
  → server-only Preview loader
  → immutable Stage 5 Preview Bundle
```

当前演示架构不需要独立 Python HTTP 服务。Standalone Backend 主要承载 Git 历史、数据管道、验证器和冻结 artifacts；运行时由 Next.js BFF 以只读方式加载 Preview Bundle。

## 2. Frontend

### 技术栈

- Next.js 14
- React 18
- TypeScript
- MapLibre GL / react-map-gl
- Tailwind CSS、PostCSS 与组件级 CSS
- Vitest；部分浏览器流程使用 Playwright 工具链

### 目录职责

| 目录 | 主要职责 |
|---|---|
| `src/app/` | App Router 页面、布局和 BFF Route Handlers |
| `src/components/` | Home、Map、News、University、共享 UI 组件 |
| `src/hooks/` | 视图状态、URL 桥接与交互 Hooks |
| `src/services/` | DataSource、Preview API 客户端与模式选择 |
| `src/server/` | server-only Bundle loader、BFF 和 AI context 组装 |
| `src/domain/` | University / Region 等领域模型 |
| `src/regional/` | 州级指标、FIPS 规范化和区域状态逻辑 |
| `src/state/` | Compare 等客户端状态 |
| `src/test/unit/` | 数据契约、页面、地图、摄影和回归测试 |
| `generated/regional-data/` | 后期地图 Demo 使用的 4 项州级区域数据 |

### 主要模块

- **Home：** 品牌叙事、Feature Showcase、真实路由 CTA 与功能入场效果。
- **Map：** `MapShell` 组织地图、工具栏、Marker、州级图层、侧栏和 Bottom Sheet。
- **News：** `NewsEntryHero`、本地校园摄影、reduced-motion 与 Credits。
- **Assessment：** 学生输入与评估流程骨架。
- **Calculator：** 学校选择、费用比较与最多 3 校对比流程。
- **Match：** 基于当前真实维度的匹配展示；区域指标明确不进入算法。
- **Compare：** 目前是地图内 `ComparePanel`，没有独立 `/compare` 正式路由。
- **University Detail：** 动态服务端路由 `/university/[id]`，从真实 DataSource 读取 Detail。

## 3. Backend / Data

Standalone Backend：

`/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking-standalone`

- 当前分支：`feature/stage7-post-demo-development`
- 当前 HEAD：`b73e61ec4fda11b7c72e74c14e414fbe2c74300f`
- 数据 checkpoint：`ec8c66e200b566dba4de35987aa5213960749a57`
- Git metadata 位于 standalone 目录内。
- Frontend integration 没有修改该 Backend commit、Stage 4B / 4C artifacts 或 Stage 5 Preview Bundle。

Preview Bundle：

`PathOS-db-ranking-standalone/data-pipeline/artifacts/stage5-warning-aware-preview`

运行时 loader 校验 contract version、view、manifest 和数据 schema；backend mode 失败时 fail closed，不回退 fixture。

## 4. Data Layer

### University Preview

- Schools：62
- Summaries：62
- Details：62
- Verified records：904
- Contract：`pathos-preview-v1`
- Dataset：`stage5-preview-ec8c66e`
- View：`preview`

### Regional Map Dataset

- Metrics：4
- Records：204
- Jurisdictions：51（50 州 + Washington, D.C.）
- `usedForMap=true`
- `usedForMatch=false`

区域数据是 Stage 7 后期独立生成的地图 Demo 数据，不应被误写为 Stage 5 Bundle 内已启用的 Choropleth。Stage 5 manifest 仍保留 `choropleth=blocked` 的历史契约状态。

## 5. 部署形态

- 唯一正式前端：`frontend/`
- Canonical Backend：`PathOS-db-ranking-standalone/`
- `frontend/data/preview` 是为 Next.js BFF / Vercel file tracing 保留的运行时 Bundle 副本，其 manifest 与 canonical Bundle 一致。
- 历史隔离耦合源已由发布前清理取代；审计报告保留在 `docs/history/integration-bugfix/`。
- 公网演示地址：`https://pathos-preview-20260726.vercel.app`

公网地址属于 Vercel Preview / Demo，不等同于生产级部署，也不授权 Production Data Export。
