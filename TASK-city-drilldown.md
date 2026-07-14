# PathOS 地图模块 — 城市下钻功能开发任务书

> 发给队友前请确认：本文档对应 GitHub 仓库 `MAGA2010/PathOS`，commit `aeb3db5`

---

## 一、项目背景

PathOS 是一个面向中国家庭的美国留学数据平台。当前已完成的子模块是**交互式地图**，包含：

| 模块 | 状态 | 说明 |
|------|------|------|
| 州级色块图（Choropleth） | ✅ 完成 | MapLibre + TopoJSON，5 个指标色层 |
| 指标切换 Tab | ✅ 完成 | 收入/安全/就业/成本/录取率/华人 |
| 图例 | ✅ 完成 | 渐变色条 |
| 大学列表（底部横条） | ✅ 完成 | 展示 40 所大学，点击弹出卡片 |
| 大学详情卡 | ✅ 完成 | 含学费/安全/认可度/排名 |
| 对比面板 | ✅ 完成 | 4 校对比表格 |
| 排名页 | ✅ 完成 | `/map/rankings` 四大排名 |
| 新闻侧边栏 | ✅ 完成 | 留学资讯 |
| **城市下钻（本次任务）** | ❌ 未开始 | 见下文 |

### 技术栈

```
Next.js 14 (App Router) + TypeScript + Tailwind CSS
MapLibre GL JS (地图渲染)
D3-scale-chromatic (色板)
TopoJSON / GeoJSON (地理边界)
lucide-react (图标)
```

### 目录结构（只列与本任务相关）

```
frontend/src/
├── lib/
│   ├── types.ts              ← 所有 TypeScript 类型定义
│   └── metrics.ts            ← 6 个指标的定义 + 格式化
├── data/
│   ├── universities.json     ← 40 所大学 POI 数据
│   ├── region-metrics.json   ← 51 州 × 5 指标的区域数据
│   └── university-rankings.json ← QS/ARWU/USNews/THE 排名
├── components/map/
│   ├── MapShell.tsx          ← 顶层编排器（状态中心）
│   ├── MapCanvas.tsx         ← MapLibre 初始化 + 色块图层
│   ├── MetricTabs.tsx        ← 指标切换 Tab 条
│   ├── MapLegend.tsx         ← 地图图例
│   ├── UniversityMarkers.tsx ← 大学横条 + 地图 Pin（含 UniversityMapPins）
│   ├── UniversityCard.tsx    ← 大学详情弹出卡
│   └── ComparePanel.tsx      ← 大学对比表格
└── app/map/
    ├── page.tsx              ← 地图路由 → 渲染 MapShell
    └── rankings/
        └── page.tsx          ← 排名页面
```

---

## 二、功能需求（三阶段下钻）

### 整体交互流

```
[地图：州级色块图]             ← 当前状态
      │ 点击某个州（e.g. 加州）
      ▼
[地图放大到该州 + 出现城市气泡层]   ← Part 1
      │ 气泡大小 = 大学数量
      ▼
[侧边栏打开城市详情面板]          ← Part 2
      │ 列出该州所有有大学的城市
      │ 点击某个城市
      ▼
[地图飞到该城市 + 大学 Pin 高亮]  ← Part 3
      │ 侧边栏显示该城市大学的详细信息
      │ 显示周边生活数据
```

### 详细需求

#### 需求 1：城市筛选（只显示有大学的城市）

- 从 `universities.json` 自动提取所有 (state, city) 对
- 只有数据里存在至少一所大学的城市才出现在系统中
- 当前覆盖：**18 个州，约 35 个城市，40 所大学**
- 参考城市分布：

```
CA: Berkeley, Davis, Irvine, La Jolla, Los Angeles, Pasadena, Santa Barbara, Stanford
MA: Boston, Cambridge, Chestnut Hill
NY: Ithaca, New York, Rochester
IL: Champaign, Chicago, Evanston
PA: Philadelphia, Pittsburgh, State College
TX: Austin, Houston
...其余见 universities.json
```

#### 需求 2：点击州 → 显示该州的大学城市

