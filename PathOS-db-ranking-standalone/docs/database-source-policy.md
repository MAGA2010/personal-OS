# PathOS 数据来源与合规政策

## 基本原则

每项外部事实必须可追溯到 `sources`。保存 URL、发布方、页面标题、来源类型、访问时间、适用学年或排名版本、内容 hash 与极短核验说明；不保存整篇网页正文。

不得绕过登录、付费墙、CAPTCHA、robots.txt 或其他访问控制。缺失的公开证据要标记 incomplete，并通过人工 seed 或质量问题记录缺口，不能凭记忆补数据。

## 来源优先级

| 领域 | 优先级 |
| --- | --- |
| 排名 | U.S. News 官方公开页 → 官方声明/新闻稿 → 大学官方排名页 → 可靠媒体交叉验证 |
| 学校身份与专业 | IPEDS → College Scorecard → 官方 academic catalog → 官方 majors/programs 页面 |
| 学费 | 官方 bursar/tuition/student accounts → 官方学院或项目页面 → Common Data Set → IPEDS → College Scorecard |
| 师生比 | Common Data Set → 官方 fact book → IPEDS → College Scorecard → U.S. News 公开资料 |
| 地理 | Census Geocoder → Census Gazetteer / Places；第一版只用 Haversine 直线距离 |
| 人物、历史、轶事 | 大学档案馆 → 官方 biography / award / research / news → 可信机构 → 高质量媒体 |

Wikipedia 可用于发现线索，但不能是重要人物、专业、历史或轶事的唯一证据。

## 排名 seed 与覆盖率

当某类别不能合规、稳定获取时，先记录 category、edition、publication date、可访问来源和不可访问原因。随后可在 `data-pipeline/manual-seeds/` 放入人工核验数据；seed 必须保留来源和核验说明。没有合法证据的 category 在 coverage report 中为 `incomplete`。

### Ranking record 的 edition 与 evidence anchors

- `edition_direct`：来源短摘录直接写明当前 edition（例如 `2026 Best Colleges`、`2026 U.S. News Best Colleges` 或明确等价的 `2026 U.S. News & World Report rankings`）时，才可将 `edition` 放入 `directly_supported_fields`。
- `edition_inferred_from_release_cycle`：仅当发布日期、ranking family/category 与发布周期一致时可记录 contextual support；必须说明推断，且不得将 `edition` 标成直接支持。缺少其他 direct edition 证据的记录只能为 partial/unresolved，不能进入 staging。
- `edition_ambiguous`：仅有 `2025-26`、未说明 cycle 或不能明确等价到 PathOS edition 的页面必须为 partial/unresolved。
- 每条 `verified` seed record 的每个 `directly_supported_fields` 字段都必须有至少一个短 `evidence_anchor`，包含 field、source_id、非空 quote 与 `direct_quote` 类型。anchor 的 source_id 必须存在于 full artifact 的 source manifest。短摘录只供人工复核，不保存整篇正文。
- 正式或批量 `validate-ranking-pilot` 必须传入 seed batches、identity mappings、source manifest、candidate observations、coverage matrix 与 result output；缺任一 artifact 必须 fail closed。底层函数可用于单元测试，不能替代批量 validation。

### Source-limited candidate provenance

- source-limited university candidate 只能从 revalidated corpus 的 accepted verified records 生成；candidate 或 membership 的 supporting record、source ID 和 evidence-anchor reference 必须逐条回验至该 corpus。
- `validate-universe-candidate` 与 `generate-universe-candidate` 必须接收 corpus root 和对应 `corpus-validation-result.json`。正式路径会重跑 corpus validation 并拒绝不一致或手工编辑的 candidate artifact；没有 corpus artifact 不得验证通过。
- candidate 只用于后续身份 enrichment 准备，不能被当作 final universe、canonical selection memberships 或正式 frontend 数据源。

## 学校详情来源与非 U.S. News 排名隔离（Gate 2H M-1）

- CollegeData 可以用于学校 detail enrichment，例如学费、专业、师生比、地理和学校概况；每个 detail field 都必须保留 field-level provenance、来源访问日期和适用年份。CollegeData 不得写入 US News ranking fields。
- Times Higher Education（THE）可以用于学校背景或全球声誉的交叉参考；THE 不得写入 US News ranking fields，也不得覆盖 U.S. News 的综合或本科专业排名。
- QS 与 xuanxiao.org / QS ranking pages 只能作为 QS 或其他 non-US-News ranking reference；QS、xuanxiao.org 不得写入 US News ranking fields，不得混入 National Universities 或 undergraduate program ranking 字段。
- US News ranking fields 只能来自 U.S. News 官方页面、已审核 manual seed，或学校官方明确引用 U.S. News 且直接支持 edition、category、institution 与 rank 的页面。其他排名系统必须保存到独立、带 ranking-system 标识的字段。
- 学校 detail field 如有冲突，优先顺序是：学校官网 / official Common Data Set → IPEDS / NCES → College Scorecard → CollegeData / other secondary references。冲突来源必须并存并形成质量问题，不得用 THE、QS 或 xuanxiao 结果覆盖 U.S. News ranking。

