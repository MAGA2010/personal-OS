# PathOS — 留学选校决策平台

面向中国家庭的美国留学交互式数据平台。

## Pages

| 路由 | 功能 | 状态 |
|------|------|:----:|
| / | 首页 — 品牌展示 + 6大指标卡片 | ✅ |
| /map | 交互式地图 — 色块图 + 大学POI + 对比面板 | ✅ |
| /map/rankings | 四大排名对比（QS/ARWU/USNews/THE） | ✅ |
| /calculator | **留学预算计算器** — 选大学 + 生活费档次 + 按州调整物价 | ✅ |
| /match | **SmartMatch 智能选校** — 6维权重匹配引擎 | ✅ |

## Quick Start

`ash
cd frontend
npm install
npm run dev
# → http://localhost:3000
`

## Tech Stack

Next.js 14 · TypeScript · Tailwind CSS · MapLibre GL JS · D3 · Lucide Icons

## What's New (2026-07-13~14)

### 🗺 Map Enhancements
- **指标替换**: 托福/SAT → **就业指数**（基于BLS各州失业率数据）、**留学成本**（基于各大学COA）
- **修复图层切换bug**: COLOR_INTERPOLATORS 未同步导致切换指标时地图色块不更新

### 🧮 Budget Calculator /calculator
- 选 1-3 所大学自动填入学费
- 低/中/高三档生活费标准
- **按州物价系数调整**（基于收入数据推算，加州×0.94 vs 印第安纳×0.62）
- USD/RMB 双显示，一键复制结果
- 展开「查看计算过程」展示完整公式

### 🧠 SmartMatch 智能选校 /match
- 6 维评分引擎：费用/排名/安全/就业/华人社区/录取难度
- 拖拽滑条实时调整权重，结果即时重排
- 每所大学显示分项得分 bar
- 数据全部来自已有 JSON，无需后端

### 📊 ComparePanel 增强
- 替换 emoji 为 lucide 图标
- 新增「认可度」对比维度
- 2 所以上自动显示总费用对比条形图
- 清理遗留的 toeflMin/satMedian 引用

### 🏠 Landing Page 改版
- 6 大指标小卡片（带色条和描述）
- 数据统计行（40所大学·18州·6指标）
- 3 个CTA入口（地图/排名/计算器/匹配）

## Data

- rontend/src/data/universities.json — 40所大学POI（学费/安全/排名等）
- rontend/src/data/region-metrics.json — 51州 × 5指标（收入/安全/就业/成本/华人）
- rontend/src/data/university-rankings.json — QS/ARWU/USNews/THE排名
- rontend/src/data/news.json — 留学资讯文章

## Architecture

- "use client" 仅用于需浏览器API的组件
- MapLibre 地图实例通过 React Context 共享
- 所有数据通过 JSON 文件导入，组件与数据严格分离
- 中文为主、英文为辅的国际化方案