# PathOS 旧版入场动画与环境效果恢复报告

## 范围

本轮仅在现有正式功能页之前恢复旧版入场体验，不修改正式页面的业务逻辑、数据读取或交互定义。

- 首页恢复星球与波纹环境层。
- 地图入口：`/entry/map`，进入现有 `/map`。
- Match 入口：`/entry/match`，进入现有 `/match`。
- Assessment 入口：`/entry/assessment`，进入现有 `/assessment`。
- Portfolio 入口：`/entry/portfolio`，进入现有 `/portfolio`。
- News 保留现有摄影 Hero。
- Calculator 保持直接进入 `/calculator`。

正式 `/map`、`/match`、`/assessment`、`/portfolio`、`/news` 和 `/calculator` 页面本体均未修改。

## 实现边界

- 所有入场页均提供明确的“进入功能”与“返回首页”路径。
- 地图入口使用本地 NASA 地球摄影，不存在运行时远程热链。
- Assessment 入口复用项目中已经完成授权记录的本地校园摄影。
- Portfolio 使用纯 CSS 环境图形，不引入来源未知的旧机器人图片。
- 环境层不接管正式页面状态，也不改变 Map、Match、Assessment、Portfolio 或 News 的数据契约。
- 动画仅使用 `transform` 与 `opacity`，并提供 `prefers-reduced-motion` 静态降级。
- 入场页在 390×844 与 320×568 下无横向溢出，主 CTA 固定可见。

## 地球图片授权

- 本地文件：`public/entry/pathos-earth-from-orbit.jpg`
- 场景：STS-131 飞行第二日拍摄的地球
- 来源：Wikimedia Commons File 页面
- 作者：NASA
- 许可：Public Domain（NASA）
- SHA-256：`2fe7ed133cbbdafe02581c58665a5199e992dbcd53c700171a097f6bd45e5d33`
- 尺寸：4256×2700

完整来源记录见 `public/entry/ATTRIBUTIONS.md`。

## 自动化结果

- TypeScript：通过，0 errors。
- ESLint：通过，0 warnings / 0 errors。
- Vitest：17 个测试文件，551/551 通过。
- Next.js production build：通过，静态页面生成 20/20。
- 大学详情路由 `/university/[id]` 保持动态服务端路由。

## 浏览器结果

- 首页、四个入场页以及对应正式页面均完成真实浏览器检查。
- 桌面：1440×900。
- 移动：390×844、320×568。
- 四个入场页均无横向溢出，标题与主 CTA 可见。
- Map、Match、Assessment、Portfolio 的 CTA 均进入原有正式页面。
- `/news` 保持 9 张本地校园摄影，0 broken image，0 远程图片请求。
- 浏览器 Console 未发现新增应用错误。

## 数据与后端完整性

- Backend branch：`feature/stage7-post-demo-development`
- Backend HEAD：`b73e61ec4fda11b7c72e74c14e414fbe2c74300f`
- Backend worktree：clean。
- Preview Bundle manifest SHA-256：`88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`
- Preview contract：62 schools / 62 summaries / 62 details / 904 verified records。
- 未修改 Backend、Preview Bundle、地图数据、Match 算法或任何现有业务事实。

## 运行状态

- 预览地址：`http://127.0.0.1:3017`
- 数据模式：`backend`
- 数据链：Next.js BFF 直接读取 standalone Preview Bundle。
- 服务保持运行，供用户人工查看。