## Stage 3 MVP detail pack：IPEDS 使用边界

- Stage 3 的 NCES/IPEDS detail 输入必须逐字段保留来源：HD 用于机构身份、官网和地图基础字段；IC Academic Year 用于本科 tuition 与 required fees；Completions 用于报告的 bachelor-degree award areas；CIP 浏览表仅用于名称规范化。
- IPEDS tuition 只能作为 institution/university-level undergraduate tuition and required fees。它不能被表述为某个专业的独立收费，也不能推断 college surcharge、program fee、room and board 或 estimated cost of attendance。
- Completions 的 award areas 不是当前学校 catalog 的保证；当 Stage 3 用它补足 demo programs 或 majors 时，必须标为 `areas_of_study`，记录年份与 limitation，不能把它写成 U.S. News ranking 或当前完整专业目录。
- Stage 3 写入路径必须调用 `validate_source_policy_use()`。CollegeData 仅可进入 detail domain 且必须有 field-level provenance；THE、QS、xuanxiao 与所有 other non-U.S.-News ranking source 都不得进入 `usnews_ranking` domain。
- 本科 tuition validator 必须 fail closed：estimated cost of attendance、graduate、MBA、law school、medical school 与 professional school tuition 不能进入本科专业展示或 highest/lowest tuition calculation。没有官方本科 tuition 时只写 null reason，不得估算。

## Stage 3B demo-critical overlay：College Scorecard、reviewed alias 与学校本科页面

- College Scorecard 的 `STUFACR` 可作为官方联邦发布的 student-faculty ratio 字段；必须保存数据 release、UNITID row 的短 anchor、原始字段名、definition notes 与 source reference。直接 `STUFACR` 不是学校 facts-page ratio，也不得伪装成学校自行发布的数据。
- 若未来使用 IPEDS enrollment/staff 字段派生 ratio，必须设置 `derived_ratio=true` 并保存公式、每个变量的 source、年份和定义差异；没有这些元数据不得发布派生 ratio。Stage 3B 当前不进行本地 ratio 派生。
- identity gap 只能通过版本控制的 reviewed alias mapping 解析：mapping 必须连接 Candidate v2 已有 name/alias 与一个声明的 exact IPEDS `INSTNM`；resolver 必须检验该名字唯一命中。未映射、零命中或多命中均保持 unresolved，禁止 fuzzy matching、campus 猜测或 system-level 替代。
- 学校官方 undergraduate majors/programs/areas-of-study 页面可补 demo program，但每条必须标为官方本科观察、保留 URL 和短 anchor、不得写入 `usnews_category` 或 `usnews_rank`。graduate、MBA、law、medical、professional-only program 不得作为 demo program 补充。

## Stage 3C Academic + Geo overlay：official majors、undergraduate fee 与 geography

- Stage 3C 只读 Candidate v2、Stage 3 与 Stage 3B；官方 majors/programs/catalog 页面可以建立 `official_*` major source 或 demo program observation，但不得覆盖 U.S. News category、rank 或 ranking evidence。没有官方页面时，IPEDS bachelor-degree award areas 仍可作为 `only_ipeds_award_areas_available` fallback，且必须明确它不是当前学校官方 catalog。
- Stage 3C tuition deepening 只接受学校官方本科 tuition/bursar/college/program fee 页面，或已经验证的 IPEDS institution-level undergraduate tuition。college surcharge、differential tuition 与 program fee 只有在来源直接证明本科、required、适用 college/program、金额、学年和 residency 时才能进入可比较计算。未发现差异收费的 `university_level_only_confirmed`、`insufficient_data` 和 `not_found` 都是合格的诚实状态。
- COA、room and board、books、transportation、personal expenses，以及 graduate、MBA、law、medical、professional tuition 永远不得进入本科 tuition 或 highest/lowest calculation。course/lab fee 只有在官方明确其为整个本科项目必需费用时才可参与比较。
- `region` 固定为 Census 四区 `Northeast`、`Midwest`、`South`、`West`，不得混用 subregion。nearest towns 只可使用 city、town、municipality、incorporated place 或 Census-designated place；county、campus、neighborhood 与未分类标签不得作为 town。距离固定为 `haversine_straight_line`，必须保存 school/town coordinates、source ID 和 “not driving distance” calculation note。
- Census Gazetteer/other geography cache 必须 gitignored；若正常访问的官方 source 在执行环境不可用，生成空 `nearest_towns` 和明确 source gap，而不是以学校城市、county 或 AI 推断补齐。

