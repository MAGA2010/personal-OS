# Stage 7R — Resource Inventory

> Stage 7R — Regional Heatmap Data Audit
> Generated: 2026-07-25

## 1. 工作区只读扫描 (Read-only resource scan)

工作区：`/Users/jiayihuang/Downloads/PathOS合并`
资源目录：`/Users/jiayihuang/Downloads/PathOS合并/resource`

```
$ ls -la resource/
-r--r--r--  jiayihuang  staff  18202  Jul 25 19:52  PathOS_美国各州留学数据矩阵.xlsx
```

仅发现 1 个文件（一个 Excel 工作簿）。未发现 README、数据字典、独立 CSV/TSV/JSON。

---

## 2. 主工作簿指纹 (Primary workbook fingerprint)

| 字段 | 值 |
|------|----|
| `relativePath` | `resource/PathOS_美国各州留学数据矩阵.xlsx` |
| `fileType` | xlsx (Office Open XML) |
| `fileSize` | 18,202 bytes |
| `sha256` | `409ed47b5153725914b463ae3421ad51e5d3d34e5918144f001f341b9894b096` |
| `created` | 2026-07-25 19:52 (read-only mtime) |
| `modified` | 2026-07-25 19:52 |
| `toolsForRead` | `openpyxl 3.1.5` (Python 3.9.6) |

工作簿内部 ZIP 解压确认标准 OOXML 结构；无密码、无外部链接、无共享字符串异常。

---

## 3. 工作表清单 (Sheet inventory)

| sheet 名 | 状态 | 维度 | 隐藏 | 角色 |
|----------|------|------|------|------|
| `州级数据汇总` | visible | 53 rows × 22 cols | 否 | 主数据：51 行 FIPS × 6 指标 × (norm, raw, display) |
| `指标说明` | visible | 8 rows × 5 cols | 否 | 元数据：6 指标 ID / 中英名 / 来源 / 含义 |
| `Top10排名` | visible | 77 rows × 6 cols | 否 | 每个指标前 10 名排名（衍生品，可重建） |

未发现任何隐藏 / VeryHidden 工作表。

---

## 4. 主工作表 — `州级数据汇总` 头部识别 (Header detection)

### Row 1 — Banner（不计入数据）

`A1`:
```
PathOS 美国各州留学数据矩阵  |  数据来源: Census ACS + FBI UCR  |  更新: 2026-07
```

这条 banner 给出**全局来源声明**：「Census ACS + FBI UCR」与「更新: 2026-07」，
但 6 个指标的**单独来源**写在「指标说明」工作表中（更精确）。

### Row 2 — Header（22 列）

```
A2:  FIPS
B2:  缩写
C2:  州名 (中文)
D2:  州名 (英文)
E2:  收入水平\n(0-1归一化)
F2:  收入水平\n原始值
G2:  收入水平\n显示值
H2:  安全系数\n(0-1归一化)
I2:  安全系数\n原始值
J2:  安全系数\n显示值
K2:  就业指数\n(0-1归一化)
L2:  就业指数\n原始值
M2:  就业指数\n显示值
N2:  留学成本\n(0-1归一化)
O2:  留学成本\n原始值
P2:  留学成本\n显示值
Q2:  录取率\n(0-1归一化)
R2:  录取率\n原始值
S2:  录取率\n显示值
T2:  华人水平\n(0-1归一化)
U2:  华人水平\n原始值
V2:  华人水平\n显示值
```

每个指标占据 3 列：(normalized, raw, display)。

### Row 3..Row 53 — Data

51 行；FIPS 字符串 `'01'`..`'56'`（保留前导零）；DC = `'11'`。

---

## 5. 指标说明工作表 — `指标说明`

| 指标 ID | 中文名 | 英文名 | 来源 |
|---------|--------|--------|------|
| `income` | 收入水平 | Median Income | Census ACS 5-Year |
| `safety` | 安全系数 | Safety Index | FBI UCR (Uniform Crime Report) |
| `employment` | 就业指数 | Employment Index | BLS (Bureau of Labor Statistics) |
| `cost` | 留学成本 | Study Cost Index | College Board / 各大学官网 |
| `admission_rate` | 录取率 | Admission Rate | IPEDS |
| `chinese_population` | 华人水平 | Chinese Population % | Census ACS |

`admission_rate` 注释：「录取率数据，州级暂缺，仅有城市级示范数据」 ——
说明工作簿作者明确标注该指标州级缺失。

