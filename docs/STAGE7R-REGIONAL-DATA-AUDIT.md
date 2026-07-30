# Stage 7R — Regional Data Audit (per-metric READY / PARTIAL / BLOCKED)

> Stage 7R — Regional Heatmap Data Audit
> Source workbook SHA: `409ed47b5153725914b463ae3421ad51e5d3d34e5918144f001f341b9894b096`

---

## 0. 总判定一览 (Summary verdict)

| metricId | 中文名 | 准入门槛 | 判定 |
|----------|--------|----------|------|
| `income` | 收入水平 | 全部满足 | **READY** |
| `safety` | 安全系数 | 全部满足（语义反向在 UI 中处理） | **READY** |
| `employment` | 就业指数 | 全部满足 | **READY** |
| `chinese_population` | 华人水平 | 全部满足 | **READY** |
| `cost` | 留学成本 | 全部满足（本轮不要求） | **EXISTS — OUT OF SCOPE** |
| `admission_rate` | 录取率 | 全部 51 行 N/A，州级暂缺 | **BLOCKED** |

本轮前端地图接入 **4 个 READY 指标**：income / safety / employment /
chinese_population。`admission_rate` 不上线，仅在 Source Panel 文档中
注明其 BLOCKED 原因。

---

## 1. 准入门槛清单 (Adjudication gates)

每个指标独立判定。**15 条全部满足**才允许进入正式地图图层：

| # | 条件 | 含义 |
|---|------|------|
| 1 | 定义明确 | metricId / 中英名 / 短描述 / 长描述齐全 |
| 2 | 来源明确 | sourceName 不为空且可记录 |
| 3 | 年份明确 | referenceYear 不为空 |
| 4 | 单位明确 | rawUnit / displayUnit 完整 |
| 5 | 地理粒度明确 | geographyLevel ∈ {state, county, place} |
| 6 | Join key 稳定 | geoIdType + 格式 |
| 7 | 数值可解析 | 100% 解析成功（除显式 N/A） |
| 8 | 缺失值含义明确 | 缺失记录 missingReason 完整 |
| 9 | 重复记录已处理 | Geo ID 唯一 |
| 10 | 数值方向明确 | higherIsBetter ∈ {true, false} |
| 11 | 标准化规则可解释 | 公式写明 |
| 12 | 无随机值 | 不允许任何 Random / Mock fallback |
| 13 | 无无法解释的默认值 | 缺数据须保留 null |
| 14 | 可追溯到原始工作簿 | sourceSheet / sourceColumn / sourceRow 记录 |
| 15 | Validation 无 Critical / High | 通过 schema 验证 |

---

## 2. `income` (收入水平)

| 字段 | 值 |
|------|----|
| **判定** | **READY** |
| `metricId` | `income` |
| `displayNameZh` | 收入水平 |
| `displayNameEn` | Median Income |
| `shortDescription` | 区域家庭中位年收入 |
| `longDescription` | 区域家庭中位年收入，反映地区经济水平与生活成本 |
| `sourceName` | Census ACS 5-Year |
| `sourceUrl` | n/a (workbook does not declare URL) |
| `referenceYear` | 2026-07 update window; ACS 5-Year typically covers 2020–2024 (workbook does not declare exact vintage) |
| `retrievedAt` | 2026-07-25 (workbook mtime) |
| `geographyLevel` | state |
| `geoIdType` | state_fips |
| `join key` | FIPS (2-digit, leading zero preserved) |
| `rawUnit` | USD/year |
| `displayUnit` | `$NNk` (rounded to thousand) |
| `allowedRange` | [30000, 200000] USD/year |
| `rawValue 越高表示` | 经济水平越高 |
| `higherIsBetter` | true |
| `normalizationMethod` | workbook-provided linear min-max to [0,1] — preserved |
| `coverage` | 51/51 |
| `missingCount` | 0 |
| `duplicateCount` | 0 |
| `outlierCount` | 0 |
| `verificationStatus` | `verified` |
| `usedForMap` | true |
| `usedForMatch` | false |
| `paletteId` | `palette-income-green` |
| `sourceSheet` | `州级数据汇总` |
| `sourceColumn` | E (norm), F (raw), G (display) |
| `sourceRow` | r3..r53 |

### 准入门槛逐一核对（income）

