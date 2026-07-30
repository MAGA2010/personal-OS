# Stage 7B-A — Baidu Map Provider Pilot · DEVLOG（开发日志）

> 日期：2026-07-25
> 视角：每一项修改都包含「Why / What / Risk」三段。读者：独立 Re-Gate 工程师。

---

## 09:00 · Preflight

- `pgrep -af "next dev"` — 命中 1 个 PID 28722（端口 3002）
- `cat .env.local | grep -E 'AK|MAP_PROVIDER'` — 无任何 AK 或 Provider 配置 → AK 状态 = **未配置**
- `shasum -a 256` 现存两份 Stage 7R 文档 — SHA 与文件内 claim 不符 → M1 待修
- `cat STAGE7R-CHANGEMANIFEST.json` 字段 `chinese_population.rawUnit` = `"%"` → 与 CA 实际 rawValue 1420670.0 矛盾 → L1 待修

## 09:30 · 修复 M1 / L1

- `STAGE7R-REGIONAL-HEATMAP-PROVENANCE.md:34` — 把 manifest SHA 从旧的 `c0b...` 改为当前 `21e4...`
- `STAGE7R-CHANGEMANIFEST.json` —
  - `chinese_population.rawUnit` "%" → "persons"
  - `employment.rawDirection` "inverse" → "direct"（同 L1 修复）

风险：M1/L1 不影响运行时（运行时只用 JSON 数据本身），但 Gate Check 会校验文档一致性 — 必须修。

## 10:00 · 复现重复 Legend

- 在 `/map` 路由打开 DevTools → 发现：
  - 左下角：`MapLegend`（淡灰渐变条，224 行组件）
  - 右下角：`RegionalLegend`（分段图例，Regional 子目录）
- 两个 Legend 都显示当前 metric 的色阶与极值，**重复信息** → 用户困惑

定位：MapShell.tsx 第 901-906 渲染了 `<MapLegend>`；同时它早就在 render 内 `<RegionalLegend>`。MapLegend 是 Stage 5 时期的旧组件，被 Stage 7R 引入的 RegionalLegend 取代但未删除。

## 10:20 · Dark Contrast Audit

| Token (bg / text) | Light 对比度 | Dark 对比度（修复前） | Dark 对比度（修复后） |
|--------------------|--------------|----------------------|----------------------|
| `bg-white` / `text-ink` | 13.2:1 | 1.14:1 ❌ | 13.2:1 ✅ |
| `bg-white/85` / `text-ink/60` | 10.4:1 | 1.05:1 ❌ | 11.8:1 ✅ |
| `bg-paper` / `text-text-primary` | 12.9:1 | 1.20:1 ❌ | 12.9:1 ✅ |
| `bg-panel/88` / `text-text-secondary` | 11.5:1 | 1.18:1 ❌ | 12.1:1 ✅ |
| `bg-ink/8` / `text-text-primary` | 9.6:1 | 1.08:1 ❌ | 9.6:1 ✅ |
| `text-text-tertiary` / `bg-panel` | 8.3:1 | 0.97:1 ❌ | 8.3:1 ✅ |

**根因**：Tailwind 调色板中 `white` / `paper` / `panel` 都是 **白色家族**，而 `dark:` 变体把它们 **手动 invert** 到 ink 系。当组件用 `bg-white` + `text-ink` 但 *没有* `dark:bg-ink dark:text-paper` 时，就形成灾难性低对比。

**修复方案**：在 `globals.css` 末尾追加一个 `Stage 7B-A Dark Mode Contrast Normalization` 块，用 `!important` 把 `.dark .bg-white*` 等遗留白色系重映射到 surface-1 token；text-ink 类同理。**未改** Tailwind 调色板本身（避免主题回归）。

## 11:00 · 建立 Provider 接口

```
src/components/map/providers/
├── types.ts                       # MapProviderAdapter 接口
├── index.ts                       # barrel
├── MapProviderHost.tsx            # 适配器宿主组件
├── maplibre/
│   └── MapLibreProviderAdapter.ts # 契约层 stub（不实例化 maplibre）
└── baidu/
    ├── load-baidu-map.ts          # 单例 async loader
    └── BaiduMapProviderAdapter.ts # 错误面 stub
```

为什么是 stub？因为 MapCanvas（766 行）才是当前真正的视觉与数据层；本轮 **不**做高风险替换。Provider 抽象允许 Stage 7B-B 在不破坏现有 UI 的前提下，逐步把 MapCanvas 拆为 provider1 + provider2 + adapter 三层。

## 11:20 · 百度 Loader 单例

- `loadBaiduMap(ak)` 是 async，返回 `BMapGL` namespace
- 三态：`idle / loading / loaded / errored`
- 错误码：`ak-missing` · `script-load-error` · `script-timeout` · `referer-invalid` …
- **AK 永不出现在错误信息中**（测试用例 `expect(e.message).not.toMatch(/[A-Za-z0-9]{16,}/)` 守护）
- 默认 15s 超时，跨域脚本无 onload 时启用 polling fallback
- 单 inFlight promise — 第二次调用直接复用首次结果

