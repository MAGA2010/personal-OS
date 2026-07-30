# Stage 7B-A — Baidu Map Provider Pilot · PLAN（执行计划）

> 日期：2026-07-25
> 阶段：Stage 7B-A（实验性 · 不进默认）
> 状态：READY FOR INDEPENDENT RE-GATE · 不自我宣告 PASS

---

## 一、目标

在不破坏 Stage 7R 既有交付（Regional Heatmap · MapLibre Style · State/City · 4 种 Metric）的前提下，新增一组 **Map Provider 抽象**，并以 **Baidu JSAPI GL v3.0** 作为实验性 Provider 接入；同步清理 **深色模式对比度** 与 **重复 Legend** 两类历史遗留问题。

## 二、四条铁律（不可破坏）

1. **不动 .env.local** — 仅可在 `.env.example` 增加可空占位。
2. **不抢外部端口 3000/3010** — 仅可使用 3002 或后续 free port。
3. **真实 AK 不得进入** 源码 / Git / 文档 / 日志 / 截图 / Change Manifest / 测试 fixture。
4. **不自我宣告最终 PASS、不创建 tag、不 push。** 完成后停止本轮服务，等待独立 Re-Gate。

## 三、阶段（按 Begin Order）

| # | 任务 | 出口条件 |
|---|------|---------|
| 1 | Preflight + 资源状态确认 | PID/端口/磁盘 README |
| 2 | 修复 Stage 7R Gate 遗留 M1（PROVENANCE SHA）+ L1（CHANGEMANIFEST 单位） | 6 处 SHA、单位 "persons" |
| 3 | 复现重复 Legend + 定位来源 | 找到 MapShell 内 `<MapLegend>` 与 `RegionalLegend` 共存 |
| 4 | 完成 Dark Contrast Audit | body ≥4.5:1 · UI ≥3:1 · 收集 16 个 token 对 |
| 5 | 修复 Token 与图标 | 在 `globals.css` 加入 `.dark .bg-white/N → --token-surface-1` 重映射 |
| 6 | 建立 Provider 接口 | `MapProviderAdapter` TS interface + `MapProviderId` 字面量类型 |
| 7 | 建立百度 Loader | `load-baidu-map.ts` 单例 + 超时 + 错误面（无 AK 泄漏） |
| 8 | 检查 AK 状态 | `.env.local` 不存在真实 AK → BLOCKED |
| 9 | 五地 Pilot 对比 | Boston/Cambridge · NY · Bay Area · Chicago · Tempe/Phoenix |
| 10 | WGS84 坐标抽样验证 | 5 个 US 高校坐标在 [-180,-50]×[20,60] 矩形内 |
| 11 | 百度 Provider 接入州级 Polygon | 现状 = no-op（MapLibre 仍负责）；Baidu 适配器保留 `setRegionalFill` 钩子 |
| 12 | 保留四种热力图 | `income / safety / admission / chinese_population` 全部已实现 |
| 13 | 删除重复 Legend | `MapShell.tsx` 不再 import `MapLegend`；唯一权威 = `RegionalLegend` |
| 14 | 验证百度版权预留空间 + Responsive | 右下 56×56 padding；1280×720 / 375×812 实测 |
| 15 | 自动测试新增 + 回归 | 220/220 · tsc 0 · lint 0 · next build 14 routes |
| 16 | Browser matrix 真实实测 | /map /calculator /match /assessment /portfolio /news /university/* /404 |
| 17 | 决定默认 Provider | BLOCKED → 维持 `maplibre` |
| 18 | 输出 6 份中文文档 | PLAN/DEVLOG/REPORT/DARK-CONTRAST-AUDIT/MAP-PROVIDER-COMPARISON/CHANGE-MANIFEST.json |
| 19 | 停止本轮启动的服务 | dev server PID kill（指定 PID，非 pkill） |
| 20 | 等待独立 Re-Gate | 不自我宣告 PASS |

## 四、Provider 抽象最小契约

```
MapProviderAdapter
├── id: "maplibre" | "baidu"
├── initialize(container, opts) → dispose
├── destroy()
├── setCenter / setZoom / flyTo / fitBounds / getCenter / getZoom
├── onMove / onMoveEnd / onClick
├── addUniversityMarkers / updateUniversityMarkers / removeUniversityMarkers
├── setRegionalFill / clearRegionalFill / setSelectedRegion / setHoveredRegion
├── setTheme / resize / project / unproject
└── onError(MapProviderError) / onReady()
```

## 五、错误码（百度侧）

| Code | 触发条件 | 用户可见文案 |
|------|---------|-------------|
| ak-missing | `NEXT_PUBLIC_BAIDU_MAP_AK` 为空/空白 | "百度地图 AK 尚未配置" |
| ak-invalid | 401/403 from baidu | "AK 无效或被吊销" |
| referer-invalid | 403 Referer 不在白名单 | "请在百度地图后台添加当前域名到白名单" |
| overseas-unavailable | 海外 IP 拒服务 | "百度地图海外不可用" |
| service-disabled | 服务被禁用 | "百度地图服务暂不可用" |
| quota-exceeded | 配额耗尽 | "百度地图配额已达上限" |
| script-timeout | 15s 内未回调 init | "百度地图脚本加载超时" |
| script-load-error | script.onerror | "百度地图脚本加载失败" |
| tile-failure | tile 4xx/5xx | "百度瓦片加载失败" |
| not-implemented | 当前 round 不支持 | "此功能在 Baidu 适配器尚未实现" |

## 六、退出条件

- [x] 23/23 新增测试通过
- [x] tsc / lint / build 全部 0 警告
- [x] 6 份中文文档落盘
- [x] dev server 已停止（PID 28722）
- [ ] 独立 Re-Gate 通过 → 才进入 Stage 7B-B（Provider 全量替换 MapCanvas）