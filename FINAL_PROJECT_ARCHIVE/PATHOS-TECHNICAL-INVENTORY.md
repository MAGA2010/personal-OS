# PathOS 技术库存

## 1. 主要目录

| 路径 | 角色 | 冻结说明 |
|---|---|---|
| `frontend/` | 唯一正式前端 | Next.js App Router、BFF、测试、本地 Preview Bundle 和授权媒体。 |
| `PathOS-db-ranking-standalone/` | Canonical Backend / Data 仓库 | HEAD `b73e61e…`，工作树 clean。 |
| `PathOS-db-ranking-standalone/data-pipeline/` | Canonical 数据管道与 artifacts | 约 864 个文件；包含 Stage 5 Preview Bundle。 |
| `resource/` | 区域数据工作簿 | 原始工作簿禁止无审查修改。 |
| `scripts/` | Stage 6 运行控制 | `pathos-ops.mjs`、process helpers 和 tests。 |
| `docs/` | Workspace 级阶段文档 | Stage 6、Stage 7R、Stage 7A 等报告。 |
| `FINAL_PROJECT_ARCHIVE/` | 最终冻结与发布文档 | 包含 KEEP / DELETE manifest。 |

隔离整合和 Bugfix 报告已收敛到 `docs/history/integration-bugfix/`。

## 2. 前端规模快照

| 项目 | 文件数 |
|---|---:|
| `frontend/src` | 143 |
| `frontend` unit test files | 21 |
| News local campus WebP | 9 |
| Workspace `scripts` | 23 |

文件数只用于导航，不是完整性 manifest。

## 3. 主要组件

### Map

- `MapShell`：地图页面编排、DataSource、工具栏、选择和面板。
- `MapCanvas`：MapLibre canvas、视图和图层宿主。
- `UniversityPoiLayer`：大学 Marker / POI。
- `RegionalStateLayer`：州级 Choropleth 与州选择。
- `RegionDetailPanel`：区域指标和州内学校列表。
- `MapToolbar` / `RegionalLegend`：指标控制与图例。
- `UniversityHoverTooltip` / `UniversityProfile`：学校悬停和详情。
- `BottomSheet` / `ResizablePanel`：移动端与桌面布局。

### Home / Shared

- 首页 Hero、Feature Showcase 和功能翻转卡片。
- `NavBar`、`Footer`、`ThemeToggle`。
- Map / Assessment / Match / Portfolio 的 Entry 场景。

### News

- `NewsEntryHero`
- `HeroImage`
- `HeroBracket`
- `NewsCreditsPage`
- `news-images.ts`
- `usePrefersReducedMotion`

### Data / Server

- `PreviewApiDataSource`
- `data-source-provider`
- `backend-preview.ts`
- `pathos-preview.ts`
- Runtime schemas、legacy mappers 和 domain models
- `/api/pathos/preview`

### Assessment / Calculator / Match

- Assessment 页面及权重、结果展示组件。
- `SchoolPicker` 和费用格式化逻辑。
- Portfolio / Match 的确定性清单分析与缺失值处理。

## 4. 依赖快照

主要运行依赖：

- Next.js `^14.2.0`
- React / React DOM `^18.3.1`
- MapLibre GL `^5.24.0`
- react-map-gl `^8.1.1`
- Tailwind CSS `^3.4.0`
- lucide-react、d3-scale-chromatic、supercluster、topojson-client

主要开发依赖：TypeScript、Vitest、ESLint、eslint-config-next、Playwright types / runner。

## 5. 路由库存

页面路由：Home、Map、News、News Credits、Assessment、Calculator、Match、Portfolio、University Detail、Xuanxiao，以及 4 个 Entry 页面。

BFF 路由：PathOS Preview、AI analyze、AI context、Xuanxiao universities。

没有正式 `/compare`、`/rankings` 或 `/explore` 路由。

## 6. 测试状态

归档时在最终源以 backend mode 和本地 `data/preview` 运行：

- Test files：21/21
- Tests：563/563
- Vitest：v2.1.9

覆盖范围包括 Stage 5 contract、UI closing、区域数据、MapLibre、Choropleth lifecycle、News 摄影、UI collision、首页功能入口、本地 AI Demo 和公网 Map 状态回归。

历史耦合报告记录 529/529；后续 Bugfix 报告记录 534/534。563/563 是归档时最新现状测试数量。

本次归档没有重新运行 Build、Lint 或 TypeScript，也没有更改测试。恢复开发后必须重新执行完整自动化。

## 7. 冻结哈希

- Final frontend filtered copy aggregate：`8197e652d57a48ba19974d2ca4b892ef21093ef57bd924d14278c52a6c1d92d8`
- Preview manifest：`88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`
- Regional workbook：`409ed47b5153725914b463ae3421ad51e5d3d34e5918144f001f341b9894b096`

Aggregate hash 由按路径排序后的源文件 SHA-256 列表再次计算，仅用于本次归档前后对照。