## Stage 3C2 Nearest Towns Gap Repair：reviewed Census place cache

- Stage 3C2 只接受经审核的 U.S. Census National Places Gazetteer cache，并在结构化 source manifest 中记录官方 URL、文件名、SHA-256、review status 与 cache 的 gitignored 状态。cache 本身不得进入 commit。
- 允许的 nearest-town place 仅为 Census city、town、municipality、incorporated place 或 Census-designated place。county、campus、neighborhood、学校设施、metro area 与未分类标签一律拒绝。
- 距离固定为 `haversine_straight_line`，保存学校与 place 的坐标、公里/英里值、source ID、source reference 与 calculation notes；必须明示不是 driving distance、不是 travel time。不得调用 driving-distance API，也不得从商业 geocoder 或未审核来源补 place。
- Census 2024 National Places Gazetteer 不含 population counts 时，`population_class` 保持 null 并披露该 limitation；不得估计或伪造人口分级。Stage 3C2 geography detail 不得写入或覆盖任何 U.S. News ranking field。

## Stage 3D People + Narrative overlay：人物关系与短叙事来源

- Stage 3D 的人物、就读、历史与 interesting-fact 来源均属于 `detail` domain；每条正向断言都必须通过 `validate_source_policy_use(..., "detail", has_field_provenance=True)`，并保存 source manifest、字段级短 direct-quote anchor 与来源置信度。不得写入或覆盖任何 U.S. News ranking category、rank、family 或 membership 字段。
- 人物关系只允许严格区分 `graduated`、`attended_no_degree`、`alumnus_unspecified`、`faculty_only`、`honorary_degree_only`、`donor_only` 与 `unclear`。只有前三者可显示为学生/校友；faculty、donor、honorary degree 或 unclear 只能作为 exclusion/audit observation，绝不得表述为就读、毕业或校友。
- 人物 major、degree、graduation year 与 attendance years 各自需要直接来源支持。职业、任教单位、后续 graduate degree、捐赠或声望均不能推断本科专业、毕业状态或就读关系。
- `无` 仅表示在 non-empty `reviewed_scope` 和 `reviewed_source_ids` 指定的已审查来源中没有合格证据；它不是现实中绝对不存在的断言。尚未完成来源审查时必须使用 `source_review_not_completed` 和明确 null reason，不能伪装为 `无`。
- 历史与 interesting facts 必须来自学校官方页面、官方 archive/library、或直接支持事实的可信参考来源。提交内容只保存结构化 observation、短 anchor 与短 factual paraphrase；不得提交整页快照、长段 biography、复制的历史正文或编造故事。

## Stage 3D-Fill：reviewed people and narrative source fill

- Stage 3D-Fill 是独立于 Stage 3D framework 的 reviewed-source overlay。它只能读取 Candidate v2、Stage 3C demo-program slots、Stage 3D framework 和 version-controlled reviewed observations；不得回写上述输入或在 detail artifacts 中携带任何 U.S. News ranking field。
- program-person slot 只允许 `identified`、`no_qualifying_person_found` 或 `source_review_not_completed`。`无` 仅适用于前者来源范围已实际审查且 `reviewed_scope`、`reviewed_source_ids` 都非空的 scoped result；正常来源未审查、访问失败或未录入 observation 时必须保持 `source_review_not_completed`，不得把未审查写成 `无`。
- 每条 affirmative program person、attendance、history 或 anecdote 都必须有 manifest source ID、短 direct quote evidence anchor 和字段级 provenance。`direct_quote` 必须从所引来源逐字复制；paraphrase 绝不得标为 `direct_quote`。每个 anchor 必须记录 `quote_verification_method`（`manual_verbatim_check` 或 `local_cache_substring_check`）；若 manifest 提供 reviewed short quotes，anchor 必须逐字匹配其中一项。history/anecdote 正文仅保存不超过短文本阈值的 factual paraphrase，不得复制长段网页原文、完整 biography 或 HTML snapshot。
- 只有 `graduated`、`attended_no_degree`、`alumnus_unspecified` 可进入学生或校友内容。`faculty_only`、`donor_only`、`honorary_degree_only`、`unclear` 只能写入 exclusions/audit notes，绝不得显示为 student、alumnus、attended 或 graduated。

## Stage 3D-Fill Batch 1：reviewed history + anecdotes