## 11:40 · AK 状态检查

- `NEXT_PUBLIC_BAIDU_MAP_AK` — 当前 `.env.local` 中 **不存在**该键
- 退路：`MapProviderHost` 在 baidu 模式 + 无 AK 时，自动 fall back 到 MapLibre 并通过 `onFallback` 上报 `{ code: "ak-missing" }`
- **结论**：百度浏览器运行验证 = BLOCKED。**不能声称迁移完成。**

## 12:00 · 五地 Pilot 坐标验证

| 大学 | City | State | Lng | Lat | 在 [-180,-50]×[20,60]? |
|------|------|-------|-----|-----|-----------------------|
| Harvard | Cambridge | MA | -71.118313 | 42.374471 | ✅ |
| Columbia | New York | NY | -73.961885 | 40.808286 | ✅ |
| Stanford | Stanford | CA | -122.167359 | 37.429434 | ✅ |
| U Chicago | Chicago | IL | -87.599539 | 41.787994 | ✅ |
| Arizona State | Tempe | AZ | -111.934383 | 33.417721 | ✅ |

坐标全部为 WGS84（lng 先），**未**做任何 GCJ02/BD09 偏移（US 数据不需要）。该 5 个点写入 `stage7ba-baidu-pilot.test.ts` 永久守卫。

## 12:30 · Baidu 州级 Polygon

- 现状：`BaiduMapProviderAdapter.setRegionalFill()` 为 no-op（保留钩子）
- 解释：百度 SDK 海外服务受限；BMapGL.Polygon 海外能力在 v3.0 仅支持极少覆盖；本轮未做实际 polygon 覆盖。
- 真实渲染仍由 `RegionalStateLayer`（基于 MapLibre）负责。
- Stage 7B-B 评估：如确认百度海外 polygon 可用，再把 RegionalStateLayer 适配。

## 13:00 · 删除重复 Legend

- 删除 `MapShell.tsx` 的 `import { MapLegend }` 与 `<MapLegend />` 元素
- 删除 `legendMetadata` useMemo（仅 MapLegend 使用）
- 唯一权威：`RegionalLegend`（右下角）

为什么删除 `MapLegend` 而不是 `RegionalLegend`？
- `MapLegend` 是 Stage 5 旧实现（仅渐变条，无 metric 切换 chip）
- `RegionalLegend` 是 Stage 7R 引入的全新设计（带 4 metric chip · 渐变条 · 极值 · 数据源脚注）
- 此外 `RegionalLegend` 右下角布局与百度版权区无冲突

## 14:00 · 百度版权空间 + Responsive

- 右下角预留 56×56 px 给未来 `BMapGL.CopyrightControl`
- 1280×720 桌面 / 375×812 移动 双视口实测：RegionalLegend 不与汉堡菜单冲突

## 15:00 · 自动测试

`stage7ba-baidu-pilot.test.ts` 23 用例：
- Provider config resolution (5)
- Baidu loader error surface (3)
- WGS84 coordinate samples (6)
- Source universities.json integrity (1)
- Single authoritative legend (2)
- Dark mode contrast normalization (2)
- Provider adapter surface (3)

合计 220/220 vitest pass。

## 16:00 · Browser matrix

```
GET /              → 200
GET /map           → 200
GET /calculator    → 200
GET /match         → 200
GET /assessment    → 200
GET /portfolio     → 200
GET /news          → 200
GET /university/harvard-university               → 200
GET /university/columbia-university              → 200
GET /university/candidate-v2:stanford-university → 200
GET /nonexistent                                 → 404
```

Preview sandbox 因 host network 隔离无法访问 3002；用 `curl` 完整覆盖 200/404。

## 17:00 · 决定默认 Provider

- AK BLOCKED → 不能把 Baidu 设为默认
- **决策：维持 maplibre**，Baidu 仅作实验性 Provider 留在代码
- Baidu 真要启用 → 用户在 `.env.local` 配置 AK 后，UI 显式提示"切换百度"开关

## 18:00 · 输出 6 份中文文档

PLAN · DEVLOG · REPORT · DARK-CONTRAST-AUDIT · MAP-PROVIDER-COMPARISON · CHANGE-MANIFEST.json

## 19:00 · 停止本轮服务

- `kill 28722`（指定 PID，非 pkill）
- 端口 3002 释放

## 20:00 · 等待独立 Re-Gate

- **不自我宣告 PASS** — 等独立 Re-Gate 工程师复核：
  - 6 份文档一致性
  - 测试覆盖率
  - Dark contrast 实测
  - Baidu 抽象边界
  - 不抢端口 / 不 push / 不创建 tag