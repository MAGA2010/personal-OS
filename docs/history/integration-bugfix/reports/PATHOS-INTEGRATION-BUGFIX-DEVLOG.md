# PathOS Integration Bug-Fix Devlog

日期：2026-07-26

## Preflight

- integration 根目录确认是 Next.js App Router 前端。
- 数据架构确认是 Next.js BFF 直接读取 standalone Preview Bundle，无独立 Python HTTP 服务。
- Backend branch=`feature/stage7-post-demo-development`，HEAD=`b73e61ec4fda11b7c72e74c14e414fbe2c74300f`，worktree clean。
- Bundle manifest SHA-256=`88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`。

## 修复前观察

- 1440/1280/1024：MapLibre 右上控件与统一工具栏占用同一锚点。
- 768：桌面导航文字换行；360px 桌面侧栏压缩地图，平板布局出现双重桌面语义。
- 390/320：地图缩放控件被工具栏覆盖。
- 320：州下拉从视口左侧溢出，且层级可能低于图例。
- 所有地图视口：图例与 MapLibre attribution 相交；320 短屏图例还覆盖左侧缩放控件。
- 首页、News、Assessment、Calculator 未发现 Critical / High 碰撞。

## 实现

1. 全局导航桌面断点由 `md` 调整到 `lg`，768px 使用单一移动导航。
2. MapLibre NavigationControl 从右上移到左上；手机端按工具栏实际行数增加 scoped 顶部安全区。
3. 工具栏打开州下拉时提升到既有 `z-map-tooltip` token；320px 下拉固定在工具栏左缘且保持完整视口内。
4. 桌面 UniversityProfile、Sidebar 和 CityCard 统一从 `lg` 开始；Tablet/Phone 使用既有 BottomSheet 承载州/城市详情。
5. 图例上移至 attribution 之上；有 BottomSheet 时继续上移；320px 下收窄图例，为缩放控件保留 6px 以上独立轨道。
6. 新增 5 条 integration bug-fix 响应式碰撞契约，并同步更新既有断点断言。

## TDD 证据

- 新增 Q1–Q5 后首次运行：5 项失败、60 项通过。
- CSS specificity 回归断言加入后先失败，再修复为通过。
- 320px 2px 安全区和图例轨道断言均先失败，再修复为通过。
- 最终专项：65/65；最终全量：534/534。

## 浏览器结果

- 六视口均无页面横向溢出、broken image 或交互控件几何重叠。
- 320px 最终：toolbar/nav=false，nav/legend=false，legend/attribution=false。
- 390px 最终：toolbar/nav=false，legend/attribution=false。
- 768px：桌面导航、桌面侧栏均隐藏；州详情 BottomSheet 唯一可见。
- 1024px 以上：桌面侧栏恢复，工具栏与左上地图控件分离。
- California 10 所；Massachusetts 7 所；Texas 3 所；URL 与 Back/Forward 正确。
- 学校详情打开后地图中心点顶层仍为 MapLibre canvas，无 full-viewport pointer overlay。
- News 9/9 本地校园图，0 broken，0 external campus image。

## 已知非阻塞项

- `/compare` 不是当前正式路由，HTTP 404；没有任何正式导航或 CTA 指向它。比较功能仍在 `/map` 的 ComparePanel 中，本轮不扩大产品路由决策。
- 地图底图依赖 CARTO/OpenStreetMap 网络；BFF 数据与校园图片均为本地只读资源。
