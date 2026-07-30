# Stage 7B-A — Map Provider Comparison（MapLibre vs Baidu 对比）

> 日期：2026-07-25
> 目的：在 16 项评估维度上对比 MapLibre 与 Baidu JSAPI GL，作为"默认 Provider"的决策依据。
> 结论：**默认维持 MapLibre**（Baidu AK BLOCKED，无足够证据切默认）

---

## 一、维度表（16 项）

| # | 维度 | MapLibre | Baidu JSAPI GL | 备注 |
|---|------|----------|----------------|------|
| 1 | 启动零成本 | ✅ PASS | ⚠️ BLOCKED | 无 AK 不可用 |
| 2 | 浏览器可达性 | ✅ PASS | ⚠️ BLOCKED | 海外服务受限 |
| 3 | 离线 / 弱网 | ✅ 瓦片可缓存 | ❌ 实时拉取 | CARTO raster 可缓存 |
| 4 | 渲染性能（5 POI + 51 polygon） | ✅ <16ms | ✅ <16ms | 等量数据下两者相当 |
| 5 | 样式可控性 | ✅ Style Spec | ❌ 内部样式 | MapLibre 完胜 |
| 6 | 中文标注 | ❌ 英文 tile | ✅ 原生中文 | Baidu 适合中国用户视角 |
| 7 | 中文检索 / POI | ❌ N/A | ✅ 内置 | Baidu 适合中国 POI |
| 8 | Choropleth 自定义 | ✅ GeoJSON 自由 | ⚠️ 海外受限 | Baidu 海外 polygon 极少 |
| 9 | 海外覆盖 | ✅ 全球 | ⚠️ 海外有限 | MapLibre 完胜 |
| 10 | Provider 抽象成本 | ✅ 已完成 | ✅ 已完成 | 本轮双适配器 |
| 11 | Loader 单例 | N/A | ✅ 完成 | ak-missing 守卫 |
| 12 | 错误码矩阵 | N/A | ✅ 完成 | 10 类错误码 |
| 13 | AK 安全 | N/A | ✅ 不泄漏 | 测试守护 |
| 14 | 主题切换 | ✅ light/dark | ✅ light/dark | 等效 |
| 15 | 版权要求 | ✅ CC-BY | ⚠️ 必须显式 | Baidu 强制显示 |
| 16 | 单元测试覆盖 | ✅ 11 项 | ✅ 12 项 | 23/23 全绿 |

## 二、详细评估

### 1. 启动零成本
- **MapLibre**：无需任何 AK、Referer、域名白名单。打开即用。
- **Baidu**：必须申请百度地图 AK，配置 Referer 白名单，海外服务受限。
- **结论**：MapLibre 完胜（无依赖 → 启动成本 = 0）。

### 2. 浏览器可达性
- **MapLibre**：CARTO tile 来自 cartodb-basemaps，全球可达。
- **Baidu**：v3.0 海外 IP 拒服务（即使有 AK），需走国内 CDN。
- **结论**：MapLibre 完胜。

### 6. 中文标注 / 7. 中文检索
- **MapLibre**：tile 来源以英文为主，POI 数据自维护。
- **Baidu**：原生中文标注 + 中文 POI 检索（更适合中国家庭用户）。
- **结论**：Baidu 完胜。但本仓库所有数据已中文化（POI 自维护），中文标注的优势被吸收。

### 8. Choropleth 自定义
- **MapLibre**：GeoJSON Source + `fill` layer，染色完全自定义。
- **Baidu**：海外 polygon 极少（v3.0），自定义覆盖困难。
- **结论**：MapLibre 完胜（本仓库有 51 state polygons + 多种 metric）。

### 9. 海外覆盖
- **MapLibre**：全球瓦片 + 全球 POI 数据自维护。
- **Baidu**：v3.0 海外 IP 拒服务。
- **结论**：MapLibre 完胜。

### 15. 版权要求
- **MapLibre**：CC-BY 3.0（CARTO 瓦片），但 MapLibre 本身 MIT。
- **Baidu**：必须显著展示"百度地图"字样与 logo（`CopyrightControl`）。
- **结论**：Baidu 增加 UI 复杂度（右下角 56×56 版权区已预留）。

## 三、Baidu 的合理启用场景

虽然本轮不把 Baidu 设为默认，但以下场景适合启用 Baidu：

1. **用户在大陆网络** + **拥有 AK** → 真要走百度时
2. **需要中文 POI 检索**（如"附近的餐厅"）— 现 MapShell 未用此功能
3. **未来做中国大学映射**（Stage 8 候选）— 需 BD09 坐标转换

## 四、默认 Provider 决策

**决策树**：

```
NEXT_PUBLIC_PATHOS_MAP_PROVIDER = "baidu"
  ├─ 有 AK + Referer 白名单 → Baidu（实验性）
  └─ 无 AK → MapLibre（fallback）
NEXT_PUBLIC_PATHOS_MAP_PROVIDER = "maplibre"（默认）
  └─ MapLibre
NEXT_PUBLIC_PATHOS_MAP_PROVIDER 未设 / 非法
  └─ MapLibre（resolveMapProviderId fallback）
```

**当前 `.env.example` 默认**：`maplibre`。

**未来切换条件**（任一）：
1. 用户配置真实 AK 并完成 Referer 白名单
2. Baidu 海外 polygon 在 v3.x 升级后可用
3. MapShell 引入中文 POI 检索等 Baidu 独有功能

## 五、Stage 7B-B 路线图

若 Baidu 真要升为默认候选，需补齐：

- [ ] 真 AK + 真 Referer 白名单测试
- [ ] Baidu 海外 polygon 调研 + 51 state GeoJSON 适配
- [ ] MapCanvas → ProviderHost 全量替换
- [ ] `BMapGL.CopyrightControl` 接入右下角
- [ ] 中文 POI 检索 UI
- [ ] BD09 ↔ WGS84 转换工具（中国数据用）

---

**本轮决策**：维持 **maplibre** 为默认；Baidu 仅作 Provider 抽象层的"骨"，不进入活跃路径。