- 用户在色块图上点击某个州 → 触发 `onRegionClick(fipsCode)`（已实现）
- 当前行为：侧边栏显示该州所有大学列表
- **新行为**：
  - 地图平滑 zoom in 到该州范围（`map.flyTo()` 到州的中心+bounds）
  - 出现城市气泡层：每个有大学的城市画一个圆形标记
  - 气泡大小正比于该城市的大学数量
  - 气泡颜色使用该州在当前指标下的颜色
  - 侧边栏切换到"州内城市列表"视图

#### 需求 3：点击城市 → 显示该城市详情 + 大学

- 用户点击城市气泡 → 地图 smooth flyTo 到城市中心（zoom ≈ 10-12）
- 侧边栏显示城市详情面板：

```
┌──────────────────────────────────┐
│  ← 返回州级视图                   │
│                                   │
│  洛杉矶 Los Angeles, CA           │
│  ════════════════════════════════ │
│  📊 城市概况                      │
│  大学数量    2 所                  │
│  平均学费    ¥57万/年              │
│  平均安全分  74/100               │
│  平均录取率  12.5%                 │
│                                   │
│  🏫 该城市大学                    │
│  ┌────────────────────────┐      │
│  │  UCLA              →  │      │
│  │  加州大学洛杉矶分校      │      │
│  │  ¥50万 · 安全76 · 录取11% │    │
│  └────────────────────────┘      │
│  ┌────────────────────────┐      │
│  │  USC               →  │      │
│  │  南加州大学             │      │
│  │  ¥60万 · 安全72 · 录取13% │    │
│  └────────────────────────┘      │
│                                   │
│  🏪 周边生活                      │
│  中餐馆: ~15家   亚洲超市: ~8家    │
│  平均月租: ¥18,000                │
│  🚇 地铁站: 附近有                │
└──────────────────────────────────┘
```

- 每所大学可点击 → 弹出已有的 `UniversityCard`
- 点击某所大学后，地图上该大学的 Pin 高亮

---

## 三、技术方案

### 3.1 数据层：城市聚合

**新建类型**（建议放在 `src/lib/types.ts` 或新建 `src/lib/city.ts`）：

```typescript
// 从 universities.json 自动推导的城市聚合
export interface CityAggregate {
  id: string;                // "los-angeles-ca"
  name: string;              // "Los Angeles"
  nameZh: string;            // "洛杉矶"
  state: string;            // "CA"
  stateFips: string;        // "06"
  latitude: number;          // 城市中心(取该城市所有大学平均坐标)
  longitude: number;
  universityCount: number;
  universityIds: string[];   // ["ucla", "usc"]
  
  // 聚合指标（该城市大学平均值）
  avgAnnualCostRmb: number;
  avgSafetyScore: number;
  avgAdmissionRate: number;
  avgRecognitionScore: number;
  
  // 周边生活（取所有该城市大学的 nearby 平均值）
  chineseRestaurants: number;
  asianGroceries: number;
  avgRentRmb: number;
}
```

**聚合函数**（建议放在 `src/lib/city-utils.ts`）：

```typescript
import universities from "@/data/universities.json";

export function buildCityAggregates(): CityAggregate[] {
  // 1. 按 (state, city) 分组
  // 2. 计算每组平均坐标
  // 3. 计算聚合指标
  // 4. 返回 CityAggregate[]
}

export function getCitiesByState(fipsCode: string): CityAggregate[] {
  // 返回某州的所有城市
}

export function getCityById(cityId: string): CityAggregate | undefined {
  // 按 ID 查找城市
}

export function getUniversitiesInCity(cityId: string): UniversityPOI[] {
  // 返回某城市的所有大学
}
```

### 3.2 地图层：城市气泡（CityLayer.tsx）

**新建组件** `src/components/map/CityLayer.tsx`：

```typescript
"use client";

interface CityLayerProps {
  activeState: string | null;   // 当前选中州的 stateFips
  activeMetricId: MetricId;
  onCityClick: (cityId: string) => void;
  visible: boolean;             // 是否显示（进入城市模式时显示）
}
```

**内部逻辑：**
1. 使用 MapLibre `addSource` + `addLayer` 或 HTML Marker 渲染城市气泡
2. 气泡样式：
   - 直径：`20 + universityCount * 8`（最少 28px）
   - 颜色：使用 `metricColor(activeMetricId, avgValue)` 匹配当前指标
   - 内部数字：大学数量
   - hover/click 事件

