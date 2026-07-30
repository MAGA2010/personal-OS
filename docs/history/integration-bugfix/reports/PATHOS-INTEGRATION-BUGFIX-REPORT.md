# PathOS Integration Bug-Fix Report

日期：2026-07-26

## 结论

当前候选已达到 `READY FOR USER BUG REVIEW` 条件。修复后 Critical=0、High=0、Medium=0；未重新设计页面，也未改变数据或业务语义。

## Bug before / after

| 等级 | 修复前 | 修复后 |
|---|---:|---:|
| Critical | 0 | 0 |
| High | 3 | 0 |
| Medium | 1 | 0 |
| Low | 0 | 0 |

主要修复：地图原生控件与工具栏分离；768px 统一使用移动导航与 BottomSheet；320px 州下拉保持视口内；图例避开 attribution、缩放控件和 BottomSheet。

## 页面与浏览器矩阵

| 视口 | 首页 | Map | News | Assessment | Calculator | 横向溢出 |
|---|---|---|---|---|---|---:|
| 1440×900 | 正常 | 正常，桌面侧栏 | 正常 | 正常 | 正常 | 0 |
| 1280×720 | 正常 | 正常，桌面侧栏 | 正常 | 正常 | 正常 | 0 |
| 1024×768 | 正常 | 正常，桌面侧栏 | 正常 | 正常 | 正常 | 0 |
| 768×1024 | 移动导航唯一 | BottomSheet 唯一 | 正常 | 正常 | 正常 | 0 |
| 390×844 | 正常 | 无工具栏/控件碰撞 | 9 图正常 | 正常 | 正常 | 0 |
| 320×568 | 正常 | 三组碰撞均为 false | 9 图正常 | 正常 | 正常 | 0 |

125% 与 150% 使用等效 CSS viewport（819px、683px）复核：移动/桌面互斥、核心 CTA、地图工具栏和 BottomSheet 保持可用。Light、Dark、System 三态可循环；reduced-motion 由现有 CSS media query 与自动化契约验证，未修改其产品语义。

## Map 专项

- `/map?region=income&state=06`：California，10 所学校。
- `/map?region=safety&state=25`：Massachusetts，7 所学校。
- `/map?region=income&state=48`：Texas，3 所学校。
- California → Massachusetts → Back → Forward URL 顺序正确。
- 详情卡打开后无 full-screen pointer overlay；地图中心顶层仍是 MapLibre canvas。
- 320px：toolbar/nav overlap=false；nav/legend overlap=false；legend/attribution overlap=false。
- 四项 Choropleth、单州选择、州内大学列表、Marker、Tooltip、ComparePanel 和 URL Store 业务语义未改变。

## News 与其他页面

- News：9 个唯一 `/news/campus/` 本地资源，0 broken，0 external campus image；Credits 路由可达。
- Home 两个主 CTA 分别指向 `/map` 和 `/match`，点击地图 CTA 成功导航。
- Assessment、Calculator、Match、Credits、Harvard detail 均返回 HTTP 200。
- `/compare` 返回 HTTP 404；它不是当前正式路由，且没有正式链接指向它。现有比较能力位于地图 ComparePanel，本轮按范围约束未新增产品路由。

## 自动化

- `npx tsc --noEmit`：0 error。
- `npx next lint --max-warnings 0`：0 warning / 0 error。
- `npx vitest run`（显式 backend Bundle）：16 files，534/534。
- `npx next build`（显式 backend Bundle）：成功；15 条 route table，`/university/[id]` 为 Dynamic。

## 运行架构与服务

- 数据后端：Next.js BFF + standalone Preview Bundle；无需独立 Python HTTP 服务。
- Frontend controller PID：81248（最终 PID 以运行时记录为准）。
- Frontend listener PID：81263（最终 PID 以运行时记录为准）。
- Port：3017。
- URL：`http://127.0.0.1:3017`。
- Log：`/tmp/pathos-integration-bugfix-3017.log`。
- 数据模式：backend；fixture fallback=0。

## 数据完整性

- contractVersion=`pathos-preview-v1`；datasetVersion=`stage5-preview-ec8c66e`；view=`preview`。
- school/summary/detail=`62/62/62`；verifiedRecordCount=`904`。
- Backend HEAD 与 worktree 未变化。
- Bundle manifest SHA-256 保持 `88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`。
- Backend、Preview Bundle、Workbook、数据事实和 Match 算法均未修改。
