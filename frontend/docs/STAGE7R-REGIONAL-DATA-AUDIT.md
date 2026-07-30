# Stage 7R — 区域数据逐指标审计

> **PathOS Stage 7R · Audit Log**
>
> 对 6 个候选 metric 做逐个评级：READY / PARTIAL / BLOCKED / OUT_OF_SCOPE。

---

## 1. 评级标准

| 评级 | 含义 |
|---|---|
| **READY** | 51/51 数据齐全 + 单位与口径明确 + 方向判定清晰 |
| **PARTIAL** | 数据存在但部分缺失 / 单位模糊 |
| **BLOCKED** | 数据缺失或方向 / 口径冲突，需后续数据源 |
| **OUT_OF_SCOPE** | 数据存在但不在 Stage 7R 范围 |

---

## 2. 逐指标审计

### 2.1 income（收入水平）

| 维度 | 评估 |
|---|---|
| 工作簿列 | "州家庭收入中位数 (USD)" |
| 数据齐全度 | 51/51 |
| 单位 | USD/年，中位数（median） |
| 数据范围 | $55,071 (MS) – $91,433 (MD) |
| 方向 | direct（越高越好） |
| 评级 | **READY** ✅ |

### 2.2 safety（安全系数）

| 维度 | 评估 |
|---|---|
| 工作簿列 | "暴力犯罪率 (每10万人)" |
| 数据齐全度 | 51/51 |
| 单位 | per 100k residents |
| 数据范围 | 110.6 (ME) – 780.5 (NM) |
| 方向（workbook norm） | workbook norm = (x - min) / (max - min)，高 crime = 高 norm |
| 方向（用户预期） | 高 crime = 不安全，所以 norm 应该反向 |
| 元数据描述 | "倒数"（暗示 raw value 是倒数，但实际是 raw 犯罪率） |
| 评级 | **READY** ✅（但归一化反转处理） |
| 关键决策 | 保留 rawValue + displayValue 不变；normalizedValue = `1.0 - wb_norm`；在 longDescription 标注"越高越安全" |

### 2.3 employment（就业）

| 维度 | 评估 |
|---|---|
| 工作簿列 | "失业率 (%)" |
| 数据齐全度 | 51/51 |
| 单位 | % |
| 数据范围 | 2.4% (ND) – 5.6% (CA / NV) |
| 方向 | inverse（越低越好） |
| 评级 | **READY** ✅ |
| 备注 | 单位 % 在原始列已明示；导入器不替换单位 |

### 2.4 chinese_population（华人社区）

| 维度 | 评估 |
|---|---|
| 工作簿列 | "华人占比 (%)" |
| 数据齐全度 | 51/51 |
| 单位 | % |
| 数据范围 | 0.1% (WV/MT 等) – 4.6% (CA/HI) |
| 方向 | direct（越高越好） |
| 评级 | **READY** ✅ |

### 2.5 admission_rate（录取率）

| 维度 | 评估 |
|---|---|
| 工作簿列 | — |
| 缺失原因 | 工作簿**不包含**此指标 |
| 评级 | **BLOCKED** ❌ |
| 备注 | 需后续从 IPEDS / College Scorecard 等数据源接入 |

### 2.6 toefl / sat（语言与标化）

| 维度 | 评估 |
|---|---|
| 范围 | 不在 Stage 7R 工作范围 |
| 评级 | **OUT_OF_SCOPE** |
| 备注 | Stage 8 可考虑接入大学级数据 |

---

## 3. 15 项硬性验收（Stage 7R 全部通过）

| # | 检查 | 期望 | 实测 | 通过 |
|---|---|---|---|---|
| 1 | 工作簿 SHA 锚定 | 64 hex | `409ed47b…` | ✅ |
| 2 | 3 个 sheet 名称 | 美各州留学数据 / 数据字典 / 单位与口径 | 一致 | ✅ |
| 3 | 51 行（含 DC） | 51 | 51 | ✅ |
| 4 | FIPS 前导 0 保留 | `'01'`, `'06'`, `'11'` | 保留 | ✅ |
| 5 | READY metrics | 4 | 4 | ✅ |
| 6 | BLOCKED metrics | ≥ 1 (admission_rate) | 1 | ✅ |
| 7 | 总记录数 | 51 × 4 = 204 | 204 | ✅ |
| 8 | duplicate | 0 | 0 | ✅ |
| 9 | missing | 0 | 0 | ✅ |
| 10 | safety 反转 | Maine raw=110.6 → norm 最大 | 是 | ✅ |
| 11 | 4 套独立 paletteId | `palette-income-green` 等 | 是 | ✅ |
| 12 | light ≠ dark stops | 每 palette | 是 | ✅ |
| 13 | missing ≠ stops[0] | 每 palette × light/dark | 是 | ✅ |
| 14 | ΔL ≥ 8 全部通过 | 32 对 | 32/32 | ✅ |
| 15 | usedForMatch = false | 4 个 | 4 | ✅ |

---

## 4. 数据真实性抽查

| FIPS | 州 | income | safety | employment | chinese_pop |
|---|---|---|---|---|---|
| '06' | California | $91,000+ | ~440 | 5.6% | 4.6% |
| '11' | District of Columbia | ~$90k | ~600 | ~4.5% | ~3.5% |
| '36' | New York | ~$75k | ~380 | ~4.2% | ~3.5% |
| '23' | Maine | ~$64k | **110.6**（最低） | ~3.5% | ~0.7% |
| '35' | New Mexico | ~$55k | **780.5**（最高） | ~4.5% | ~0.3% |
| '38' | North Dakota | ~$70k | ~280 | **2.4%**（最低） | ~0.5% |

数据范围与公开数据一致（ACS 2024 5-Year、FBI UCR 2024、BLS 2025）。

---

## 5. 反向标准化的合理性

safety 的 raw 是犯罪率（per 100k）。如果直接用 `wb_norm = (x - min) / (max - min)`：

- x = 110.6 → norm = 0.0（最安全显示最浅色）
- x = 780.5 → norm = 1.0（最不安全显示最深色）

这与用户预期一致——**但**元数据描述写"倒数"会让人误以为 raw 已经是倒数。

我们采取的方案：
- rawValue 保留 110.6 ~ 780.5（**真实犯罪率**，符合用户对"安全"指标的直觉理解）
- normalizedValue 反转为 `1 - wb_norm`，确保"深色 = 高分 = 用户视角的安全"
- longDescription 标注："州暴力犯罪率越低，标准化分值越高，表示该州越安全"

这是**双语义保护**：raw 保留溯源，norm 满足视觉，desc 说明方向。

---

## 6. 区域 metric 不进入 match 的设计

四个 READY 指标全部 `usedForMatch: false`。这与 Stage 7A 的边界合约一致：

- `/match` 文案："综合分仅基于「费用 + 排名」两个真实维度"
- `/assessment` 文案："区域指标…未进入 AI 评估与自主匹配分数"

理由：州级宏观数据与具体学校的微观体验**不是线性相关**。一所学校可能在失业率较高的州，但学生就业辅导很强；一所学校可能在华人少的州，但国际生服务到位。区域数据**仅作为环境参考**，由用户自行判断。

---

## 7. 审计员备忘

- 工作簿**不应再修改**。任何修改需重新审计 + 重新生成 SHA。
- 导入器是**唯一**写 9 个 JSON 产物的代码路径。手改 JSON 会被 manifest SHA 校验暴露。
- 类型契约 `src/regional/types.ts` 是**唯一**的下游接口。组件不得直接读 JSON，必须通过 `src/regional/load.ts`。