`safety` 注释：「基于暴力犯罪率（每10万人暴力犯罪案件数）的倒数，数值越高越安全」
—— 但**实际原始值是 raw crime rate**，**未取倒数**。这是数据语义缺陷；
本轮规范化为忠实保留 rawValue，但在 normalizedValue 阶段**反向**，并
在 Tooltip / Legend 中写明方向。

---

## 6. FIPS 审计 (FIPS audit)

| 检查 | 结果 |
|------|------|
| 总数 | 51 |
| 唯一 | 51 |
| 全部 2 字符 | ✓ |
| 前导零保留 | ✓（全部以字符串存储） |
| 是否全部数字 | 部分 — 类型是 `str` 而非 `int` |
| 含 DC | ✓（FIPS=11） |
| 含 Puerto Rico 等领地 | ✗（仅 50 州 + DC） |
| 缺哪个州 | 无；50 州 + DC 全员到位 |
| 与底层 GeoJSON state boundaries 对齐 | 依赖 FIPS 字符串 join |

---

## 7. 逐指标数值审计 (Per-metric numeric audit)

| 指标 ID | coverage | missing | "N/A" literal | raw direction | norm direction | higherIsBetter (元数据) | higherIsBetter (实际 raw) |
|---------|----------|---------|----------------|---------------|----------------|--------------------------|---------------------------|
| `income` | 51/51 | 0 | 0 | \$/year | 0–1 | yes | yes |
| `safety` | 51/51 | 0 | 0 | /100k (crime rate) | 0–1 | yes (元数据声明) | **no** (raw = crime rate, 高=更危险) |
| `employment` | 51/51 | 0 | 0 | % (employment rate) | 0–1 | yes | yes |
| `cost` | 51/51 | 0 | 0 | ¥/year | 0–1 | n/a (not requested) | n/a |
| `admission_rate` | **0/51** | **51** | **102** | n/a | n/a | n/a | n/a |
| `chinese_population` | 51/51 | 0 | 0 | count | 0–1 | yes | yes |

---

## 8. 数据语义陷阱 (Data semantics traps)

1. **`safety` 反向问题**：原始值的「数值越高越危险」，但元数据声明「数值越高越安全」。
   决策：rawValue / displayValue **保留原方向**（crime rate），normalizedValue
   **反向**（数值越高=越安全），并在 UI 中用蓝色顺序色阶 + 显式方向文字说明。
2. **`cost` 不在请求范围**：用户本轮只要求 4 类指标，本轮不接入 cost，但保留
   解析路径以备后续。
3. **`admission_rate` 全部 N/A**：工作簿作者已标注「州级暂缺」。本轮**完全不上
   线**该指标，记录为 BLOCKED。
4. **前导零保留**：FIPS 全部以字符串形式存储（`'01'` 等）。需在 GeoJSON join 时
   保留零前缀。

---

## 9. 资源清单文件清单 (Inventory file list)

| relativePath | fileType | sha256 | sheetNames | rowCount | colCount | possibleMetrics |
|--------------|----------|--------|------------|----------|----------|-----------------|
| `resource/PathOS_美国各州留学数据矩阵.xlsx` | xlsx | `409ed47b…94b096` | `州级数据汇总`, `指标说明`, `Top10排名` | 53/8/77 | 22/5/6 | income, safety, employment, cost, admission_rate, chinese_population |

无 README / 数据字典 / 独立 CSV/TSV/JSON。所有元数据来自工作簿内部两
个工作表。

---

## 10. 临时解压路径 (Temp inspection path)

只读扫描中产生的临时文件存放在 `/tmp/pathos-stage7r-resource-inspection/`：

```
$ ls /tmp/pathos-stage7r-resource-inspection/
workbook-dump.json
```

raw 单元格全部保留为字符串、数字、None；未做任何修改。

---

## 11. 结论 (Conclusion)

| 项 | 状态 |
|----|------|
| 资源完整盘点 | ✓ |
| 原始工作簿 SHA-256 记录 | `409ed47b5153725914b463ae3421ad51e5d3d34e5918144f001f341b9894b096` |
| 多工作表读取 | ✓（3 个工作表全部读取） |
| 多行表头识别 | ✓（r1 = banner，r2 = header，r3.. = data） |
| 隐藏 / VeryHidden | ✗ 未发现 |
| 数据问题识别 | `safety` 反向、`admission_rate` 全空 |
| 准备进入逐指标审计 | ✓ |

下一步：进入 [`docs/STAGE7R-REGIONAL-DATA-AUDIT.md`](STAGE7R-REGIONAL-DATA-AUDIT.md)
对每个指标做准入门槛判定。