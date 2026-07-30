# Stage 7B-A — Baidu Map Provider Pilot · REPORT（结案报告）

> 日期：2026-07-25
> 阶段：Stage 7B-A
> 状态：**READY FOR INDEPENDENT RE-GATE**
> 决策：**维持 maplibre 为默认 Provider**（Baidu 仍为实验性选项，AK 不可用故未启用）

---

## 一、TL;DR

| 项目 | 状态 | 证据 |
|------|------|------|
| Baidu Provider 抽象 | ✅ 落地（契约层 + 错误面） | `providers/{types,index,MapProviderHost}.tsx` |
| Baidu Loader 单例 | ✅ 落地（含 ak-missing 守卫） | `providers/baidu/load-baidu-map.ts` |
| 五地 Pilot 坐标 | ✅ 5/5 WGS84 正确 | `stage7ba-baidu-pilot.test.ts` |
| Baidu Provider 浏览器实测 | ⚠️ BLOCKED（无真实 AK） | `.env.local` 无 `NEXT_PUBLIC_BAIDU_MAP_AK` |
| Dark contrast 修复 | ✅ 6+ token 对达标 WCAG-AA | `globals.css` 末尾新增 dark normalization 块 |
| 重复 Legend 删除 | ✅ MapShell 不再 import MapLegend | grep 验证 0 命中 |
| Stage 7R Gate 文档修复 | ✅ M1（SHA）+ L1（单位） | `STAGE7R-REGIONAL-HEATMAP-PROVENANCE.md` + `STAGE7R-CHANGEMANIFEST.json` |
| 全量回归 | ✅ tsc/lint/vitest/build 全绿 | 220/220 test, 0 warn, 14 routes |
| 默认 Provider 切换 | ❌ 未切换（维持 maplibre） | Baidu AK BLOCKED |
| 文档完整性 | ✅ 6 份中文文档齐 | docs/STAGE7B-A-*.md + .json |
| 服务停止 | ✅ dev server 已 kill | PID 28722 |

## 二、Stage 7R Gate 遗留修复

### M1 · PROVENANCE manifest SHA 不匹配

- **位置**：`docs/STAGE7R-REGIONAL-HEATMAP-PROVENANCE.md:34`
- **原值**：`c0b0573ef48e26f7d9c73a23cedde03d64718c371e083a8cb0451ce8a6b1b2bc`
- **新值**：`21e4c311784a455f00b2f4adaec20001495f6a5f6c0792132634ff71a77abb0b`
- **验证**：`shasum -a 256 data-pipeline/artifacts/stage7r-regional-heatmap/regional-data-manifest.json` 一致

### L1 · CHANGEMANIFEST 单位错误

- **位置**：`docs/STAGE7R-CHANGEMANIFEST.json`
- **修复 1**：`chinese_population.rawUnit` `"%"` → `"persons"`
- **修复 2**：`employment.rawDirection` `"inverse"` → `"direct"`（一并发现）

## 三、Provider 抽象（Stage 7B-A 范围）

**契约边界**：本轮不替换 MapCanvas（766 行）—— 高风险。Provider 抽象作为**适配层**先落地，未来 Stage 7B-B 逐步迁移。

```
MapProviderAdapter（interface）
├── id: "maplibre" | "baidu"
├── initialize(container, opts) → dispose
├── destroy / setCenter / setZoom / flyTo / fitBounds / getCenter / getZoom
├── onMove / onMoveEnd / onClick
├── addUniversityMarkers / updateUniversityMarkers / removeUniversityMarkers
├── setRegionalFill / clearRegionalFill
├── setSelectedRegion / setHoveredRegion
├── setTheme / resize / project / unproject
└── onError(MapProviderError) / onReady()
```

**MapProviderHost** 行为：

1. 读 `NEXT_PUBLIC_PATHOS_MAP_PROVIDER` 字面量
2. `baidu` + 无 AK → 自动 fallback 到 `MapLibreProviderAdapter`，surface `{ code: "ak-missing" }`
3. `baidu` + 有 AK → `BaiduMapProviderAdapter`，但海外 polygon 在 v3.0 限制下 `setRegionalFill` 仍为 no-op
4. `maplibre` → 直走 `MapLibreProviderAdapter`（当前唯一活跃路径）

## 四、百度 AK 状态 — BLOCKED

| 检查 | 结果 |
|------|------|
| `.env.local` 中存在 `NEXT_PUBLIC_BAIDU_MAP_AK`？ | ❌ 不存在 |
| `.env.local` 中存在 `NEXT_PUBLIC_PATHOS_MAP_PROVIDER`？ | ❌ 不存在（走默认 maplibre） |
| `.env.example` 提供合法占位？ | ✅ 提供空字符串占位 |
| 任何代码 / Git / 文档 / 日志中出现真实 AK？ | ❌ 无 |
| 用户可自助启用？ | ✅ 配置 AK 后即可切换 |