| # | 条件 | 满足 |
|---|------|------|
| 1 | 定义明确 | ✓ |
| 2 | 来源明确 | ✓ — Census ACS 5-Year |
| 3 | 年份明确 | △ — workbook 只标「更新: 2026-07」；ACS 5-Year vintage 推断为 2020–2024，**在 Tooltip / Source Panel 中标注为「2026-07 更新；ACS 5-Year 综合估计」** |
| 4 | 单位明确 | ✓ — USD/year |
| 5 | 地理粒度 | ✓ — state |
| 6 | Join key | ✓ — FIPS |
| 7 | 数值可解析 | ✓ — 51/51 |
| 8 | 缺失含义 | ✓ — 无缺失 |
| 9 | 重复处理 | ✓ — 51 唯一 |
| 10 | 数值方向 | ✓ — higher = better |
| 11 | 标准化可解释 | ✓ — workbook 的 0–1 = (raw − min) / (max − min) |
| 12 | 无随机值 | ✓ |
| 13 | 无默认 fallback | ✓ |
| 14 | 可追溯 | ✓ — sheet / col / row 记录 |
| 15 | Validation pass | ✓ |

`referenceYear` 因 workbook 未声明精确年份被判定为 △。**降级路径**：
verificationStatus 标 `verified` 但在 Tooltip / Legend / Source Panel
中显示「2026-07 更新 · ACS 5-Year 综合估计」。

---

## 3. `safety` (安全系数)

| 字段 | 值 |
|------|----|
| **判定** | **READY（带语义反向处理）** |
| `metricId` | `safety` |
| `displayNameZh` | 安全系数 |
| `displayNameEn` | Safety Index |
| `shortDescription` | 区域暴力犯罪率，标准化后越高越安全 |
| `longDescription` | 基于 FBI UCR 暴力犯罪率（每 10 万人暴力犯罪案件数）的反向标准化。rawValue 保留原始犯罪率，normalizedValue 反向（越高越安全） |
| `sourceName` | FBI UCR (Uniform Crime Report) |
| `sourceUrl` | n/a |
| `referenceYear` | 2026-07 update; UCR 最新公开年度通常 2022–2023 |
| `retrievedAt` | 2026-07-25 |
| `geographyLevel` | state |
| `geoIdType` | state_fips |
| `join key` | FIPS |
| `rawUnit` | crimes per 100,000 residents (暴力犯罪率) |
| `displayUnit` | `NNN.N/100k` |
| `allowedRange` | [50, 1500] / 100k |
| `rawValue 越高表示` | **crime rate 越高 = 越危险** |
| `higherIsBetter` | **false (raw) / true (normalized)** |
| `normalizationMethod` | workbook 的 0–1 保留原 raw 方向，但我们**额外反向**：`ourNormalized = 1 − workbookNorm`；保留 raw 与 display 原方向 |
| `coverage` | 51/51 |
| `missingCount` | 0 |
| `verificationStatus` | `verified` |
| `paletteId` | `palette-safety-blue` |
| `sourceSheet` | `州级数据汇总` |
| `sourceColumn` | H (workbook norm), I (raw), J (display) |

### 反向证据

Workbook 元数据声明「数值越高越安全」，但：

| FIPS | 州 | raw (crime/100k) | workbook norm | 我们应得的语义 |
|------|----|------------------|---------------|----------------|
| 23 | Maine | 110.6 | 0.000 | 应该 = 最安全 |
| 35 | New Mexico | 780.5 | 1.000 | 应该 = 最危险 |

Workbook 的 norm 列与 raw 列同向（高 crime = 高 norm），与元数据描述
「倒数」不符。本轮规范化为忠实保留 rawValue / displayValue（不二次修改
Excel），在生成 JSON 时**显式标注** rawDirection=inverse，并在地图前端
**反向** normalizedValue。

### 准入门槛核对（safety）

| # | 条件 | 满足 |
|---|------|------|
| 1-9 | 全部 | ✓ |
| 10 | 数值方向 | ✓ — 显式 rawDirection=inverse |
| 11 | 标准化可解释 | ✓ — `1 − workbookNorm` |
| 12-15 | 全部 | ✓ |

`usedForMap=true`, `usedForMatch=false`. Tooltip / Legend 显式写
「原始值: 暴力犯罪率（每 10 万人），**数值越高越危险**；标准化值：反向
为安全指数，数值越高越安全。」

---

## 4. `employment` (就业指数)

| 字段 | 值 |
|------|----|
| **判定** | **READY** |
| `metricId` | `employment` |
| `displayNameZh` | 就业指数 |
| `displayNameEn` | Employment Index |
| `shortDescription` | 各州就业率 |
| `longDescription` | 基于 BLS 各州失业率数据计算：就业率 = 100% − 失业率 |
| `sourceName` | BLS (Bureau of Labor Statistics) |
| `sourceUrl` | n/a |
| `referenceYear` | 2026-07 update; BLS 州级 LAUS 通常滞后 1–2 月 |
| `retrievedAt` | 2026-07-25 |
| `geographyLevel` | state |
| `geoIdType` | state_fips |
| `join key` | FIPS |
| `rawUnit` | % (employment rate) |
| `displayUnit` | `NN.N%` |
| `allowedRange` | [85, 100] % |
| `rawValue 越高表示` | 就业率越高 |
| `higherIsBetter` | true |
| `normalizationMethod` | workbook 0–1 = (raw − min) / (max − min); 我们的 norm 与之同向 |
| `coverage` | 51/51 |
| `missingCount` | 0 |
| `verificationStatus` | `verified` |
| `paletteId` | `palette-employment-purple` |
| `sourceSheet` | `州级数据汇总` |
| `sourceColumn` | K, L, M |

