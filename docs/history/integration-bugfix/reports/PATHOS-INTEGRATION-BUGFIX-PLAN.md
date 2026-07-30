# PathOS Integration Bug-Fix Plan

日期：2026-07-26

## 目标

在不改变产品设计、数据契约和业务功能的前提下，清除整合候选中的 Critical / High UI 碰撞，并修复低风险 Medium 问题。完成 TypeScript、零警告 lint、全量测试、生产构建和真实 Chrome 多视口验收，最后保持服务运行供用户查看。

## 边界

- 仅修改 integration 前端的布局、响应式样式、交互层级及相关测试。
- 不修改 standalone Backend、Preview Bundle、Workbook、62/62/62/904 数据事实、Match 算法、FIPS Join、Choropleth palette 或 URL Store 业务语义。
- 不新增 `/compare` 路由；当前比较能力继续由地图中的 ComparePanel 提供。
- 不创建 tag、commit、push 或 checkpoint。

## 修复顺序

1. 建立浏览器 Bug Matrix 和修复前截图。
2. 先写失败的碰撞契约测试。
3. 修正导航断点、地图控件锚点、下拉层级、图例安全区和平板侧栏。
4. 运行 TypeScript、lint、534 项测试与生产构建。
5. 在 1440×900、1280×720、1024×768、768×1024、390×844、320×568 下复核正式页面。
6. 启动 backend 数据模式，打开 Chrome 并保持服务运行。

## 验收门槛

- Critical=0，High=0。
- 核心控件可点击，无透明层阻挡，无横向溢出。
- 320px、390px、Tablet 和桌面布局互斥正确。
- California 10 所学校、州切换、Back/Forward、四项州级图层保持。
- TypeScript 0 error；lint 0 warning；测试数不少于 529；production build 成功。
