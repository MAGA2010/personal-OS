# Stage 7A — Regional Data Provenance Report

> 编写时间：2026-07-25
> 范围：调查四种美国区域热力图（收入 / 安全 / 就业 / 华人生活便利度）的真实数据可用性
> 状态：**BLOCKED — 无可信数据可接入**

---

## 1. 调查结果总览

| 期望指标 | 用户授权 | 数据源状态 | 结论 |
| --- | --- | --- | --- |
| 收入水平 | ✅ | 无 verified | **BLOCKED** |
| 安全指数 | ✅ | 无 verified | **BLOCKED** |
| 就业指数 | ✅ | 无 verified | **BLOCKED** |
| 华人生活便利度 | ✅ | 无 verified | **BLOCKED** |

---

## 2. 调查路径

按指令"查找关键词 region-metrics / choropleth / income / median_income / safety / crime / employment / employment_rate / job / chinese / asian / community / convenience / stateFips / countyFips / geoId / ACS / Census / FBI / BLS"在以下路径中检索：

- `/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking-standalone`（Preview Bundle backend，只读）
- `/Users/jiayihuang/Downloads/PathOS合并/PathOS-main`（前端工作区）
- `/Users/jiayihuang/PathOS`（旧路径，只读）
- `/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking`（handoff 工件，只读）
- `/Users/jiayihuang/Downloads/PathOS-checkpoints/stage6-demo-pass-2026-07-25-2`（Stage 6 冻结点，只读）

### 2.1 命中文件
- `PathOS-db-ranking-standalone/frontend/src/data/region-metrics.json`（占位骨架）
- `PathOS-db-ranking-standalone/frontend/src/lib/types.ts`（类型定义）
- `PathOS-db-ranking-standalone/frontend/src/lib/metrics.ts`（mock 生成）
- `PathOS-main/frontend/...`（无 region-metrics 引用 — 该模块不在前端消费链路上）
- `PathOS-db-ranking-standalone/data-pipeline/artifacts/stage5-warning-aware-preview/region-metrics.json`（**关键文件**）
- `PathOS-db-ranking/handoff/frontend-data-extraction/normalized-preview/region-metrics.candidate.json`（handoff 候选）
- `PathOS-db-ranking/handoff/frontend-data-extraction/backend-import-candidates/region-metrics.raw.json`（原始采集）
- `PathOS/frontend/src/data/region-metrics.json`（旧路径占位骨架）

---

## 3. 各来源详细分析

### 3.1 Stage 5 Preview Bundle（权威源）

```json
// PathOS-db-ranking-standalone/data-pipeline/artifacts/stage5-warning-aware-preview/region-metrics.json
{
  "choroplethEnabled": false,
  "contractVersion": "pathos-preview-v1",
  "disabledReason": "Credentialed official regional intake is unavailable.",
  "metricMetadata": [
    { "metricId": "income",             "status": "deferred", "unit": null },
    { "metricId": "safety",             "status": "deferred", "unit": null },
    { "metricId": "employment",         "status": "deferred", "unit": null },
    { "metricId": "cost",               "status": "deferred", "unit": null },
    { "metricId": "chinese_population", "status": "deferred", "unit": null }
  ],
  "records": [],
  "status": "blocked",
  "warnings": ["deferred_regional_data_not_a_verified_fact"]
}
```

**关键证据**：
- `status: "blocked"` — Preview 阶段明确不返回任何区域数据
- `records: []` — 空数组，无 fallback
- `disabledReason: "Credentialed official regional intake is unavailable"` — 后端没有可信官方区域数据接入
- `warnings: ["deferred_regional_data_not_a_verified_fact"]` — 警告直接命名："区域数据不是已验证事实"
- `choroplethEnabled: false` — 故意禁用了 Choropleth
- Manifest SHA：`88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2` — 不可修改

### 3.2 Handoff 候选（前端遗留 estimate）

`PathOS-db-ranking/handoff/frontend-data-extraction/normalized-preview/region-metrics.candidate.json`（339 行）：

| 字段 | 值 |
| --- | --- |
| `candidate_only` | **全部 true**（339/339） |
| `preview_only` | **全部 true**（339/339） |
| `verified_against_backend` | 全部 false |
| `production_ready` | 全部 false |
| `manual_review_required` | 全部 null（缺失） |
| 数据条数 | 339（每个 metric 65 州级 + 部分 city） |
| 数据来源字段 | `"Demonstration estimate based on university data"`（65/65 收入 / 65/65 安全 / 65/65 就业 / 65/65 华裔人口 / 14 admission_rate city） |
| 真实来源 URL | 无 |
| 年份 | 2023 / 2024 / 2025（混用） |
| 地理粒度 | state + city |
| 数值单位 | 缺失（`unit: null`） |
| FIPS join | 存在 `"06-berkeley"` 字符串拼接（非标准 FIPS） |

**结论**：候选数据是 Stage 5 之前前端硬编码的演示性 estimate，没有任何官方数据源追溯，且本就被标 `candidate_only=true, production_ready=false` —— **不可作为 verified regional fact 接入**。

### 3.3 旧路径（`/Users/jiayihuang/PathOS`）

`frontend/src/data/region-metrics.json`：仅 7 条占位骨架，与工作区内的占位文件结构相同（更早期版本）。

### 3.4 后端 pipeline（`data-pipeline/`）