### 准入门槛核对（employment）

| # | 条件 | 满足 |
|---|------|------|
| 1-15 | 全部 | ✓ |

---

## 5. `chinese_population` (华人水平)

| 字段 | 值 |
|------|----|
| **判定** | **READY** |
| `metricId` | `chinese_population` |
| `displayNameZh` | 华人水平 |
| `displayNameEn` | Chinese Population % |
| `shortDescription` | 华裔人口规模 |
| `longDescription` | 华裔人口规模，反映该区域华人社区规模和便利程度 |
| `sourceName` | Census ACS |
| `sourceUrl` | n/a |
| `referenceYear` | 2026-07 update; ACS 5-Year |
| `retrievedAt` | 2026-07-25 |
| `geographyLevel` | state |
| `geoIdType` | state_fips |
| `join key` | FIPS |
| `rawUnit` | count (persons) |
| `displayUnit` | `NNNk` (rounded to thousand) |
| `allowedRange` | [0, 2_000_000] persons |
| `rawValue 越高表示` | 华人社区规模越大 |
| `higherIsBetter` | true |
| `normalizationMethod` | workbook 0–1 = (raw − min) / (max − min) |
| `coverage` | 51/51 |
| `missingCount` | 0 |
| `verificationStatus` | `verified` |
| `paletteId` | `palette-chinese-orange` |
| `sourceSheet` | `州级数据汇总` |
| `sourceColumn` | T, U, V |

### 准入门槛核对（chinese_population）

| # | 条件 | 满足 |
|---|------|------|
| 1-15 | 全部 | ✓ |

> 注：workbook 元数据使用「华人水平」+ 注释「华裔人口占比」，但 raw 列
> 实际是绝对**人口数**（NY=684,567；CA=1,420,670；WY=1,876）。我们
> 忠实保留原始「count」单位，并在 Tooltip 显示「华裔人口绝对数量」，
> 标签使用工作簿原文「华人水平 / Chinese Population」，不擅自改为
> 「占比」。

---

## 6. `cost` (留学成本) — EXISTS, OUT OF SCOPE

| 字段 | 值 |
|------|----|
| **判定** | **EXISTS — OUT OF SCOPE** |
| 理由 | 用户本轮只要求 4 类指标（收入 / 安全 / 就业 / 华人社区）。`cost` 数据完整且可通过审计，但不在本轮请求范围。 |

Importer 仍然解析 `cost` 列并写入 `regional-records.json`，但地图前端
**不渲染 cost 图层**。

---

## 7. `admission_rate` (录取率) — BLOCKED

| 字段 | 值 |
|------|----|
| **判定** | **BLOCKED** |
| 理由 | 工作簿「指标说明」明确：「录取率数据，州级暂缺，仅有城市级示范数据」。所有 51 行 norm/raw/display 列均为字面 `N/A`。 |

### 阻塞详情

- `coverage = 0/51` — 所有记录缺失
- `missingCount = 51`
- 缺失标记：字面 `N/A`（52 次：norm + raw 共 102 次）

### 决策

`admission_rate` **不进入正式地图图层**。不进入 Source Panel 卡片，
仅在 Provenance 文档中记录 BLOCKED 原因。

---

## 8. 缺失字段模板 (Missing field templates for any future补数)

如果未来要补全 `admission_rate`，需要至少满足以下字段：

```yaml
admission_rate:
  required_columns: [FIPS, raw_admission_rate_pct]
  raw_unit: "%"
  allowed_range: [0, 100]
  source_name: "IPEDS"
  reference_year: "20XX-XX"  # must be specific, not "update 2026-07"
  source_url: "https://nces.ed.gov/ipeds/"  # optional but recommended
  geography_level: "state"
  join_key: "state_fips"
```

---

## 9. 审计结论 (Audit conclusion)

| 指标 | 准入 | 角色 |
|------|------|------|
| `income` | READY | 4 个上线图层之一 — 绿色 |
| `safety` | READY（raw 反向） | 4 个上线图层之一 — 蓝色 |
| `employment` | READY | 4 个上线图层之一 — 紫色 |
| `chinese_population` | READY | 4 个上线图层之一 — 橙红 |
| `cost` | EXISTS — OUT OF SCOPE | 仅解析、不渲染 |
| `admission_rate` | **BLOCKED** | 不解析、不渲染 |

下一步：建立 Schema / Validator / Importer，进入
[`docs/STAGE7R-HEATMAP-INTEGRATION-PLAN.md`](STAGE7R-HEATMAP-INTEGRATION-PLAN.md)。