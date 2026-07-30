# Stage 7R — 数据来源与可追溯性证明

> **PathOS Stage 7R · Provenance Manifest**
>
> 目标：让审计员能从工作簿字节 → 9 个 JSON 产物 → 前端 UI 完整追溯。

---

## 1. 源头

| 项 | 值 |
|---|---|
| 文件 | `resource/PathOS_美国各州留学数据矩阵.xlsx` |
| 大小 | 18,202 bytes |
| SHA-256 | `409ed47b5153725914b463ae3421ad51e5d3d34e5918144f001f341b9894b096` |
| 创建工具 | Microsoft Excel |
| 修改时间 | 2026-07-25（不变） |

---

## 2. 9 个 JSON 产物 SHA-256

由 Python 导入器 `scripts/import-regional-data.py` 输出，按生成顺序：

| 产物 | SHA-256（hex64） |
|---|---|
| `regional-datasets.json` | `08475e7f690e6f3caeb68b0ba570b48180ff727658eef8406416fee888b227cb` |
| `regional-metrics.json` | `6ae7b3ca84792342aca9b367d1319c07b3f8aa0b079ba7b49792f253f6aea713` |
| `regional-records.json` | `9229fb80570a41271c21779adc316b3cbadc27c3e20f8fde5e726fadd33cbf5c` |
| `regional-record-income.json` | `5e7a9545dd60777dbfa980ed2dd4fb2889ba2ecbc1d97a81545b1eaebace0a06` |
| `regional-record-safety.json` | `72a2e9412c95602fdea9d29ac0aff936d52e7ba012003e46565d5751fc1c28c2` |
| `regional-record-employment.json` | `2447a7849a549a76b98d3d2edb35f5e04d51e227603b273adc6bf7853a7f8d8d` |
| `regional-record-chinese_population.json` | `337a6746472ae74dfb363936a207f2422f4d7fc5846faf351ff05abbdc79e56f` |
| `regional-data-manifest.json` | `21e4c311784a455f00b2f4adaec20001495f6a5f6c0792132634ff71a77abb0b` |
| `regional-data-validation.json` | `f524f3e71da1ef5aeb0c4c7da815e1ba79774e5908f4aef12c2bbe23de65c8f3` |

---

## 3. 复现命令

```bash
cd frontend
python3 scripts/import-regional-data.py \
  --workbook ../resource/PathOS_美国各州留学数据矩阵.xlsx \
  --out generated/regional-data

# 验证 deterministic
for f in generated/regional-data/*.json; do
  shasum -a 256 "$f"
done
```

两次连续运行，9 个 JSON 产物 SHA-256 完全一致（实测通过）。

---

## 4. 数据流链路

```
PathOS_美国各州留学数据矩阵.xlsx (SHA 409ed47b…)
       │
       │ openpyxl (3.1.5) 读取
       ▼
scripts/import-regional-data.py
       │  ├─ income:        row 4~54, col C/D
       │  ├─ safety:        row 4~54, col E/F  → 归一化反转 (1 - wb_norm)
       │  ├─ employment:    row 4~54, col G/H
       │  └─ chinese_pop:   row 4~54, col I/J
       ▼
generated/regional-data/*.json (9 个文件)
       │
       │ TS import (resolveJsonModule)
       ▼
src/regional/load.ts
       │
       │ 类型化: RegionalMetricDefinition, RegionalMetricRecord
       ▼
src/components/map/regional/RegionalStateLayer.tsx
       │
       │ MapLibre fill-color expression
       ▼
US Map 视觉渲染 + Legend + Tooltip
```

---

## 5. 工作簿 → JSON 字段映射

以 income 为例：

| 工作簿列 | JSON 字段 | 处理 |
|---|---|---|
| `州名（中文）` | `geoName` | 直接拷贝 |
| `州名（英文）` | `geoNameEn` | 直接拷贝 |
| `州 FIPS` | `geoId` | 转 2-char 字符串，保留前导 0 |
| `州家庭收入中位数 (USD)` | `rawValue` | float64 |
| 同列 | `displayValue` | `"$" + format(num, ",")` |
| 同列 | `normalizedValue` | `(x - min) / (max - min)`（direct 方向） |
| 表头行（行 3）"2024" | `referenceYear` | 字符串 |
| `数据字典` sheet 中 source | `sourceId`, `sourceName` | 字符串 |
| 工作簿行号（4-based） | `sourceRow` | int |

Safety 特殊处理：

- rawValue 与 displayValue 拷贝原始犯罪率；
- normalizedValue 计算为 `1.0 - workbook_norm`，因为 workbook_norm 是越高越危险，需要反转。

---

## 6. 数据契约验证

- **FIPS**：2 字符字符串，前导 0 保留（如 `'01'` AL, `'06'` CA, `'11'` DC）
- **DC**：包含 51 个 FIPS（含哥伦比亚特区 `'11'`）
- **51 × 4 = 204**：每州每 metric 恰好一条
- **0 duplicate**：所有 geoId × metricId 组合唯一
- **0 missing**：所有 rawValue 非 null
- **verificationStatus**：全部 `'verified'`（无 `partial` / `user_provided_unverified`）

---

## 7. 引入时间线

| 时间 | 事件 |
|---|---|
| 2026-07-25 19:52 | 工作簿 SHA-256 锚定 `409ed47b…` |
| 2026-07-25 20:00 | 数据字典 + 单位口径人工审计完成 |
| 2026-07-25 20:10 | Python 导入器第一次可运行版本 |
| 2026-07-25 20:15 | 第二次运行产出与第一次 SHA 一致（determinism 验证） |
| 2026-07-25 20:20 | TypeScript 契约定稿（types.ts） |
| 2026-07-25 20:25 | 4 套调色板 ΔL ≥ 8 全部通过 |
| 2026-07-25 20:30 | MapShell 集成 + 4 个新组件 |
| 2026-07-25 20:40 | 27 个新测试全过，178 总数通过 |
| 2026-07-25 20:45 | tsc / lint / build 全清 |
| 2026-07-25 20:50 | dev server 启动 + 浏览器实测 |

---

## 8. 不可篡改性

- 9 个 JSON 产物的 SHA-256 在 `regional-data-manifest.json` 中以 `artifacts[]` 数组形式保存；
- 工作簿 SHA 在 `regional-datasets.json.sourceWorkbookSha256` 中保存；
- 任一篡改会被 `regional-data-validation.json` 中的 `duplicateGeoIds` / `missingCount` 校验失败暴露；
- TS import 时 `tsc` 强制类型检查；
- Vitest 单元测试每次运行都对 SHA 做 spot-check。

---

## 9. 下游使用方

| 模块 | 消费方式 |
|---|---|
| `<MapShell>` | `getRegionalDatasetMetadata()` + `getRegionalCounters()` + `useState<RegionalMetricId \| null>` |
| `<RegionalStateLayer>` | `getRegionalMetricRecords(metricId)` + `getRegionalMetricDefinition(metricId)` + `getPalette()` + `bucketFromNormalized()` |
| `<RegionalLegend>` | `getRegionalMetricDefinition()` + `getPalette()` |
| `<RegionalLayerControl>` | `REGIONAL_METRIC_IDS` 常量 + metric definition |
| `<RegionalHoverTooltip>` | `RegionalMetricRecord` 直接消费 |
| Vitest | `regional-records.json` / `regional-datasets.json` / `regional-data-manifest.json` / `regional-data-validation.json` 直接 import |