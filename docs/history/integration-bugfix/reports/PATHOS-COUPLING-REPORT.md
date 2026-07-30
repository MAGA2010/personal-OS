# PathOS 并行开发耦合报告

## 结论

状态：**READY FOR USER INTEGRATION REVIEW**。

以当前稳定 PathOS 为唯一 Canonical 功能与数据主线，在隔离目录中完成视觉提取式整合。没有用候选 mock、旧 JSON、Backend ZIP 或未知媒体替换正式链路。

## 盘点结果

- 候选物理项目仓库：1。
- 候选版本实体：3。
- 前端候选实体：2（dirty 工作树、Git HEAD）。
- Backend 候选实体：1（历史 ZIP）；另有 Canonical standalone Backend 1。
- Git 仓库：1。
- 模块：144；完全重复 17、近似重复 13、完全重复组 27。

## 主要决策

- Home：HYBRID。保留 Canonical 导航、路由、事实和免责声明，吸收候选高级编辑式视觉结构。
- 网站介绍 / Feature showcase：吸收候选叙事节奏，改写为 6 个真实、可达章节，不虚构功能。
- Navigation / Footer：KEEP_CANONICAL；各保留一份。Footer 只把来源口径纠正为“数据来源可追溯 · Preview / Demo”。
- News：KEEP_CANONICAL + 合法本地摄影。拒绝候选旧 `news.json` 和未知来源图片。
- Map / Assessment / Calculator / Match / Portfolio：KEEP_CANONICAL。仅修正整合验收发现的 FIPS、URL、图例和缺失值显示耦合问题。
- 候选 Rankings / Explore：ARCHIVE_ONLY，等待独立产品与数据决策。
- Backend ZIP、candidate data pipeline：ARCHIVE_ONLY，未运行、未导入。

## 数据边界

- `contractVersion=pathos-preview-v1`
- `view=preview`
- schools / summaries / details = 62 / 62 / 62
- verified records = 904
- regional metrics / records / jurisdictions = 4 / 204 / 51
- `usedForMap=true`，`usedForMatch=false`
- fixture fallback = 0；quarantine exposed = 0
- sourceLimited / incomplete / notFinal = true / true / true
- Production Data Export 保持禁止。

## 自动化

- TypeScript：通过，0 error。
- ESLint：通过，0 warning / 0 error。
- Vitest：16 files，529/529。
- Build：通过；15 条 route table，`/university/[id]` 为 dynamic。
- 新增整合契约测试：6 项；覆盖唯一 Navigation/Footer、正式 CTA、62/904/51/4、无 candidate mock、Preview BFF 和依赖面。

## 浏览器矩阵

- 视口：1440×900、1280×720、1024×768、768×1024、390×844、320×568。
- 正式路由：`/`、`/map`、`/news`、`/assessment`、`/calculator`、`/match`、`/portfolio`、Harvard detail。
- 主题：Light、Dark、System；reduced-motion 样式与测试契约有效。
- `/news`：9 个本地 WebP、0 broken、0 remote runtime image。
- `/map`：MapLibre canvas 加载；四项图层切换；`?state=06`；California 10 校侧栏。
- 所有检查页面：1 个 Navigation、1 个 Footer、无横向溢出、无 Next error portal。
- 最终生产浏览器 Console：0 error、0 warning。

## 对比截图

`screenshots/` 下保留 canonicalBefore、candidate、integratedAfter。Home、News、Map、Assessment、Feature showcase、Mobile Home 均有可追溯 SHA；详见 `PATHOS-COUPLING-SCREENSHOT-MANIFEST.json`。

## 未进入运行路径

- 候选 Backend ZIP、migration、数据副本、stash。
- 候选 mock/static university/news JSON。
- 候选未知来源 earth、robot、校园媒体。
- 候选 `/map/rankings` 和 explore 原型。
- 第二套 UI framework、动画库、lockfile 或全局 CSS。

## 未解决事项

- 非阻塞 Medium：是否将候选 Rankings / Explore 概念发展为正式、真实数据驱动路由，需要用户后续产品决策。
- 无 Critical；无 High。

稳定前端 baseline 清单逐项校验成功；Backend worktree clean；Preview manifest SHA 未变。未创建 tag、未 push、未创建 checkpoint。