未发现 ACS / Census / FBI / BLS 原始采集脚本或 ETL 流水线代码。仅在 `tests/test_stage3c_academic_geo.py` 看到 FIPS 工具函数，无真实数据输入。

---

## 4. 数据身份与契约不变量冲突分析

即便忽略"非 verified"标签，handoff 候选仍存在以下不可调和的契约冲突：

| 不变量 | 当前值 | 若引入候选会变 |
| --- | --- | --- |
| `schoolCount` | 62 | 不变 ✓ |
| `summaryCount` | 62 | 不变 ✓ |
| `detailCount` | 62 | 不变 ✓ |
| `verifiedRecordCount` | 904 | 不变（区域数据走独立计数）✓ |
| `quarantine.exposed` | 0 | 风险：候选数据 `production_ready=false`，可能污染 quarantine 池 ⚠️ |
| `dataMode` | backend | 若引入前端 handoff 数据会绕过 backend ⚠️ |
| `identityVerified` | true | 候选 `verified_against_backend=false` ⚠️ |
| `sourceLimited` | true | 候选 source = "Demonstration estimate" ⚠️ |
| `incomplete` | true | 不变 ✓ |
| `notFinal` | true | 不变 ✓ |
| Preview Bundle SHA | `88f3dd60…` | 修改即破坏不变量 ✗ |

`identityVerified` / `sourceLimited` / `dataMode` 三项若被打破，意味着把"演示性 estimate"伪装成 verified regional fact —— 违反 Stage 6 的"no fake fallback"原则。

---

## 5. 阻塞热力图子任务的最终结论

按指令"如果无法找到数据文件，或者无法确认来源、年份、单位和 join key：只阻塞热力图子任务并报告。不得生成随机数或重新使用安全 70、就业 80 等默认值。"

**决定：BLOCKED 子任务 — 不实施四种热力图。**

理由汇总：
1. Preview Bundle `status: "blocked"`，`records: []`，`disabledReason: "Credentialed official regional intake is unavailable"`。
2. 后端数据源未对接（无 Census ACS / FBI UCR / BLS LAUS / IPEDS 实际 ETL）。
3. handoff 候选数据 339/339 行均为 `candidate_only=true, preview_only=true, verified_against_backend=false, production_ready=false`，source = "Demonstration estimate"。
4. 任何"接入"行为都会引入 fake fallback / 篡改数据真实性边界。
5. 旧路径同样仅占位，无新数据。
6. 用户的"已确认数据准确"声明无法在当前可访问的数据资产中找到证据。

---

## 6. 前端是否可独立建立接入层？

理论上可以：
- 在 `frontend/src/data/regional/` 下新建 JSON + types + validator + adapter。
- 经 BFF `/api/pathos/regional` 暴露（不复用 `pathos/preview` 通道，避免与大学数据契约混淆）。
- 计数独立：frontend 维护 `regionalRecordCount` 等局部 metrics。
- 与 904 完全解耦，不修改 Preview Bundle。

**但前提是数据文件本身可信**。本环境内无任何可信原始数据，因此即便前端管线建立起来也只会做"加载 + 校验 + 渲染空状态"三件事。

### 6.1 留给独立 Re-Gate 的建议
若用户希望热力图真实接入，建议路径（**不属本轮实施范围**）：
1. 接入 **Census ACS 5-Year Estimates** API（公开 endpoint，无 key）：
   - `median_income` / `chinese_population` / `asian_population` (table B02018)
2. 接入 **FBI Crime Data Explorer**（公开 dataset）：
   - 暴力犯罪率（violent crime rate per 100k）
3. 接入 **BLS LAUS**（公开 API）：
   - state-level unemployment / employment rate
4. 数据进入 backend `region_metrics` 表并完成 verified 流程。
5. 重新生成 Stage 5 Preview Bundle → `status: "ok"`, `choroplethEnabled: true`。
6. 在此之前，前端不得渲染任何 choropleth 色块。

---

## 7. 受影响与不受影响的子任务

| 子任务 | 状态 |
| --- | --- |
| ThemeToggle Hydration 修复 | ✅ 本轮实施 |
| 暗色对比度审计与 token 重做 | ✅ 本轮实施 |
| MapLibre Dark Basemap | ✅ 本轮实施 |
| `/assessment` 区域 callout | ✅ 本轮实施（文案调整：地图有数据时显示"可用于参考，未计入 Match Score"） |
| Calculator 缺失费用合成测试 | ✅ 本轮实施 |
| `eslint-disable` 审计 | ✅ 本轮实施 |
| **四种区域热力图接入** | ❌ **BLOCKED — 等待真实 verified 数据** |
| Match 区域 callout 文案同步更新 | ✅ 本轮实施（增加"区域数据地图可参考"措辞） |

---

## 8. 自检结论

按指令 §三：

> 如果无法找到数据文件，或者无法确认来源、年份、单位和 join key：
> 只阻塞热力图子任务并报告。
> 不得生成随机数或重新使用安全 70、就业 80 等默认值。

✅ 已执行。
✅ 未生成任何新区域数据。
✅ 未修改 Preview Bundle（manifest SHA `88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2` 保持不变）。
✅ 未修改 backend tracked files。
✅ 未修改 `verifiedRecordCount=904`。
✅ 文档完整记录数据来源调查与阻塞理由。