**缩放同步：**
- 监听 `map.on("zoom")` 事件
- zoom < 4: 只显示州级色块
- zoom 4-7: 显示城市气泡 + 州边界线
- zoom > 7: 显示大学 Pin + 城市名标签

### 3.3 UI 层：城市详情面板（CityDetailPanel.tsx）

**新建组件** `src/components/map/CityDetailPanel.tsx`：

```typescript
"use client";

interface CityDetailPanelProps {
  city: CityAggregate;
  universities: UniversityPOI[];
  onBack: () => void;           // 返回州级视图
  onUniversitySelect: (id: string) => void;
  onAddToCompare: (id: string) => void;
}
```

**UI 规格：**
- 使用设计中已有的颜色 token：`ink`, `paper`, `panel`, `line`, `jade`, `persimmon`, `cobalt`
- 头部：城市名（中文+英文），返回按钮
- 指标卡片：2×2 网格，显示 4 个关键数字
- 大学列表：每个大学一个行，点击→`UniversityCard`。右侧带「对比」按钮
- 周边生活：图标+数字布局
- 字体：`text-xs` / `text-sm` / 中文优先

### 3.4 编排层：修改 MapShell.tsx

在 `MapShell.tsx` 中新增状态：

```typescript
// 新增状态
const [drillMode, setDrillMode] = useState<"state" | "city" | "university">("state");
const [selectedCityId, setSelectedCityId] = useState<string | null>(null);
const [selectedStateFips, setSelectedStateFips] = useState<string | null>(null);
```

**交互逻辑变更：**

```typescript
// 原有的 handleRegionClick 改为：
function handleStateClick(fipsCode: string) {
  // 1. 设置 drillMode = "city"
  // 2. 设置 selectedStateFips = fipsCode
  // 3. 地图 flyTo 到该州中心
  // 4. 侧边栏显示城市列表 → 调用 getCitiesByState(fipsCode)
  // 5. CityLayer 显示该州的城市气泡
}

function handleCityClick(cityId: string) {
  // 1. 设置 drillMode = "city"
  // 2. 设置 selectedCityId = cityId
  // 3. 地图 flyTo 到该城市中心
  // 4. 侧边栏显示 CityDetailPanel
  // 5. 地图上该城市气泡高亮
}

function handleBackToState() {
  // 1. 地图 flyTo 全美视图
  // 2. 清除城市选中状态
  // 3. 侧边栏回到新闻/区域详情
}
```

---

## 四、详细任务清单

### Step 1 — 数据工具函数（半天）

- [ ] 在 `src/lib/types.ts` 添加 `CityAggregate` 接口
- [ ] 新建 `src/lib/city-utils.ts`
- [ ] 实现 `buildCityAggregates()` — 从 universities.json 聚合
- [ ] 实现 `getCitiesByState(fipsCode)` — 按州查城市
- [ ] 实现 `getUniversitiesInCity(cityId)` — 按城市查大学
- [ ] 在浏览器 console 验证：`buildCityAggregates()` 返回 35 个城市

### Step 2 — 地图城市气泡层（1 天）

- [ ] 新建 `src/components/map/CityLayer.tsx`
- [ ] 读取 `CityAggregate[]` 数据
- [ ] 用 MapLibre `circle` layer 或 HTML marker 画城市气泡
- [ ] 气泡大小 = `20 + universityCount * 8`
- [ ] 气泡颜色 = 当前指标的 `metricColor`
- [ ] 气泡内文字 = 大学数量
- [ ] hover 显示城市名 tooltip
- [ ] click 调用 `onCityClick`
- [ ] 根据 zoom 级别显示/隐藏（`map.on("zoom")`）

### Step 3 — 城市详情侧边栏（1 天）

- [ ] 新建 `src/components/map/CityDetailPanel.tsx`
- [ ] 布局：返回按钮 + 城市名 + 概况指标网格 + 大学列表 + 周边生活
- [ ] 大学列表行：名称（中/英）+ 简要指标
- [ ] 点击大学 → 触发 `onUniversitySelect` → 弹出 `UniversityCard`
- [ ] 周边生活区域：餐厅/超市/租金

### Step 4 — 编排集成（1 天）

