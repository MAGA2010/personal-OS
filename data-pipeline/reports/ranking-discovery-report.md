# PathOS Ranking Discovery Report — Stage 2A

## 执行信息

- 执行日期：2026-07-10
- 范围：仅 ranking family、edition、category、来源可访问性和 manual seed 流程；不含学校排名记录、university universe 或学校详情。
- 机器可读输出：[2026-best-colleges](../data/ranking-discovery/2026-best-colleges/)。

## 最新版本判断

当前发现的 U.S. News `Best Colleges` edition 为 **2026 Best Colleges**，发布于 **2025-09-23**。U.S. News 通过 [官方新闻稿转载](https://www.prnewswire.com/news-releases/us-news-announces-2026-best-colleges-rankings-302563669.html) 宣布该版本；[Georgia Tech 官方发布](https://coe.gatech.edu/news/2025/09/undergrad-engineering-program-returns-no-3-us-news-2026-rankings) 与 [University of Arizona 官方发布](https://eller.arizona.edu/news/eller-college-management-listed-among-2026-us-news-world-reports-best-colleges-rankings) 交叉确认其发布日期和本科项目版本。

直接 U.S. News ranking pages 在本次发现环境受 robots 控制而无法访问，未尝试绕过。因此版本号和发布日期的证据置信度为高；「截至发现日仍为最新」的结论为中等置信度，并要求后续运行重新核验。

## Ranking Family Inventory

共发现 9 个易混淆 family：

| Family | Scope | 可访问性 |
| --- | --- | --- |
| National Universities | 纳入 A，数字名次 ≤ 50 | needs_manual_seed |
| National Liberal Arts Colleges | 不作为 A；可通过 B 进入 | partially_public |
| Regional Universities / Colleges | 不作为 A；可通过 B 进入 | partially_public |
| Undergraduate Academic Program and Subject Rankings | 纳入 B，数字名次 ≤ 20 | needs_manual_seed |
| Best Global Universities | 排除 | blocked |
| Best Graduate Schools | 排除 | blocked |
| Best Online Programs | 排除 | publicly_accessible |
| Institutional / Experience categories | 排除 | partially_public |

Global 是研究导向全球排名，Graduate 是研究生范围；Online、Value、Top Public、Veterans、Social Mobility、Innovation 和体验列表不构成当前的本科专业/学科筛选依据。

## Undergraduate Category Inventory

本版共记录 30 个本科类别：28 个纳入、2 个排除。类别不是写死在 `ranking-scope.json`，而是版本化保存在 [category-inventory.json](../data/ranking-discovery/2026-best-colleges/category-inventory.json)，每一项都带 edition、来源、可访问性和 lineage。

| 组别 | 纳入类别 |
| --- | --- |
| Business（12） | Overall、Accounting、Analytics、Entrepreneurship、Finance、International Business、Management、Management Information Systems、Marketing、Production/Operations Management、Real Estate、Supply Chain Management/Logistics |
| Engineering（12） | Overall (Doctorate)、Overall (No Doctorate)、Aerospace、Biomedical、Chemical、Civil、Computer、Electrical、Environmental、Industrial、Materials、Mechanical |
| Other academic subjects（4） | Computer Science、Nursing、Economics、Psychology |

`Undergraduate Teaching Programs` 与 `Undergraduate Research/Creative Projects` 被排除：它们是机构教学/体验认可列表，而非学校 academic program 或 subject ranking。

类别事实由 [ASU 官方发布](https://news.asu.edu/b/20250922-10-asu-undergraduate-business-programs-rank-top-25-nation)、[University of Florida 官方发布](https://warrington.ufl.edu/news/2026-us-news-best-colleges/)、[Georgia Tech 官方发布](https://coe.gatech.edu/news/2025/09/undergrad-engineering-program-returns-no-3-us-news-2026-rankings)、[Kansas State 官方发布](https://www.k-state.edu/news/articles/2025/09/kstate-ranked-as-one-of-the-best-value-universities-in-the-nation.html)、[Hope College 官方发布](https://hope.edu/news/2025/academics/hope-advances-in-u-s-news-and-world-report-national-rankings.html) 和 [Valdosta State 官方发布](https://www.valdosta.edu/about/news/releases/2025/09/vsu-named-a-best-college-by-u.s-news-and-world-report.php) 交叉发现；这些页面不是完整排名表的替代品。

## 来源覆盖与访问审计

- 记录来源：12 个。
- 可公开访问：9 个。
- robots-blocked：3 个。
- 有完整、可合法批量获取的 Top 50 / Top 20 ranking-record feed：0 个。
- 需要 manual seed 的本科类别：28 个；National Universities 也需要单独的 manual seed stream。

`needs_manual_seed` 表示公开交叉资料足以确认 category 存在，但不足以合法、稳定、完整获取 cutoff 内所有学校记录。它不表示可以以记忆或第三方转载替代来源。

## Manual Seed 流程

manual seed 使用 [manual-ranking-seed-batch.json](../schemas/v1/manual-ranking-seed-batch.json) schema，必须包含 ranking system、family、category、edition、学校显示名、numeric/displayed rank、tied、来源及访问日期、录入人与时间、核验状态和 notes。

`validate-ranking-discovery` 会拒绝缺来源、重复 record、超 cutoff rank、Global/Graduate family 和 edition 不一致。通过校验的 batch 仅进入 `manual_ranking_seed_staging`；仍须经过身份解析和 canonical validation，不能直接生成 universe 或前端数据。

## 未解决问题与 Stage 2B

1. 直接 U.S. News pages 的 robots-blocked 状态使完整 cutoff record 获取存在 coverage gap。
2. 未创建任何 school record、排名 record 或 universe；本阶段只完成 metadata。
3. 新 edition 必须重新发现；category rename/add/remove/split/merge 必须建立新 inventory version。

**Stage 2B（manual-seed collection / 合法来源覆盖补齐）准入：满足。**

**最终 university universe generation 准入：尚未满足。** 必须先为 National Universities Top 50 和全部 28 个纳入 category 收集、校验并覆盖所需 ranking records，之后才能去重并生成 universe。