**结论**：百度浏览器实测 = **BLOCKED**。本轮**不能声称百度迁移完成**，仅完成 Provider 抽象的"骨"。

## 五、五地 Pilot

| 大学 | City | Lng | Lat | 数据可信 | WGS84 |
|------|------|-----|-----|---------|------|
| Harvard | Cambridge, MA | -71.118313 | 42.374471 | ✅ | ✅ |
| Columbia | New York, NY | -73.961885 | 40.808286 | ✅ | ✅ |
| Stanford | Stanford, CA | -122.167359 | 37.429434 | ✅ | ✅ |
| U Chicago | Chicago, IL | -87.599539 | 41.787994 | ✅ | ✅ |
| Arizona State | Tempe, AZ | -111.934383 | 33.417721 | ✅ | ✅ |

**重要**：5 个坐标均为 WGS84（lng 先 lat 后）。本轮**未**做 GCJ02/BD09 转换（US 数据不需要）。Stage 7B-B 真要切百度时，海外 polygon 仍需评估。

## 六、Dark Contrast Audit 摘要

详见 [`STAGE7B-A-DARK-CONTRAST-AUDIT.md`](./STAGE7B-A-DARK-CONTRAST-AUDIT.md)。

修复前后对比（节选）：

| Token Pair | Before (dark) | After (dark) | WCAG |
|------------|---------------|--------------|------|
| `bg-white` / `text-ink` | 1.14:1 | 13.2:1 | AA |
| `bg-paper` / `text-text-primary` | 1.20:1 | 12.9:1 | AA |
| `bg-panel/88` / `text-text-secondary` | 1.18:1 | 12.1:1 | AA |

## 七、Map UI Consolidation

**修复前**：左下角 `MapLegend`（渐变条）+ 右下角 `RegionalLegend`（带 chip 切换） → 信息重复，视觉拥挤
**修复后**：仅保留右下角 `RegionalLegend`（唯一权威）

为什么不是 `MapLegend`？
- RegionalLegend 是 Stage 7R 新设计（4 metric chip · 渐变条 · 极值 · 数据源脚注）
- MapLegend 是 Stage 5 旧实现（仅渐变条，无 chip 切换）
- RegionalLegend 右下角位置与未来百度版权 `CopyrightControl` 不冲突

## 八、Provider 对比结论

详见 [`STAGE7B-A-MAP-PROVIDER-COMPARISON.md`](./STAGE7B-A-MAP-PROVIDER-COMPARISON.md)。

16 项评估：
- MapLibre：12 项 PASS · 4 项 N/A（自身没有版权水印，无海外限制，无配额，无 AK）
- Baidu：3 项 PASS · 8 项 BLOCKED（无 AK） · 5 项 PASS-Architectural（接口/Loader 落地）

**默认 Provider**：维持 **maplibre**。

## 九、未做 / 待 Stage 7B-B

1. 真用 Baidu 渲染 5 个大学 marker（需 AK + Referer 白名单）
2. Baidu 海外 polygon overlay 验证
3. 把 MapCanvas 拆为 provider1 + provider2 + adapter
4. 删除 MapLegend 文件本身（暂保留以备 fallback）
5. 真实百度版权条渲染

## 十、风险

- **低**：CSS `!important` 重映射 — 未来若 Tailwind 调色板改动，需同步审查 dark normalization 块
- **中**：Provider 抽象的 `MapProviderHost` 仅在 React 树内生效；Stage 7R 的 `RegionalStateLayer` 仍硬编码 MapLibre，未来替换需双轨过渡
- **中**：百度 AK 一旦配置，**海外服务可能受限**（需在用户可见层显式说明）

## 十一、独立 Re-Gate 清单

请独立 Re-Gate 工程师验证：

- [ ] 本文件 + 5 份配套文档内容一致
- [ ] 6 份 SHA256 落盘
- [ ] tsc / lint / vitest / build 全绿（命令：`cd frontend && npm run check && npm run build`）
- [ ] `.env.example` 含 `NEXT_PUBLIC_PATHOS_MAP_PROVIDER=maplibre` 与空 AK 占位
- [ ] `MapShell.tsx` 不再 `from "./MapLegend"`
- [ ] `globals.css` 末尾有 Stage 7B-A dark normalization 块
- [ ] `providers/baidu/load-baidu-map.ts` 中 `BaiduLoadError` 不含 AK
- [ ] dev server 已停止（端口 3002 释放）
- [ ] `.env.local` 未被修改
- [ ] **无真实 AK 出现在 Git / 文档 / 日志**

---

**本轮结束。等待独立 Re-Gate。**