- Batch 1 是独立的 source-intake overlay；它只读取固定 Candidate v2、Stage 3C demo slots 与已提交的 Stage 3D-Fill seed fingerprints，不得回写这些输入或把 People/Narrative detail 写入任何 U.S. News ranking field。
- 每个正向 history、anecdote、attendance 或 program-person record 都必须保存 `source_id`、source URL/reference、短 `direct_quote` anchor、`quote_verification_method` 和短 factual paraphrase。Batch manifest 只保存 reviewed short quote allowlist；每个 anchor 必须逐字匹配 allowlist，且 method 只能是 `manual_verbatim_check` 或 `local_cache_substring_check`。
- Batch 1 的 history/anecdote status rows 必须覆盖 62 所学校。没有正常访问且审查过的合格来源时，status 是 `source_review_not_completed`；不以「无」替代未审查 source gap。310 个 demo-program slots 也只有在 person、eligible relationship 与 major/program 都由同一 reviewed evidence 直接支持时才可 `identified`。
- attendance 只能写 `graduated`、`attended_no_degree`、`alumnus_unspecified`；major 不在来源中时为 null 并写 `major_not_stated_in_accepted_source`。faculty、donor、honorary-degree、unclear 关系一律拒绝进入 alumni/attendee output。

## Stage 3D-Fill Batch 2：reviewed history + anecdotes expansion

- Batch 2 是 Batch 1 之后的独立、增量 reviewed-source overlay。它只能读取固定 Candidate v2、Stage 3C demo slots、Stage 3D-Fill seed 与不可变 Batch 1 artifacts；history/anecdote 不得与 Batch 1 同校重复，且不得回写任何上游或 Batch 1 文件。
- 每条 Batch 2 affirmative history/anecdote/person assertion 必须同时具备 official/credible manifest source、短 direct-quote anchor、source reference 与 `quote_verification_method`。anchor 必须逐字匹配该 source manifest 的 `reviewed_short_quotes` allowlist；没有本地 source cache 时必须标记 `manual_verbatim_check`，paraphrase 永远不得作为 direct quote。
- Batch 2 未审查 history、anecdote 与 program-person slot 必须保持 `source_review_not_completed`，不得以「无」替代 intake gap。任何 scoped 「无」仍需要 non-empty `reviewed_scope` 与 `reviewed_source_ids`；本批没有创建 scoped 「无」。
- Batch 2 people/narrative 均属于 `detail` domain；学校 official history/about 页面只支持短 narrative detail，绝不得写入或覆盖 U.S. News ranking fields。Batch 2 不是完整 people/narrative database，也不是 PASS 或 frontend export claim。

## Stage 3D-Fill People Pilot：reviewed notable attendance

- People Pilot 是独立、固定范围的小批量 attendance overlay。每条正向人物关系必须有学校官方或等价 reviewed institutional source、短逐字 `direct_quote`、source reference 与 `quote_verification_method`；它们只能进入 `detail` domain，绝不得写入或覆盖 U.S. News ranking field。
- 只有 `graduated`、`attended_no_degree`、`alumnus_unspecified` 可以进入 notable attendance。`faculty_only`、`donor_only`、`honorary_degree_only`、`unclear`、同名未解析或校区不匹配只能进入 exclusions；禁止从职业、名气或同名推断专业、就读或毕业。
- `canonical_person_id` 必须由已审查的 person name deterministic 生成且在本批唯一；major 或 degree 不被 selected source 直接支持时保持 null 并披露 scoped null reason。program-person 仅可在同一人物已有 reviewed attendance 且 source 直接支持 demo program/degree 关联时填入，不能由职业反推。
- manifest 只提交 reviewed short-quote allowlist，完整网页 cache 不得入库。若本地 cache 存在，cache manifest 必须记录路径和 SHA-256，validator 复核完整性并可进行 substring check；未缓存时需记录 `manual_verbatim_check`。未审查 slot 必须保持 `source_review_not_completed`，不得伪造「无」。

## Stage 3D-Fill People Pilot Bulk Readiness：cache 与人物消歧

- Bulk 前的正向 People Pilot anchor 默认必须使用 `local_cache_substring_check`。每个 cached source 必须在 gitignored reviewed-excerpt cache 中保留 source ID、source URL/reference 与经审阅的短逐字 excerpt；manifest 必须记录相对 cache path、SHA-256、review notes 和 verification method。validator 必须同时校验 cache 存在、SHA-256、source reference 与 anchor quote substring。没有 cache 时可保守地保留 `manual_verbatim_check`，并计入 `cache_missing_count`，但不得伪装为 cache verified。
- `canonical_person_id` 不得再是纯 name slug。它必须由 normalized person name、Candidate university context 和 `person_identity_disambiguator_source_id` 决定；该 disambiguator source 必须属于同一 candidate。不同 candidate/source context 的同名人物不得自动合并。不能解析 context 的 same-name observation 只能进入 `same_name_unresolved` exclusion，不得产生正向 attendance 或 program-person assertion。

## 质量与时效

来源冲突不覆盖旧记录：保留新旧记录、按优先级选择 primary，并新增 `data_quality_issues`。无来源、年份不明、CIP 无法安全映射、学费口径不可比较或人物专业不确定时，保存 null reason / issue，不猜测。
