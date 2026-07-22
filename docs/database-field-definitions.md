# PathOS 数据库字段定义

## 核心身份与来源

| 表 | 关键字段 | 定义 |
| --- | --- | --- |
| `universities` | `internal_id` | PathOS 稳定主键 |
|  | `unitid` | IPEDS 身份与去重优先键；可暂空但不得伪造 |
|  | `college_scorecard_id` | College Scorecard 标识 |
|  | `selection_reason` | `national_top_50`、`program_top_20` 或 `both` |
| `sources` | `content_hash` | 对已访问内容的变更检测 hash，不保存全文 |
|  | `status` | `active`、`archived`、`incomplete` 或 `test_only` |

## 排名与专业

| 表 | 关键字段 | 定义 |
| --- | --- | --- |
| `ranking_snapshots` | `ranking_family` | `national_universities`、`undergraduate_program`、`graduate_program` 或 `global_universities`；后两者不进入当前主筛选 |
| `ranking_snapshots` | `category` | program ranking category 的唯一 canonical source；`program_rankings` 不重复保存该字段 |
| `university_rankings` | `numeric_rank` | 用于 cutoff 与并列判断的数字名次；不得以 displayed text 判断 |
| `programs` | `cip_code_*` | CIP 2 / 4 / 6 位标准码；无可靠映射则为空 |
| `university_programs` | `official_program_name` | 学校官方原名；不可被 canonical name 覆盖 |
| `university_programs` | `cip_mapping_status` | `mapped`、`unresolved` 或 `not_applicable` |

## 费用、地理与内容

| 表 | 关键字段 | 定义 |
| --- | --- | --- |
| `tuition_records` | `pricing_basis` | `university_wide`、`school_or_college`、`program_specific`、`per_credit`、`not_public` 或 `not_applicable` |
|  | `comparable_annual_total` | 仅含 tuition、mandatory fees 和强制项目费的可比年总额；不含食宿、书本和个人支出 |
| `student_faculty_ratio_records` | `definition` | 该比值的来源定义，避免跨来源静默覆盖 |
| `nearby_places` | `distance_method` | 第一版固定 `haversine`，单位 km |
| `distinguished_students` | `null_reason` | 找不到同时满足在校/近期、专业归属和成就证据时的明确原因 |
| `public_figures` | `attendance_status` | `graduated`、`attended`、`transferred`、`withdrew` 或 `unknown` |
| `university_anecdotes` | `is_unverified_legend` | 未核验传说默认不得进入正式前端 |

## 质量问题

`data_quality_issues` 记录问题字段、类型、描述、严重度、状态、发现来源与时间。高严重度问题不得被 export adapter 静默忽略。
