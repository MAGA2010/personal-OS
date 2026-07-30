# PathOS 功能入场动画恢复设计

## 目标

在当前整合候选版本上，以纯加法方式恢复旧版本中已经存在的首页环境效果和四套功能入场体验，同时保持现有 `/map`、`/match`、`/assessment`、`/portfolio`、`/news`、`/calculator` 页面、数据契约和业务逻辑不变。

## 已确认范围

- 首页恢复旧版地球、波形、网格与缓慢环境运动，但保留当前编辑式首页内容、可信数据边界和六模块布局。
- 新增 Map 星球入场、Match 数据波形入场、Assessment 校园影像入场、Portfolio AI 环境入场。
- News 保留现有九张本地授权校园摄影 Hero，不叠加第二套入口。
- Calculator 保持直接进入，因为旧版本不存在独立 Calculator 入场。
- 首页对应 CTA 和模块卡片先进入独立入场页；正式功能 URL 保持原样，直接访问时不播放入场。

## 路由结构

| 首页入口 | 新增入场路由 | 进入的现有正式路由 |
| --- | --- | --- |
| 留学地图 | `/entry/map` | `/map` |
| 自主匹配 | `/entry/match` | `/match` |
| 学校评估 | `/entry/assessment` | `/assessment` |
| 申请清单 | `/entry/portfolio` | `/portfolio` |
| 费用计算 | 无 | `/calculator` |
| 留学资讯 | 无新增 | `/news` |

独立入场路由不加载 Map runtime、Preview 数据或功能状态，因此不会产生透明层拦截、重复 Header、地图 hydration、localStorage 或 URL Store 回归。每个入场页 CTA 使用普通 Next.js `Link` 进入正式页面，浏览器分享、刷新、前进和后退仍以正式 URL 为准。

## 视觉恢复

### 首页环境

- 在当前 Hero 的最底层加入旧版地球视图和柔和遮罩。
- 继续使用当前网格和波形，调整波形运动使其接近旧版环境节奏。
- 地球和波形均 `pointer-events: none`，不遮挡标题与 CTA。
- 环境层不改变当前页面下方可信数据和模块章节。

### Map

- 恢复任务控制台式全屏构图、地球视图、角标、观测状态、巨大 `MAP` 字标、左右数据标识和底部进入按钮。
- 将旧的“40+州”修正为当前可信边界“51 个州级辖区”，避免恢复过时文案。
- CTA 目标从旧 `/map/explore` 改为当前 `/map`。

### Match

- 恢复深色网格、六维数据波形、节点错峰点亮、标题和进入按钮。
- 仅恢复视觉层；不复制旧 Match DTO、权重逻辑或 mock 数据。
- CTA 目标从旧 `/match/explore` 改为当前 `/match`。

### Assessment

- 恢复编辑式校园摄影序列、扫描线、渐变光晕、计数器和进入动画。
- 不采用旧版来源不明的三张校园图片；改用当前 News 已核验并本地保存的 Harvard、MIT、Stanford WebP。
- 不恢复旧版虚构或过时的录取率、响应时间等文案，只显示学校、地点和“本地授权校园摄影”。
- CTA 进入当前 Preview-backed `/assessment`。

### Portfolio

- 恢复深色 AI 控制台、网格、扫描地平线、眼部聚焦和缓慢摇头的环境节奏。
- 不采用来源不明的旧机器人 PNG；使用本地 CSS/SVG 生成的抽象 AI 结构体，避免未知媒体进入正式路径。
- 不复制旧 Portfolio 数据逻辑；CTA 进入当前 `/portfolio`。

## 素材与授权

- 旧地球图片标识为 NASA Photo ID `S131-E-006087`。公开来源确认其为 NASA 作品并属美国公共领域；最终本地文件需记录来源页面、SHA-256 和尺寸。
- Assessment 只使用当前已经完成授权记录的 News WebP。
- Portfolio 不使用来源不明图片。
- 运行时不得请求 NASA、Wikimedia 或其他远程图片地址。

## 动画与可访问性

- 循环动画只改变 `transform` 与 `opacity`。
- `prefers-reduced-motion: reduce` 下停止漂移、扫描、缩放和循环淡变，所有标题、摄影和 CTA 保持静态可见。
- 入场页必须有唯一 `h1`、可见键盘焦点、语义化 CTA 和返回首页入口。
- 装饰图层统一 `aria-hidden`，不进入可访问名称。
- 移动端使用 `100svh`、安全区域内边距和无横向溢出布局。

## 非目标

- 不修改 MapShell、地图交互、Choropleth、URL Store、四项区域指标或 51 州数据。
- 不修改 Match 算法、Assessment 数据输入、Portfolio 数据结构或 News Hero。
- 不新增 fixture、mock、Backend API、Preview Bundle 字段或产品功能。
- 不恢复 `/map/explore`、`/match/explore` 等重复正式功能路由。
- 不创建 tag、push、checkpoint 或 Production Data Export。

## 验证门槛

- 新增测试确认四个入场路由存在、首页只对四个旧入口改链、正式功能页源码未被入口层包装。
- 新增测试确认 CTA 目标是当前正式 URL、没有 `/explore`、没有 mock JSON、没有远程图片。
- 新增测试确认 reduced-motion、装饰层 pointer-events、动画属性和授权素材边界。
- TypeScript、ESLint、全部 Vitest、Next build 全部通过。
- 浏览器检查首页和四个入场页的桌面、平板、移动端及 reduced-motion；正式 Map、Match、Assessment、Portfolio 功能继续可达。