- [ ] 修改 `MapShell.tsx` 新增 `drillMode` / `selectedCityId` / `selectedStateFips` 状态
- [ ] 实现 `handleStateClick` → flyTo + CityLayer 显示 + 城市列表侧边栏
- [ ] 实现 `handleCityClick` → flyTo + CityDetailPanel
- [ ] 实现 `handleBackToState` → 恢复全美视图
- [ ] 侧边栏在三种模式下切换：
  - `"state"` → 新闻 feed 或区域详情（现有逻辑）
  - `"city"` → 城市列表
  - `"university"` → UniversityCard（现有逻辑）

### Step 5 — 动画与体验打磨（0.5 天）

- [ ] `map.flyTo()` 使用 `{ duration: 1500, zoom: 5.5 }` 飞入州级视图
- [ ] `map.flyTo()` 使用 `{ duration: 1000, zoom: 10 }` 飞入城市视图
- [ ] 城市气泡 enter/exit 动画（opacity transition）
- [ ] 侧边栏内容切换时使用 `transition-all duration-300`

---

## 五、设计规范（必须遵守）

### 颜色 token

| Token | Hex | 使用 |
|-------|-----|------|
| `ink` | `#152025` | 正文文字、激活态 |
| `paper` | `#f6f3ed` | 页面背景 |
| `panel` | `#fffaf1` | 卡片/面板背景 |
| `line` | `#d9d1c3` | 边框、分隔线 |
| `jade` | `#23766b` | 成功、正向 |
| `persimmon` | `#c45f36` | 警告、高亮 |
| `cobalt` | `#315d9f` | 信息、链接、强调 |

### 字体与间距

- 中文优先：所有标签用 `label`（中文）+ `labelEn`（英文）
- 字号：`text-xs`(12px) / `text-sm`(14px) / `text-base`(16px)
- 圆角：`rounded-lg`(8px) / `rounded-md`(6px) / `rounded-full`
- 阴影：`shadow-sm` / `shadow-panel`

### 国际化模式

所有 UI 文本使用中文为主、英文为辅：

```typescript
// ✅ 正确
<span>{city.nameZh}</span>
<span className="text-ink/48">{city.name}</span>

// ❌ 错误
<span>{city.name}</span>
```

### 图标

优先使用 `lucide-react` 图标：

```typescript
import { Building2, University, Train, UtensilsCrossed, Store, DollarSign } from "lucide-react";
```

---

## 六、验收标准

功能上线前应满足：

- [ ] 地图上点击任意州 → 出现该州的城市气泡
- [ ] 城市气泡只出现在 **有大学的城市**（数据驱动）
- [ ] 气泡大小反映大学数量
- [ ] 气泡颜色跟随当前选中指标
- [ ] 点击城市气泡 → 侧边栏显示城市详情面板
- [ ] 城市详情面板显示正确的聚合指标（平均学费/安全/录取率）
- [ ] 点击城市中的大学 → 弹出 UniversityCard
- [ ] 返回按钮 → 回到全美州级视图
- [ ] 所有交互有平滑动画（flyTo + opacity transition）
- [ ] 移动端侧边栏正常显示
- [ ] TypeScript 编译无错误（`npx tsc --noEmit`）
- [ ] 不修改 `types.ts` 中现有的 `MetricId`、`Granularity`、`UniversityPOI` 等类型

---

## 七、常见问题

**Q: 城市坐标怎么算？**
A: 取该城市所有大学的经纬度平均值。比如洛杉矶有 UCLA 和 USC，取两个坐标的均值。

**Q: 周边生活数据（中餐馆、超市）从哪来？**
A: 先读取 `universities.json` 里每所大学的 `nearby` 字段。如果为 `null`，就填 "数据待补充" 的占位文案。这部分后续再补全。

**Q: 城市气泡和现有大学 Pin 会重叠吗？**
A: 不会。它们在不同 zoom 级别出现：
- zoom < 5: 州级色块
- zoom 5-7: 城市气泡
- zoom > 7: 大学 Pin

**Q: 需要新建数据文件吗？**
A: 不需要。所有数据从已有的 `universities.json` 和 `region-metrics.json` 通过 JavaScript 聚合函数推导。不需要新建 JSON 文件或后端 API。

---

*任务书版本：v1.0 · 对应 commit aeb3db5 · 如有疑问请在 GitHub 上开 Issue 或直接 @Codex*
