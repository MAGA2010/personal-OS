# PathOS 数据状态

## 1. 冻结边界

| 项目 | 当前值 |
|---|---:|
| Contract version | `pathos-preview-v1` |
| Dataset version | `stage5-preview-ec8c66e` |
| View | `preview` |
| Schools | 62 |
| Summaries | 62 |
| Details | 62 |
| Verified records | 904 |
| Preview manifest SHA-256 | `88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2` |
| Source checkpoint | `ec8c66e200b566dba4de35987aa5213960749a57` |

数据状态继续声明：`sourceLimited=true`、`incomplete=true`、`notFinal=true`、`previewOnly=true`。

## 2. University Data

当前公开 Preview 可使用的主要信息包括：

- ranking 及排名状态；
- programs 与专业清单；
- tuition / cost summary；
- student ratio 与部分招生指标；
- campus location、state、city / county scope；
- nearby towns；
- 学校中英文名称、稳定 ID 和坐标；
- 来源、状态、warning 和 provenance。

重要缺失值规则：

- 12 所学校不在当前 national scope 时不显示 rank 0。
- 9 所 SAT / ACT `not_reported` 时不显示 0。
- Test policy 与 English policy 的 62 所记录仍为 pending，不推断结论。
- Enrollment 使用 2019 reference year 时必须显示年份与 warning。
- 16 所 county-only geography 不冒充 city。
- 130 个 program-person gaps 继续显示「数据补充中」。
- `null` 不转换为 0，quarantined records 不进入公开 UI 或 AI context。

## 3. Regional Data

后期地图阶段从本地工作簿生成以下 4 项州级指标：

| Metric | 说明 | 覆盖 | 地图使用 | Match 使用 |
|---|---|---:|---|---|
| `income` | 州家庭收入中位数 | 51/51 | 是 | 否 |
| `safety` | 暴力犯罪率的反向标准化安全指标 | 51/51 | 是 | 否 |
| `employment` | 由失业率换算的就业率 | 51/51 | 是 | 否 |
| `chinese_population` | 华人社区人口规模 | 51/51 | 是 | 否 |

合计 204 条记录，duplicate 0、missing 0。源工作簿：

`resource/PathOS_美国各州留学数据矩阵.xlsx`

归档核验 SHA-256：`409ed47b5153725914b463ae3421ad51e5d3d34e5918144f001f341b9894b096`。

### 两层数据的区别

Stage 5 Preview Bundle 的 `region-metrics.json` 仍是 blocked / empty，代表当时的冻结契约；Stage 7 的 `generated/regional-data/` 是后来为地图加入并单独验证的 Demo 数据。未来不得把二者无条件合并，也不得让区域指标进入 Match 分数。

## 4. 数据管道

```text
raw
  ↓
staging
  ↓
canonical
  ↓
validation
  ↓
warning-aware preview artifacts
  ↓
Next.js BFF / frontend DataSource
```

Stage 5 generation 为 deterministic、network-disabled；validator 记录为 49/49。Stage 4B validator 为 60/60，Stage 4C validator 为 86/86。

## 5. 数据可信度原则

- 所有公开事实应能追溯到来源或明确状态。
- 缺失优于伪造，pending / deferred 不得变成 verified fact。
- 禁止 fabricated data、fake ranking 和 placeholder university facts。
- Fixture 只能用于显式测试模式，不能作为 backend mode 的事实来源。
- Production Data Export 仍然禁止。
