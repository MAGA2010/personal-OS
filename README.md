# PathOS — 交互式留学地图模块 (Map Module)

> 这是 PathOS 整体项目中的**地图子模块**。PathOS 是一个面向中国大陆留学家庭的 AI 升学顾问平台，本模块负责其中的交互式地图部分。
>
> 仓库地址：[MAGA2010/PathOS](https://github.com/MAGA2010/PathOS)

---

## 模块定位：PathOS 中的地图子系统

```
PathOS 整体项目
├── 🗺️ 留学地图 (Map Module)  ← 当前模块
│   ├── Choropleth 面量图（六大指标图层）
│   ├── 学校 POI 精确标注
│   ├── 校园实景 / 街景沉浸
│   └── 侧边栏留学资讯
│
├── 🤖 AI 升学顾问 (Advisor Module)
│   ├── Agentic RAG 对话
│   ├── 选校矩阵生成
│   └── 学生画像分析
│
├── 📊 数据库 (Data Module)
│   ├── 院校结构化数据
│   ├── 区域地理指标数据
│   └── Supabase + pgvector
│
└── 👥 双重视角 (Parent / Student View)
    ├── 家长模式（重安全/就业/华人社区）
    └── 学生模式（重排名/生活/专业）
```

---

## 1. 地图模块定位

面向中国大陆留学家庭的**数据驱动交互式地图**，是 PathOS 的核心差异化功能。不同于市面上任何一个留学工具：

| 竞品 | 他们的做法 | 我们的做法 |
|------|-----------|-----------|
| Niche / US News | 列表 + 表格筛选 | **Choropleth 等值区域图**，像天气温度图一样直观 |
| 留学中介 (新东方/启德) | Excel + PDF | **六大指标图层切换**，点一下切换数据维度 |
| 小红书/知乎 KOL | 主观经验 | **数据引用源头可查**，每个数据带来源链接 |
| Google Maps | 纯地图 | **Choropleth 底色 + 学校POI标记叠加**，地图即分析工具 |

---

## 2. 功能架构（五层叠加）

```
┌──────────────────────────────────────────────┐
│  ⑤ 校园实景/街景沉浸                          │
│     Google Street View 360° 全景              │
│     校园POI：图书馆📍 食堂📍 宿舍📍           │
├──────────────────────────────────────────────┤
│  ④ 学校信息卡片                               │
│     🏫 哈佛大学 | Top 3 | ¥58万/年           │
│     周边：地铁3个 · 中餐12家 · 月租¥8000       │
├──────────────────────────────────────────────┤
│  ③ 学校POI标记层 (supercluster 聚合)           │
│     🏫──🏫────🏫                   🏫       │
├──────────────────────────────────────────────┤
│  ② Choropleth 面量图（六大指标可切换）         │
│     ████████▒▒▒▒▒▒▒▒░░░░░░░░░░░░░░░░        │
├──────────────────────────────────────────────┤
│  ① 底图 (MapLibre GL JS / CARTO Positron)    │
└──────────────────────────────────────────────┘
```

---

## 3. 六大指标图层

| # | 指标 | 配色 | 含义 | 数据来源 |
|---|------|------|------|----------|
| 1 | **收入水平** | 🟢 绿渐变 | 越深=区域越富裕 | Census ACS API |
| 2 | **安全系数** | 🔵 蓝 → 🔴 红 | 蓝=安全，红=高犯罪率 | FBI Crime Data API |
| 3 | **托福成绩** | 🔵 蓝渐变 | 越深=托福要求越高 | 大学官网 / Common Data Set |
| 4 | **SAT分数** | 🟣 紫渐变 | 越深=SAT分越高 | IPEDS / College Scorecard |
| 5 | **录取率** | 🟠 橙红 | 越深=越难进 | IPEDS |
| 6 | **华人水平** | 🟡→🔴 黄红 | 越深=华人占比越高 | Census ACS API |

缩放三级粒度：州级 (z0-6) → 县级 (z6-9) → 市级 (z9+)

---

## 4. 技术栈

| 层 | 技术 |
|----|------|
| 前端框架 | Next.js 14 (App Router) + TypeScript + Tailwind CSS |
| 地图引擎 | **MapLibre GL JS** (开源，免费无限量) |
| 色阶渲染 | D3 Scale Chromatic (10 阶平滑渐变) |
| 边界数据 | TopoJSON (us-atlas，简化为 112KB) |
| POI聚类 | Supercluster |
| 底图 | CARTO Positron (免费，无需 API Key) |

---

## 5. 目录结构

```
PathOS/
├── CLAUDE.md                           # Claude 项目文档
├── README.md                           # ← 本文件
├── MVP-Critical-Plan-Review.md         # MVP 产品评审文档
└── frontend/
    ├── package.json                    # 依赖清单
    ├── tailwind.config.ts              # 主题色配置
    └── src/
        ├── app/
        │   ├── page.tsx                # 首页/landing
        │   ├── layout.tsx              # 根布局 (zh-CN)
        │   └── map/
        │       ├── page.tsx            # /map 路由
        │       └── layout.tsx
        ├── components/map/
        │   ├── MapShell.tsx            # 顶层调度（711行）
        │   ├── MapCanvas.tsx           # MapLibre 地图初始化（403行）
        │   ├── MetricTabs.tsx          # 指标Tab切换
        │   ├── MapLegend.tsx           # 色阶图例
        │   ├── GranularityBadge.tsx    # 州/县/市粒度标签
        │   ├── UniversityMarkers.tsx   # 学校POI标记层
        │   └── UniversityCard.tsx      # 学校信息卡片
        ├── data/
        │   ├── universities.json       # ★ 学校数据骨架（待填充）
        │   ├── region-metrics.json     # ★ 区域指标骨架（待填充）
        │   └── news.json               # ★ 资讯骨架（待填充）
        ├── lib/
        │   ├── types.ts                # 全部类型定义（583行，27 种）
        │   └── metrics.ts              # 六指标配置 + Mock数据
        └── public/geography/
            └── us-states.topojson      # 美国州界 (112KB)
```

---

## 6. 开发状态

### ✅ 已完成的骨架（此 commit）
- **TypeScript 0 errors**，可直接编译
- 27 种类型/接口（types.ts，583行）
- 6 个指标定义 + 配色方案（metrics.ts）
- 7 个地图组件（MapShell, MapCanvas, MetricTabs, MapLegend, GranularityBadge, UniversityMarkers, UniversityCard）
- 3 个数据骨架文件（含完整示例+字段说明）
- 75+ TODO 标记，精确标注数据接入点
- US 州级 TopoJSON 边界文件

### ⏳ 待用户提供/爬取数据后即用
1. 真实学校数据 → `src/data/universities.json`
2. 真实区域指标 → `src/data/region-metrics.json`
3. 实时留学资讯 → `src/data/news.json`
4. 或爬虫脚本 → `data-pipeline/`

---

## 7. 快速启动

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000/map
```

---

## 8. 设计理念

> **数据与代码分离**：所有组件已完成，数据通过 3 个 JSON 文件接入。数据一到，无需修改任何代码即可运行。

> **TODO 标注精确**：每个待接入数据的位置都有明确的 `TODO: Replace with real {name} data` 标记，grep 即可定位。
