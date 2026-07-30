# PathOS 并行开发耦合开发日志

## 2026-07-25 — 发现与隔离

- 对 `PathOS所有合并/pathos` 递归盘点，保留 `.git`、配置、源码、资产、文档、测试和数据索引。
- 将候选 dirty 工作树与 Git HEAD 分开冻结；历史 Backend ZIP 只建立目录索引。
- 建立 `canonical-baseline`、`candidate-inventory`、`integration`、`reports`、`screenshots`、`manifests`。
- 未复制 `node_modules`、`.next`、缓存、日志、`.env.local` 或 Git metadata 到 integration。

## 2026-07-25 — Canonical 决策

- Backend、BFF、DataSource、runtime schema、Map、Assessment、Match、Calculator、Portfolio、Navigation、Footer 均以稳定版本为功能基线。
- 候选首页具备更成熟的暗色编辑式叙事，决定 HYBRID：提取构图、字号节奏、细线和章节化呈现；所有 CTA、事实和数据入口来自 Canonical。
- 候选 News 仍依赖旧静态 JSON；候选媒体存在删除、来源未知或无授权记录，全部拒绝进入正式路径。
- 候选 `/map/rankings` 与 explore 原型记录为 `ARCHIVE_ONLY`，不创建重复正式路由。

## 2026-07-25 — 整合实现

- 新首页使用 scoped CSS module 和轻量 CSS/SVG 波纹，不引入新依赖。
- 首页只指向 `/map`、`/calculator`、`/match`、`/assessment`、`/portfolio`、`/news`。
- 首页显示 62 / 904 / 51 / 4 与 Preview 免责声明。
- News 保留 Canonical Hero，接入 9 张本地 WebP；每张来自独立 Wikimedia Commons File 页面，并完成作者、许可证、原图 URL、SHA、尺寸和处理记录。
- Credits 页面直接读取本地授权 JSON，运行时无 Wikimedia 热链。

## 2026-07-26 — 浏览器发现与修正

- 真实 Backend 浏览器检查发现州选择菜单因 raw summary 缺少可选 `stateFips` 而退化为单个 `00`。
- 改为使用 Canonical POI adapter 已推导的 FIPS；Backend 模式得到 28 个有当前 62 校分布的州/辖区选项，不再出现 `00`。
- 补齐 toolbar 选州到 `?state=` 的即时状态与 URL 同步；California 显示 10 所当前范围大学。
- 将旧文案“六大指标覆盖全美”纠正为“四项州级指标覆盖 51 个辖区”。
- 图例由总记录数 204 归一到当前指标 51/51，避免错误的 `204/51` 表述。
- 城市聚合显示层对无来源值输出“数据补充中”，不再把 sentinel `0` 显示为验证事实；内部数值形状保持兼容。

## 自动化与浏览器

- TypeScript：0 error。
- ESLint：0 warning / 0 error。
- Vitest：16 files、529 tests 全部通过。
- Next build：生成 16 个静态页面任务；route table 15 条，大学详情保持 dynamic。
- 生产服务真实 Backend 路由：Home、Map、News、Assessment、Calculator、Match、Portfolio、Harvard detail 均返回可渲染页面。
- 六视口：1440×900、1280×720、1024×768、768×1024、390×844、320×568；无横向溢出。
- Light、Dark、System 均验证；reduced-motion 由 CSS contract 与测试验证。
- 最终生产浏览器 Console：0 error、0 warning。

## 风险与后续

- 候选 `/map/rankings` 和 explore 概念可能有展示价值，但数据和路由契约未验证，保留待用户决定。
- 地图的市级道路与 city-boundaries 为未来可选能力；当前正式权威层仍是 4 项州级指标，未伪装为已完成市级数据。
- 本轮未修改 Backend、Preview Bundle、稳定前端或 checkpoint。
