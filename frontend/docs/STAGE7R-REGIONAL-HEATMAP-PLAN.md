# Stage 7R — 区域热力图审计与集成 实施方案

> **PathOS Stage 7R · 单工作簿数据审计 + 区域热力图前端集成**
>
> 目标：在已有 Stage 7A 主题与边界修复基础上，引入 4 个独立的州级热力图（收入 / 安全 / 就业 / 华人社区），同时确保：
>
> 1. 区域数据**不进入**自主匹配分数（match）与 AI 评估（assessment）；
> 2. 浅色 / 深色模式视觉合规（WCAG-AA ΔL ≥ 8）；
> 3. 数据来源可追溯、可复现、可审计。

---

## 1. 范围

| 项 | 范围 |
|----|------|
| 数据源 | `resource/PathOS_美国各州留学数据矩阵.xlsx`（唯一工作簿） |
| 输出 | 4 个州级 metric × 51 个州/特区 = 204 条记录 |
| 排除 | `admission_rate`（工作簿未提供，BLOCKED）、`toefl`、`sat`（阶段 7R 不在范围） |
| 前端集成 | `RegionalStateLayer` + `RegionalLayerControl` + `RegionalLegend` + `RegionalHoverTooltip` |

---

## 2. 数据审计流程

1. 工作簿 SHA-256 计算（`409ed47b…`），作为审计基准；
2. `openpyxl` 读取三个 sheet：`美国各州留学数据` / `数据字典` / `单位与口径说明`；
3. 每个 metric 的列定位（行 3 = 表头，行 4 起为数据）；
4. 缺失值检测、范围检查、方向判定；
5. 输出 4 档评级：
   - **READY** — 51/51 数据齐全
   - **PARTIAL** — 部分缺失
   - **BLOCKED** — 数据口径不达标（如 admission_rate）
   - **OUT_OF_SCOPE** — 不在本阶段范围

---

## 3. 4 个 READY 指标

| 指标 ID | 显示名（zh） | rawUnit | 方向 | 原始值范围 |
|---|---|---|---|---|
| `income` | 州家庭收入中位数 | USD | direct（越高越好） | $55k – $91k |
| `safety` | 每10万人暴力犯罪率 | per 100k | **inverse**（越低越好） | 110.6 – 780.5 |
| `employment` | 州失业率 | % | inverse | 2.4% – 5.6% |
| `chinese_population` | 华人人口占比 | % | direct | 0.1% – 4.6% |

---

## 4. Safety 反向标准化（关键决策）

工作簿元数据写"倒数"，但 raw value 是**犯罪率原始值**（不是倒数）。处理方法：

- `rawValue` 保留原始犯罪率（110.6 ~ 780.5），不改；
- `displayValue` 同步保留（如 "110.6/10万"）；
- `normalizedValue` 由导入器计算：`our_norm = 1.0 - workbook_norm`，保证最低 crime → 最高 norm；
- 在 `RegionalMetricDefinition.longDescription` 中明示"越高越安全"。

这避免"raw 数字看起来越高反而越安全"的用户困惑。

---

## 5. 架构与文件

```
frontend/
├── scripts/
│   └── import-regional-data.py     # 确定性 Python 导入器
├── generated/regional-data/
│   ├── regional-datasets.json      # 数据集元数据
│   ├── regional-metrics.json       # 4 个 metric 定义
│   ├── regional-records.json       # 204 条全量
│   ├── regional-record-{id}.json   # 4 个 metric 的拆分文件
│   ├── regional-data-manifest.json # 全部 SHA-256 + 工作簿 SHA
│   └── regional-data-validation.json # 校验报告
├── src/regional/
│   ├── types.ts                    # TS 类型契约
│   ├── palettes.ts                 # 4 套调色板（light+dark）
│   └── load.ts                     # JSON 加载器
└── src/components/map/regional/
    ├── RegionalStateLayer.tsx      # MapLibre 填充层
    ├── RegionalLayerControl.tsx    # 顶部下拉控件
    ├── RegionalLegend.tsx          # 右下角图例
    └── RegionalHoverTooltip.tsx    # 跟随鼠标的 tooltip
```

---

## 6. 视觉规范

每个 metric 一套独立色族，浅色 / 深色模式分别调色，避免共用：

| metric | 色族 | 5 个色阶 | missing 灰 | hoverOutline |
|---|---|---|---|---|
| income | 绿 | pale mint → deep jade | `#e2dfd6` / `#3b4148` | `#0f4f37` / `#d6ffc6` |
| safety | 蓝 | pale ice → deep navy | 同上 | `#0f2f5f` / `#d8efff` |
| employment | 紫 | pale lavender → deep violet | 同上 | `#2c154d` / `#ebd6ff` |
| chinese_population | 橙 | pale apricot → persimmon | 同上 | `#5c2410` / `#ffd9bd` |

每个相邻色阶 ΔL ≥ 8（WCAG-AA），实测 32 对全部通过。

---

## 7. 与 Match / Assessment 的边界

- 4 个 metric 的 `usedForMatch = false`、`usedForMap = true`；
- `/match` 与 `/assessment` 页面均显示"区域指标仅在地图上作环境参考，未计入自主匹配/AI 评估分数"的显式声明；
- Stage 7A 的边界文案保留不变。

---

## 8. 验收检查项

| # | 检查 | 期望 |
|---|---|---|
| 1 | vitest | 178/178（151 Stage 7A + 27 Stage 7R） |
| 2 | tsc --noEmit | 0 错误 |
| 3 | next lint | 0 warning |
| 4 | npm run build | 成功，15 个静态页生成 |
| 5 | 工作簿 SHA | `409ed47b…` 与 manifest 一致 |
| 6 | 4 个 metric 各 51 条 | 204 总数 |
| 7 | safety inversion | Maine(raw=110.6) norm 最大 |
| 8 | boundary copy | `/match` + `/assessment` 显示区域边界声明 |
| 9 | hydration | `<html class="dark" data-theme="dark">` 与 colorScheme 一致 |
| 10 | 调色板 ΔL | 32 对全部 ≥ 8 |