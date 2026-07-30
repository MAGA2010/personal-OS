# PathOS Final Clean-Room Runtime Verification

验证日期：2026-07-30（Asia/Shanghai）
最终结论：**PATHOS FINAL RUNTIME VERIFIED**

## 1. 本轮修复

本轮仅关闭两个运行阻断：

1. `/compare`：项目没有独立 Compare 页面；真实比较能力已位于 `/map` 的 `ComparePanel`。新增正式 `/compare` 入口，使用 Next.js redirect 稳定进入 `/map`，没有恢复旧 Mock 或创建伪比较数据。
2. University Marker：修复 `UniversityPoiLayer` 的 MapLibre 晚挂载生命周期。旧实现会在一次性 `load` 已发生、但 `map.loaded()` 暂时为 false 时等待永不重发的事件，导致 source/layer 没有安装。新实现使用有界且可取消的 `isStyleLoaded()` readiness polling，并在 `style.load` 后幂等恢复；原生 `minzoom` 负责 zoom 可见性。

Backend、Preview Bundle、大学事实、区域数据、Match 算法、FIPS Join、Choropleth 数据与配色均未修改。

## 2. Clean-Room

- 最终目录：`/Users/jiayihuang/Downloads/PathOS合并`
- 新 Clean-Room：`/Users/jiayihuang/Downloads/PathOS-runtime-verification-final-2026-07-30`
- 初始复制：1,706 files，约 64 MB。
- 复制时排除：`node_modules`、`.next`、coverage、build/out、cache、logs、`.env.local`。
- 复制后确认：无旧 `node_modules`、无旧 `.next`、无 `.env.local`、无 broken symlink。
- Clean-Room 临时 `.env.local` 仅使用安全 backend 模式和该副本内 Preview Bundle 绝对路径；验证结束后已删除。

## 3. 工具与从零安装

| 项目 | 实际结果 |
| --- | --- |
| Node.js | v20.20.2 |
| npm | 10.8.2 |
| Python | 3.9.6 |
| Git | 2.50.1 (Apple Git-155) |
| `npm ci` | 成功，495 packages |
| `npm ls --depth=0` | 成功，无 missing / invalid |

安装保留一条间接 Mapbox 包的 Node `>=22` engine warning，以及既有 deprecated/audit 提示；当前 Node 20 环境下 TypeScript、测试、build 和 Production runtime 均成功。本轮没有升级依赖或运行 `npm audit fix`。

## 4. 自动化结果

最终目录和新 Clean-Room 均得到相同结果：

| 检查 | 结果 |
| --- | --- |
| TypeScript | 0 errors |
| ESLint | 0 warnings / 0 errors |
| Vitest | 22 files，566/566 tests |
| Production build | 成功；21 个 static generation units |
| `/compare` | 构建成功，运行时 307 到 `/map` |
| `/map` | 构建成功 |
| `/university/[id]` | 保持 dynamic |
| Backend Stage 5 | 49/49 |

新增 3 个 blocker regression tests，并保留原有 563 项全部测试。测试覆盖 Compare canonical redirect、无旧 Mock、原生 minzoom、晚到 style readiness、有界取消和不等待旧 `load`。

## 5. Backend 与数据边界

- Backend branch：`feature/stage7-post-demo-development`
- Backend HEAD：`b73e61ec4fda11b7c72e74c14e414fbe2c74300f`
- Backend worktree：clean
- Preview Bundle manifest SHA-256：`88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`
- Universities：62 schools / 62 summaries / 62 details / 904 verified records
- Regional：4 metrics / 204 records / 51 jurisdictions
- Production Data Export：未启用。

运行架构仍为 Next.js BFF 直接只读 standalone Preview Bundle；无需独立 Python HTTP 服务。

## 6. Production 冷启动与路由

- Clean-Room 命令：`npm run start -- -p 3020`
- Ready：111 ms
- `/`：200
- `/map?region=income&state=06`：200
- `/news`：200
- `/assessment`：200
- `/calculator`：200
- `/compare`：307，最终落到 `/map`
- BFF manifest：200，`pathos-preview-v1`，62/62/62/904
- 核心 404：0
- 核心 500：0

## 7. Marker 浏览器验收

真实 Chrome + MapLibre Canvas 验证：

- 初始加载：大学圆点与缩写标签可见。
- Zoom in / out：Marker 保持可见。
- Resize：六视口截图均显示 Marker。
- Theme switch / `setStyle`：由浅色切至深色后 source/layer 自动恢复，Marker 可见。
- CA：FIPS 06，侧栏 10 校；点击 Marker 正确打开南加州大学 Profile，且没有触发州切换。
- MA：FIPS 25，侧栏 7 校；点击 Marker 正确打开 Tufts University Profile。
- TX：FIPS 48，侧栏 3 校；点击 Marker 正确打开 Rice University Profile。
- Back：TX 返回 `region=safety&state=25`，恢复 Massachusetts 与 7 校。
- Forward：恢复 `region=income&state=48`，Texas 与 3 校。
- Refresh：保持 Texas state/region。
- 任意时刻只存在一个选中州。

## 8. 六视口矩阵

六个视口均检查 `/`、CA Map、`/news`、`/assessment`、`/calculator`、`/compare`：

| 视口 | Map Marker | CA 10 校 | 横向溢出 | broken image | Compare |
| --- | --- | --- | --- | ---: | --- |
| 1440×900 | 可见 | 正常 | 无 | 0 | 重定向 `/map` |
| 1280×720 | 可见 | 正常 | 无 | 0 | 重定向 `/map` |
| 1024×768 | 可见 | 正常 | 无 | 0 | 重定向 `/map` |
| 768×1024 | 可见 | 正常 | 无 | 0 | 重定向 `/map` |
| 390×844 | 可见 | 正常 | 无 | 0 | 重定向 `/map` |
| 320×568 | 可见 | 正常 | 无 | 0 | 重定向 `/map` |

截图与 SHA-256 证据位于：`/Users/jiayihuang/Downloads/PathOS-runtime-verification-final-2026-07-30/runtime-verification/screenshots/`。

## 9. News、Console 与 Network

- News：9/9 本地授权 WebP，0 fallback，0 broken image，无远程校园图片热链。
- Chrome 未观察到 PathOS/React/hydration/MapLibre/BFF 阻断错误。
- Chrome 扩展自身记录过 message-channel closed 环境噪声；该消息不来自 PathOS bundle，也不影响页面。
- 核心 HTTP/BFF 无 404/500。
- 可选 CARTO/OSM basemap 依赖外部网络；大学数据、区域数据和 News 图片均来自本地链路。
- 未配置 Baidu AK 时使用 MapLibre，应用不崩溃。

## 10. 清理和不可变确认

- Clean-Room 临时 `.env.local`：已删除。
- 最终目录 `.env.local`：不存在。
- 本轮服务：已停止；3020 已释放。
- Backend worktree：clean。
- Preview Bundle SHA 与数据边界：不变。
- 未修改 API Key 或 Secret；未 push、force、rebase、reset、tag 或 checkpoint。

本次结论：**PATHOS FINAL RUNTIME VERIFIED**。
