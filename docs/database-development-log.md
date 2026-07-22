# PathOS 数据库开发日志

## 2026-07-15｜Stage 3D-Fill Bulk People v2：Reviewed-Source Intake Batch B

- 目标与范围：为修正后的 20 所 Candidate v2 学校各处理 1 条 notable attendance 与 1 个不可变 Top-1 demo-program person slot，生成独立 Batch B overlay。Virginia Tech 因不属于 Candidate v2 被移除，由 Candidate v2 内的 Texas A&M University 替换；manifest 固定为 exactly 20 schools，且 validator/test 同时检查子集关系、排除 Virginia Tech、纳入 Texas A&M。
- Schema/状态语义：复用已通过的 Top-1 slot schema，仅允许 `identified_person`、`source_review_not_completed`、`no_qualifying_person_found`。20/20 slots 已处理，其中 4 条有 official attendance + source-stated program 双证据，16 条继续为 `source_review_not_completed`，没有把未审查缺口写成「无」，`no_qualifying_person_found=0`。
- Reviewed sources：20 条 notable attendance 复用 Bulk People v1 已验证的学校官方来源与 gitignored cache；新增 4 条 program-person 来源分别来自 Rice、Carnegie Mellon、Michigan 与 Ohio State 官方页面/PDF。所有 24 条正向记录都使用短 direct quote、cache SHA-256 与 `local_cache_substring_check`；`manual_verbatim_check=0`、`cache_missing=0`。职业、公司、名气、成就与研究方向均未用于 program match。
- Validator：fail-closed 检查 Candidate v2 scope、corrected school manifest、allowed relationships、source-backed disambiguated person ID、exact/related program match basis、双 evidence anchors、quote allowlist/cache substring/SHA、no-qualifying gate、same-name collision、ranking isolation、upstream SHA 与 deterministic regeneration。累计 A+B 统计从 artifacts 动态求并集；Michigan 跨批重复使 30 次 batch occurrences 对应 29 所 unique universities，而非错误报告成 30 所。
- 文件变更：新增 Batch B implementation prompt、school/source/cache/observation/exclusion inputs、generator/validator/CLI、8 个生成 artifact + 1 个 validation artifact、独立报告和 8 个 targeted tests；仅为独立报告增加 `.gitignore` allowlist。未修改 Candidate v2、Stage 3/3B/3C/3C2/3D、previous batches 或 frontend。
- 测试结果：Batch B targeted tests 8/8 通过；全部 Python tests 201/201 通过；Batch B CLI validator 通过并与生成的 validation artifact byte-identical；fixture/schema/migration validation 通过；artifact/report byte-identical regeneration 通过；`source_policy_violations=0`、`ranking_field_contamination=0`。
- 风险与下一步：Batch B 只识别 4/20 program people，累计 A+B 为 5/29 unique Top-1 slots；其余仍需后续 reviewed-source intake。本包继续标记 `source_limited`、`incomplete`、`not_final`。完成本提交后应停止并等待 Gate review，不进入 frontend、final universe、formal memberships 或 frontend export。

## 2026-07-10｜第一阶段：架构与可验证管道

### 本轮目标

建立 PostgreSQL-compatible canonical schema、版本化 Schema、可恢复 pipeline skeleton 和最小端到端验证闭环；不采集学校全集、不创建远程 Supabase 项目。

### 已确认技术决策

- canonical contract 以 PostgreSQL / Supabase-compatible numbered migrations 为准。
- raw、staging、cache 和 manual seed 可使用本地 JSON / JSONL；SQLite 仅可作为后续运行状态或缓存工具。
- 正式导出固定为 `raw → staging → normalization → canonical → canonical validation → frontend export`。
- provenance 对综合事实使用多对多关系表；原子事实可使用单个 `source_id`。
- 「40 所」保留为未来 featured、deep-verified 或 launch subset，不限制动态 canonical universe。

### 本轮实施状态

已完成架构、migration、schema、pipeline skeleton、来源政策、数据合同和离线验证闭环；没有创建远程 Supabase 项目、没有使用 API Key、没有采集真实学校全集，也没有修改前端类型或地图组件。

### 技术决策与原因

- 使用 3 个编号 migration 文件分别承载核心身份/来源、排名/专业、enrichment/质量问题，以保持依赖顺序清晰。
- 对 ranking records、history、anecdotes、distinguished students、public figures 与可变事实使用多对多来源关系，避免一个综合结论被迫压缩为单一来源。
- 使用 Python 标准库实现有限且明确的 JSON Schema validator；当前环境没有 `jsonschema` 包，也未安装任何依赖。JSON Schema 文件仍遵循 Draft 2020-12 声明，离线 validator 覆盖本项目使用的关键关键字。
- `data-pipeline/config/ranking-scope.json` 只定义 scope 和 exclusion，不包含凭记忆生成的学校或排名数据。
- 测试 fixture 含 `is_test_fixture: true`，仅在内存/临时目录形成 preview；正式 canonical 与正式 export 均拒绝 fixture。

### 新增文件

- `data-pipeline/`：Python package、CLI、migrations、schemas、config、fixture、tests、目录占位与忽略规则。
- `docs/database-data-contract.md`
- `docs/database-source-policy.md`
- `docs/database-field-definitions.md`
- `docs/superpowers/specs/2026-07-10-university-database-phase-1-design.md`
- `docs/superpowers/plans/2026-07-10-university-database-phase-1.md`

### 修改文件

- `docs/database-development-log.md`：由启动记录更新为本轮完成记录。

### 数据来源

本轮没有采集真实外部学校数据。唯一数据是明确标记为 `test_only` 的本地 fixture，URL 使用 `example.invalid`，不可作为真实来源。

### 测试结果

- Python 最小闭环测试：raw validation → staging → normalization → canonical-compatible validation → preview export → `UniversityPOI` required-field assertions。
- fixture 隔离测试：fixture 正式 export 必须失败。
- migration 静态审计：编号、必需表、sources 外键与 ranking snapshot 唯一约束。
- ranking scope 测试：只纳入 National Universities 和 undergraduate program families，排除 Global 与 Graduate。
- JSON Schema 文档与本地 `$ref` 解析测试。

最终验证结果：

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`：6 / 6 通过。
- `PYTHONPATH=src python3 -m pathos_data validate --fixture tests/fixtures/test-university-raw.json`：通过，输出 `Schema and migration validation passed`。
- `PYTHONPATH=src python3 -m pathos_data discover-rankings`、`collect --university test-harvard` 与 `report`：均按设计输出 dry-run，未进行网络采集。
- `npx tsc --noEmit`（`frontend/`）：退出码 0。
- `git diff --check`：无空白错误。

## 2026-07-14｜Stage 3D-Fill Bulk Completion v2：History + Anecdotes Checkpoint

- 目标与范围：在固定的 Candidate v2 62 校范围内，优先完成 reviewed history 与 anecdote 展示数据；继续将 notable attendance 保持为既有 10 条 reviewed records，并暂缓 310 个 program-specific people slots。所有改动只进入独立 Bulk v2 overlay，没有回写 Candidate v2 或 Stage 3/3B/3C/3C2/3D framework artifacts。
- 来源与方法：新增 intake 只使用已直接审阅的学校官方 history/about/catalog/news/archive 页面或官方 PDF。每条正向事实保存短 paraphrase 与短 direct quote；所有 134 条正向引文均通过 gitignored minimal cache 的 SHA-256 与 `local_cache_substring_check` 离线复核，`manual_verbatim_check_count=0`。
- 覆盖：History 62/62；Anecdotes 62/62；Notable attendance 10；Program people 0/310。未创建 fake “无”；所有未审阅 program-person slots 保持 `source_review_not_completed`，`program_people_no_qualifying_person_found_count=0`。
- 决策理由：本 checkpoint 只闭合最能提升详情页展示价值的 history/anecdote 覆盖，不用职业、名气或缺失数据推断人物与专业关系。History/anecdote checkpoint 完成不等于 People/Narrative dataset 完成；包继续标记 `source_limited=true`、`incomplete=true`、`not_final=true`。
- 安全边界：`source_policy_violations=0`、`ranking_field_contamination=0`；没有 frontend 修改，没有 final universe、正式 selection memberships 或 frontend export，也没有恢复 Stage 3A stash。
- 验证：Bulk v2 targeted tests 7/7 通过；独立 validator 通过；全量 Python tests 171/171 通过；fixture/schema/migration validation 通过；byte-identical regeneration 无差异；frontend/upstream non-mutation audit 与 `git diff --check` 均通过。
- 下一步：完成本轮 checkpoint 后再交由 Claude Gate review；在 Gate 之前不进入 frontend，也不把 310 个 program-person slots 作为本轮阻塞项。

## 2026-07-13｜Stage 3D-Fill People Pilot：Reviewed Notable Alumni / Attendees

- 目标与范围：建立独立的小型人物关系验证 overlay；固定 Candidate v2 的 62 所学校，不回写 Candidate v2、Stage 3/3B/3C/3C2/3D framework、Stage 3D-Fill seed 或 Batch 1/2，且未修改 frontend、final universe、正式 selection memberships 或 frontend export。
- 来源与记录：纳入 10 条人工逐字复核的学校官方 institutional records：Princeton（Jeff Bezos）、UT Austin（Matthew McConaughey）、Carnegie Mellon（Andy Warhol）、Georgetown（Bradley Cooper）、Johns Hopkins（Michael Bloomberg）、Washington（Bruce Lee）、Penn（John Legend）、Duke（Tim Cook）、Cornell（Ruth Bader Ginsburg）和 Stanford（Sterling K. Brown）。关系分布为 `graduated=6`、`alumnus_unspecified=3`、`attended_no_degree=1`；未将 alumni class notation 过度提升为毕业事实。
- 专业人物：只填入 1/310 个强证据 slot：Princeton Computer Science 的 Jeff Bezos 为 `direct_related_program_match`，来源直接将 computer science 列入其 Princeton 本科学位；剩余 309 个 slots 保持 `source_review_not_completed`，没有伪造「无」或从职业推断专业。
- 引文与 cache：11 条正向 assertion 全部使用 manifest short-quote allowlist 与 `manual_verbatim_check`；cache manifest 逐 source 披露 `not_cached` 状态和 gitignored cache root，未提交网页快照、完整传记或长文本。validator 同时支持未来 cached source 的 SHA-256 integrity prerequisite。
- 质量与下一步：`source_policy_violations=0`、`ranking_field_contamination=0`。本批标记 `ready_for_claude_gate_review=true`，仅代表可审计审查输入，不是 PASS、complete tag 或完整人物数据库结论；后续 Gate review 应检查每条 relationship、quote 与 degree/major null 的保守性。

## 2026-07-14｜Stage 3D-Fill Bulk Readiness Hardening

- Gate follow-up：People Pilot Gate review 的两个 Medium 已在不扩大数据覆盖的前提下处理。此前 11 条 positive attendance/program-person anchors 全为 `manual_verbatim_check`，且 `canonical_person_id` 为纯 name slug，无法作为 Bulk 的充分防碰撞机制。
- 引文机制：为 11 个已审阅 official source 建立 gitignored reviewed-excerpt cache。每个 cache 只保留 source ID、source URL/reference 与短逐字 excerpt，不保存完整网页快照；version-controlled cache manifest 保存相对路径、SHA-256、review notes 与 verification method。generator/validator 现在要求 `local_cache_substring_check` 同时通过文件存在、SHA-256、source reference 和 quote substring 检查。当前 11/11 条 positive anchors 均由 cache verified，`manual_verbatim_check_count=0`、`cache_missing_count=0`。
- 人物消歧：Pilot 的 canonical IDs 已迁移为 `person:<normalized-name>:<candidate-context>:<source-backed-disambiguator>`。source-backed disambiguator 必须属于同一 candidate；同名人物跨 candidate/source context 不能自动合并，缺少消歧字段的 observation fail closed，并要求未来进入 `same_name_unresolved` exclusion。Jeff Bezos 的 attendance 与 Princeton Computer Science program-person 仍通过相同 hardened ID 关联。
- 边界与验证：未新增人物、history、anecdote 或 Bulk records；没有修改 frontend、上游 artifacts、ranking fields、final universe、正式 memberships 或 frontend export，Stage 3A stash 仍未恢复。新增 regression tests 保护 cache substring、cache hash、name-only ID、same-name context 和 Jeff program linkage；`source_policy_violations=0`、`ranking_field_contamination=0`。

### 已知问题与数据风险

- 未运行真实 PostgreSQL apply test，因为当前没有 PostgreSQL 实例，且本轮不安装大型依赖；外键与约束目前由静态 SQL 审计覆盖。
- JSON Schema 离线 validator 是受控子集，不替代未来 CI 中的完整 Draft 2020-12 validator。
- 前端 export adapter 已验证现有 `UniversityPOI` 兼容性，但真实 canonical 数据尚不存在，因此未写入正式 `universities.json`。

### 下一步建议

执行第二阶段：在访问当天合法确认最新 U.S. News ranking edition，建立 category inventory、coverage report 和人工 seed 工作流，再生成 universe；不得从 fixture 或记忆推导学校名单。

## 2026-07-10｜Gate 1 收口：ranking contract hardening

### 目标

在独立 Gate 1 审计给出 **B. CONDITIONAL PASS** 后，建立可恢复 baseline，并在 ranking discovery 前修复 M4、M5；不进行 U.S. News 搜索或真实学校采集。

### 审计结论与准入判断

- Critical：无。
- High：H1 SQL / Python runtime binding、H2 frontend_fields 直通、H3 tuition / ratio 单来源；它们不阻断只读 ranking discovery，分别延后至 runtime binding / CI、Phase 6 export、Phase 4 tuition / ratio。
- M4 与 M5 直接影响 ranking universe 的分类和纳入事实，因此必须立即修复。完整审计记录见 `docs/database-gate1-audit.md`。

### Baseline 与工作区边界

- baseline commit：`ae3372a`（`chore(data): baseline phase 1 database architecture`）。
- `frontend/package-lock.json` 是预先存在、归属未知的工作区修改；本轮不触碰、不暂存、不提交、不 stash。

### Gate 1 变更

- 新增 `004_gate1_hardening.sql`，以增量 migration 删除 `program_rankings.ranking_category`；category 唯一从 `ranking_snapshots.category` 派生。
- normalization 将学校级 `selection_reason = both` 展开为 `national_top_50` 与 `program_top_20` 两条原子 membership；`both` 不再写入 membership。
- 新增 M4 / M5 回归测试，并增强 migration static audit。

### 验证结果

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`：8 / 8 通过，包含 M4 与 M5 回归。
- `PYTHONPATH=src python3 -m pathos_data validate --fixture tests/fixtures/test-university-raw.json`：通过，覆盖 JSON Schema、fixture pipeline 与 migration static validation。
- `npx tsc --noEmit`（`frontend/`）：退出码 0。
- `git diff --check`：无空白错误。

## 2026-07-11｜Stage 2B1 Pilot：Controlled Ranking Record Collection

### 目标与边界

仅以 3 条代表性 ranking stream 验证真实人工 seed、来源证据、identity mapping 与 verified-only staging；不扩大到其余 26 条 stream，不生成 university universe，不采集学校详情、学费、人物、历史或轶事，也不修改 frontend。

### Dirty worktree 与草稿审计

- 初始工作区因本轮尚未完成的 Stage 2B1 草稿而 dirty；首次严格准入检查已自动停止，未清理、stash、restore 或提交任何草稿。
- 随后执行只读归属审计，结论为 **B. PARTIALLY SAFE**：所有草稿均属于 Stage 2B1，且无 frontend、Supabase、Global/Graduate、selection membership 或 universe 范围外内容。
- 审计发现旧 `validation-result.json` 的 `passed` 当时并非真实命令结果；它不能作为验证证据。该问题在本轮用真实 offline validation 覆盖解决。

### Stream 选择与数据量

- Stream A：National Universities（`numeric_rank <= 50`）；选作综合主流验证。
- Stream B：Undergraduate Business Programs（`<= 20`）；选作有多学校来源和 tie 的宽本科类别。
- Stream C：Aerospace Engineering（`<= 20`）；选作 specialty，并验证 school/college ranking 不等同 canonical program。
- 真实数据边界：7 条 verified records、1 条 `partially_verified` Cornell candidate、0 条 unresolved record；未处理其余 26 条 stream。
- Cornell candidate 因来源只写 `2025-26`、没有直接确证 `2026 Best Colleges` edition，保留为 partial，不能进入 formal staging。

### 验证实现与真实结果

- 实际 Python：`/usr/bin/python3`，Python 3.9.6；不安装 Python、不创建 venv。
- 新增聚合 pilot validator：交叉验证 seed batch、source manifest、identity mappings、candidate observations 和 coverage matrix；只接受 verified record，拒绝 partial/unresolved candidate。
- 实际 pilot validation：3 个 batch 均通过，**7** 条 verified records 可进入 ranking staging；**1** 条 partial candidate 被拒绝；0 条 unresolved；没有创建 canonical university、selection membership 或 frontend export。
- `validation-result.json` 由成功 CLI 于真实执行时覆盖生成，包含 UTC `generated_at` 与 validator metadata；不再保留未经验证的 passed artifact。

### 覆盖、身份与风险

- National Universities 只收集 rank 1–3；rank 4–50 与 tie groups 未覆盖。
- Undergraduate Business Programs 只有 3 verified + 1 partial；其余 `<=20` ranks/ties 未覆盖。
- Aerospace Engineering 只有 1 verified；rank 1、3–20 与 tie groups 未覆盖。
- 7 条 ranking records 映射为 6 个逻辑 institution identity；Georgia Tech 的两个 school 名称显式复用一个 identity。UNITID 全部为 null/not collected，后续必须正式解析，不能猜测。
- U.S. News 直接 ranking pages 的访问限制、manual seed 人工成本、edition 证据不足和不同 stream 来源形态，仍是扩展风险。

### 新增/修改与测试

- 新增 Stage 2B1 seed batch、source manifest、candidate observations、coverage matrix、identity mappings、validation result、聚合 validator schemas 与 `ranking-collection-pilot-report.md`。
- 修改 CLI 以支持多个 seed batch、artifact cross-validation 和真实 result output；新增 pilot regression tests。
- `PYTHONPATH=src python3 -m unittest discover -s tests -v`：33 / 33 通过。
- `PYTHONPATH=src python3 -m pathos_data validate-ranking-discovery ...`：通过。
- `PYTHONPATH=src python3 -m pathos_data validate --fixture tests/fixtures/test-university-raw.json`：通过，覆盖 fixture pipeline、JSON Schema 文档与 migration static validation。
- 完整 artifact CLI validation：通过，真实写入 7 accepted / 1 partial-rejected 的 `validation-result.json`。
- `git diff --check`：通过。
- TypeScript：worktree 中没有 `frontend/node_modules`。临时副本上的 lockfile-pinned `npm ci` 发现预先存在的 package-lock / manifest 不同步而拒绝执行；未修改该 lockfile。随后在另一临时副本使用 `npm install --package-lock=false --ignore-scripts`，`tsc --noEmit` 通过。该结果只证明当前源码可通过类型检查，不证明 lockfile 可复现安装。
- 所有验证后仍不 commit、tag、push。

### 下一步建议

Pilot 本身闭环后可供独立审计或 checkpoint 决策。当前不建议直接扩展剩余 stream 或生成 universe；应先审计来源证据、identity-resolution policy 和 pilot validation contract。

## 2026-07-11｜Gate 2B1 小修复：Evidence validation hardening

### 审计结论与修复范围

Claude Gate 2B1 Fast Audit 对 `3e9573227b38cf9ea156fd2abda3eed469e00e35` 给出 **B. CONDITIONAL PASS**，无 Critical。本轮只修 H1（verified 自证）、H2（edition 标准不统一）和 M1（CLI 可绕过 full artifact validation）；不开始其余 26 条 stream、不生成 universe、不改 frontend。

### H1 与 H2

- `verified` record 现要求每个 `directly_supported_fields` 字段有短、非空、`direct_quote` evidence anchor；anchor field 必须属于 direct fields，且 full artifact validation 会检查 anchor source_id 位于 source manifest。
- 新增 `edition_direct`、`edition_inferred_from_release_cycle`、`edition_ambiguous`。只有 direct edition 可将 `edition` 列为 directly supported；推断或模糊 edition 必须是 partial/unresolved candidate。
- Tepper #6 tie 因只有 release-cycle contextual support，已从 seed 降级为 `partially_verified` candidate；Cornell 的 `2025-26` 继续是 `edition_ambiguous` partial candidate。

### M1、结果与准入

- `validate-ranking-pilot` 现强制 seed batches、identity mappings、source manifest、candidate observations、coverage matrix 与 result output；缺任一参数即 CLI fail closed。底层函数仅供单元测试。
- 重新运行真实 full artifact validation：**6 verified accepted、2 partial rejected、0 unresolved**；validation result 已重生成。
- 当前三个 stream 仍 coverage incomplete，Pilot 仅证明流程与 evidence contract 可行。建议先执行独立 Gate 2B1 audit，再决定是否进入批量阶段；不准生成 universe。

### 测试与风险

- 新增 anchors 缺失、anchor source/field/quote、推断 edition、Tepper/Cornell 状态与 full CLI 参数 fail-closed 回归测试；tie 和 identity tests 继续保留。
- 仍需运行完整 Python、discovery、fixture/migration/schema 与 diff validation 后提交。

## 2026-07-11｜Stage 2B2 Batch 1：Ranking Stream Batch Collection

### 目标与选择

在不生成 universe、selection memberships、学校详情或前端导出的前提下，收集 7 条未处理的 2026 Best Colleges business specialty streams：Accounting、Analytics、Management Information Systems、Production/Operations Management、Management、Supply Chain Management/Logistics、Real Estate。选择它们是因为 ASU 与 UF 官方新闻页面提供直接 2026 edition、类别与 Top-20 rank 证据；Real Estate 使用第二个来源形态交叉 batch 流程。

### 数据、来源与身份

- ASU 官方页面提供前六条 W. P. Carey School of Business records；UF Warrington 官方页面提供 Heavener School of Business Real Estate record。
- 所有 7 条为 `edition_direct` verified，均有字段级短 direct-quote evidence anchors，anchor source 在 Batch 1 source manifest 中。
- Batch 1 full artifact validation 结果：7 verified accepted、0 partial rejected、0 unresolved。
- 7 个 identity mappings 均 resolved，映射到 Arizona State University 或 University of Florida；UNITID 全为 null/not collected，不创建 canonical university。

### 覆盖与边界

- 每个 stream 只收集到 1 条有证据 record，全部标记 incomplete；其余 `<=20` ranks/ties 未覆盖。
- 未处理剩余 stream，未生成 final university universe、selection memberships、canonical university records 或 frontend export。

### Transport error 恢复

- 初次 Batch 1 aggregate test 与随后只读检查发生执行服务 transport decode error。两次均不是业务失败，结果被视为未知；没有绕过、没有伪造结果、没有跳过 full artifact validation。
- 服务恢复后，使用同一 unittest 命令重新运行 aggregate test 并通过，随后才运行正式 full artifact validation 并生成 validation result。

### 验证与下一步

- Batch 1 aggregate test、full artifact validation 已通过；仍需运行全量 Python tests、discovery、fixture/schema/migration 与 diff check 后 commit。
- 建议先复核本批次来源与 coverage，再决定是否执行受控 Batch 2；仍不准生成 universe。

## 2026-07-11｜Stage 2B2 Batch 2：Accelerated Ranking Stream Collection

- 目标：在不生成 universe 的前提下收集 10 条剩余 engineering stream；选择理由是 Georgia Tech College of Engineering 官方 2026 页面同时给出 Doctorate engineering 总类及九个 specialty 的直接 edition/rank 证据。
- 结果：10 verified accepted、0 partial、0 unresolved；所有 records 有 field-level anchors，10 个 identity mappings 均解析为 Georgia Institute of Technology，UNITID 未猜测。
- 覆盖：每条 stream 仅一条 record，全部 incomplete；剩余 ranks/tie groups 未收集。
- 使用 full artifact validation 并真实生成 Batch 2 validation result；不处理剩余 stream、不创建 memberships/universe/frontend export。
- 风险与下一步：单一官方来源形态不证明剩余类别可同样核验；建议继续受控 Batch 3，而非直接处理全部剩余 stream。

## 2026-07-11｜Stage 2B2 Batch 3：Complete Remaining Stream Sweep

- 剩余清单：Entrepreneurship、Finance、International Business、Marketing、Engineering (No Doctorate)、Computer Science、Nursing、Economics、Psychology。
- 结果：UF Marketing direct evidence 产生 1 条 verified accepted record；其余 8 条无合法 direct Top-20 evidence，作为零 verified coverage rows 记录 `no_verified_reason`，不创建 fake seed。
- full artifact validation：1 accepted、0 partial、0 unresolved；8 no-verified streams。所有剩余 category 仍 incomplete，未生成 universe/memberships/frontend export。
- 新增 zero-verified coverage regression；该模式只允许全零计数、明确原因和 incomplete flag。下一步建议进入 full ranking corpus validation，审计跨 batch coverage 与 no-verified reasons。

## 2026-07-11｜Stage 2C：Full Ranking Corpus Validation

- 范围：pilot、batch-01、batch-02、batch-03 的所有 ranking seed artifacts。
- 方法：逐 batch full artifact validation 后，执行跨 corpus duplicate、edition/category/family、anchor source、identity alias、UNITID 与 coverage/scope 检查；生成 corpus validation、coverage、identity、gap、readiness 五个 JSON artifacts。
- 结果：29 / 29 streams 已处理；24 verified、2 partial rejected、0 unresolved、8 no-verified；duplicate / identity conflict / identity unresolved 均为 0。所有 29 streams incomplete，National Universities 仍为 Top-3 pilot coverage。
- readiness：`universe_candidate_ready: true`，`universe_generated: false`。这只表示可在后续生成 source-limited/incomplete university-universe-candidate，不表示 final universe 已准入。
- 风险：没有完整 cutoff、8 条无 verified、学校 identity 尚无 UNITID；建议先审计 candidate-generation contract 与 gap disclosure，再进入 universe candidate generation。
- 未运行网络采集命令；没有真实学校数据、地图组件或 `UniversityPOI` contract 变动。

## 2026-07-11｜Stage 2D：Source-Limited University Universe Candidate Generation

- 目标与输入：只使用通过 Stage 2C corpus validation 的 Pilot、Batch 01、Batch 02、Batch 03 artifacts；没有重新搜索来源、没有新增 ranking record，也没有将 partial、unresolved 或 no-verified stream 作为 verified。
- 生成规则：仅 verified accepted records 可派生 candidate；按 canonical identity 去重；UNITID 保持 null；每个 candidate 和原子 membership 保留 supporting ranking records、streams、source IDs 与 evidence-anchor references。
- 结果：生成 7 个 `source_limited_incomplete` candidate universities 和 7 条 membership candidates，其中 `national_top_50_candidate` 为 3、`program_top_20_candidate` 为 4。24 条 corpus-accepted verified records 在 identity 层归并为 7 所候选学校，额外 17 个 supporting-record occurrences 被去重。
- Membership 语义：`national_top_50_candidate` 与 `program_top_20_candidate` 必须是两条独立 candidate membership；`both` 仅可作为未来 display summary，不能是 membership reason。本批没有 both candidate。
- 排除：Pilot 的 2 条 partially verified rejected observations（包括 Tepper 与 Cornell）、0 unresolved observation 和 8 个 no-verified streams 均未生成 candidate 或 fake school。
- Gap disclosure：National Universities 仅为 Top-3 Pilot，非 Top-50；29 / 29 streams incomplete、8 streams 无 verified record。candidate 明确标记 source-limited、incomplete、not final，禁止用于 final universe、canonical selection memberships 或 frontend export。
- 输出：`data-pipeline/data/university-universe/2026-best-colleges/candidate/` 写入 candidate、atomic memberships、source map、gap disclosure 与真实 validation result；`ranking-collection` 数据未改写。
- 验证：新增 candidate 去重、partial/no-verified 排除、原子 both 展开、membership 全证据保留及 gap disclosure 回归测试；`unittest discover -s tests -v` 为 58 / 58 通过。candidate generation、corpus validation、ranking discovery validation、fixture JSON Schema/migration validation 与 `git diff --check` 均通过。
- 下一步：建议进行 Gate 2 独立审计，重点复核 candidate 只来自 verified corpus、membership 原子语义、provenance 和缺口声明；不准据此生成 final university universe。

## 2026-07-11｜Gate 2 Hardening：Candidate Validator Provenance Check

- Gate 2 审计结论：独立审计对 `6487c138ca2c3508b08a06df987508fa72e48f7a` 给出 **A. PASS**；Ranking Engine / Source-Limited Candidate Generation 已验收合格。审计留下 M-1：旧 validator 只验证结构，不能单独回验 supporting record IDs 是否属于 accepted verified corpus。
- M-1 修复：正式 `validate_candidate` 现必须接受 revalidated corpus 与 `corpus-validation-result.json`，比对 counts、gaps、readiness 后逐条验证 candidate 与 membership supporting records、source IDs、evidence anchors、identity 和 membership reason。任何 partial、unresolved、no-verified、未知或非 accepted record 引用均 fail closed。
- Generator-only：`generate-universe-candidate` 也强制 corpus validation result 输入；`validate-universe-candidate` 成为正式 artifact validation CLI。candidate 必须与当前 corpus 的 deterministic generator output 完全一致，禁止手工编辑。
- L-1：gap disclosure 强制 source-limited、incomplete、not-final、National Top-50 incomplete、all-streams-incomplete、non-negative no-verified count、candidate count 与三项 final-output prohibition。
- L-2：metadata 强制 `source_limited`、`incomplete`、`not_final` 为 true，`final_universe`、`frontend_export`、`selection_memberships` 及兼容 generated flags 为 false。
- 数据边界：未新增 ranking data、未搜索来源、未生成 final universe、未创建 canonical/final selection memberships、未导出 frontend，也未修改 frontend、地图组件或 UniversityPOI。
- 验证：新增 non-corpus/partial membership/anchor、缺失 corpus artifact、empty gap disclosure、metadata truthful flags、final-output flags 与 hand-edited candidate artifact 的 fail-closed 回归测试。`unittest discover -s tests -v` 为 66 / 66 通过；formal `validate-universe-candidate`、corpus validation、ranking discovery validation、fixture JSON Schema/migration validation 与 `git diff --check` 均通过。tag 创建在提交后执行。
- 下一步：可进入 identity enrichment / UNITID 解析；仍需保持 candidate 与 final canonical universe 的边界。

## 2026-07-11｜Stage 2E：Universe Completion Strategy

- 策略调整：先补齐 ranking universe，再做 identity enrichment / UNITID deep work。Stage 3A 草稿已保存到 `stash@{0}`，本轮未恢复、未修改、未提交。
- 输入基线：只读取 Stage 2C / 2D verified corpus、candidate-source-map 和 corpus summaries。当前为 29 scope streams、24 verified records、7 source-limited candidates、29 / 29 incomplete streams、8 no-verified streams；National Universities 仅 Top-3。
- 目标分层：当前 7 所是 source-limited candidate；下一目标是 completed ranking universe candidate v1；final database universe 仍必须等待 completed corpus 与独立 Gate 审计。
- Phase A：National Universities numeric rank <=50，包含所有 ties；按数字 rank/tie group 验收，不以学校数等于 50 代替 coverage。
- Phase B：优先 10 条高 yield streams：Business Programs、Entrepreneurship、Finance、International Business、Marketing、Engineering No Doctorate、Computer Science、Nursing、Economics、Psychology。新增学校贡献只做定性判断，未在无 verified cutoff 前伪造数量预测。
- Phase C：剩余 18 条 included program streams 每批 6 条。每批独立 full artifact bundle；partial/unresolved 只记录、不进入 completed candidate。
- 来源政策：U.S. News 官方公开材料优先，其次直接说明 edition/category/rank 的学校官方页面；禁止搜索摘要、AI 记忆、非官方转载和任何访问控制绕过。没有 direct edition evidence 必须降级。
- artifacts：规划 future `completion-national`、`completion-programs-priority`、`completion-programs-remaining` 和 `completed-candidate` 目录；本轮不创建 collection artifacts 或 ranking seeds。
- 验收：完整 National Top-50 ties、全部 28 program Top-20 ties、verified-only union、identity de-duplication、Global/Graduate zero contamination、completed corpus validation 和 Gate audit 均为必要条件；即使通过也不是完整学校详情数据库。
- 验证：新增 completion-plan schema、CLI 和轻量 tests；`unittest discover -s tests -v` 为 70 / 70 通过。completion-plan、formal candidate、corpus、ranking discovery、fixture JSON Schema/migration validation 与 `git diff --check` 均在提交前重跑。本轮无网络采集、无 final universe、无 selection memberships、无 frontend 修改。

### 延后技术债

M1、M2、M3、M6 以及 H1、H2、H3 均仅记录、未解决；具体延后阶段见 `docs/database-gate1-audit.md`。

## 2026-07-11｜Stage 2F：National Universities Top-50 Manual Seed Import

### 目标、输入与来源限制

- 目标：导入 2026 National Universities 的前 50 个 U.S.-domestic entries，保留原始 PDF `Rank (2026)`，不生成 final universe、selection memberships、canonical university 或 frontend export。
- 输入：用户提供的 Think Academy PDF *Top 100 College Ranking Shifts 2026 vs. 2025*（本地路径记录在 source manifest）。PDF 已通过文本与视觉表格复核，使用字段为 Institution、Rank (2026)、Rank (2025)、Change；只有 Rank (2026) 进入 ranking 字段。
- 该文件被严格标记为 `user_provided_document` / `manual_seed_reference` / `secondary_user_provided`，`official_usnews_source: false`。它是 third-party compiled table，不能表述为 U.S. News 官方完整页面。此前 U.S. News 页面无法在执行环境正常人工复核。
- 既有 U.S. News 2026 Best Colleges release 仅独立交叉支持 Princeton、MIT、Harvard 前三名；Top 4 onward 明确为用户提供 PDF manual seed。后续 Gate 必须审计其可接受性。

### 选择与覆盖语义

- 本轮定义是 first 50 U.S.-domestic entries with boundary tie group，而非 `numeric_rank <= 50`。
- 50 条 accepted entries 的原始 numeric ranks 为 1、2、3、4、6、7、11、12、13、15、17、20、24、26、28、29、30、32、36、40、41、42、46。
- 第 50 条为 University of Rochester，原始 rank 46；rank 46 tie group 的 Lehigh、Northeastern、Purdue Main Campus、University of Georgia、University of Rochester 全部纳入。
- rank 51 的 Case Western Reserve、Florida State、Texas A&M、Virginia Tech、Wake Forest、William & Mary 全部仅记录为 excluded entries，未进入 seed。未发现 non-U.S. institution。

### 验证与风险

- 新增专用 full-artifact validator 与 CLI。它验证 PDF source 不是 official、permission/limitation note、50-entry order、未重编号 rank、rank-46 boundary group、rank-51 exclusions、identity mapping、短 evidence anchors、tie inference、零 final outputs。
- 50 条 identity mappings 均 resolved、UNITID 均未采集；复用 Princeton、MIT、Harvard、Carnegie Mellon、Georgia Tech、Florida、Ohio State 的已有 canonical identity IDs。
- `tied` 仅由同一 Rank (2026) 重复值推断，不写入 `directly_supported_fields`；category/ranking family/edition 的 PDF mapping 也显式与直接表格 name/rank evidence 区分。
- 风险：manual seed 基于用户提供第三方编表；它只能形成 source-limited manual completion，尚不可自行等价为官方-page-direct completion 或 final universe。

### 输出、测试与下一步

- 新增 `completion-national/` raw input、seed batch、source manifest、identity mappings、candidate observations、coverage matrix、excluded entries 与真实 validation result；新增 National completion report、schemas、CLI、validator 与 regression tests。
- 建议下一步先执行独立 Gate review，决定该 manual seed reference 是否可进入 completed corpus；通过 Gate 后才继续 priority program streams completion。不得恢复 Stage 3A stash，也不得导出 frontend。

## 2026-07-12｜Stage 2G-A：Priority Program Streams Official-Source Incremental Batch 1

### 目标与策略调整

- Stage 2G 从“每条 priority stream 一次性完成 Top-20 + ties”调整为官方学校/学院页面的受控增量收集。本批目标约 15 条 verified records；不因零散 records 宣称 stream completion。
- 范围仍是 10 条 Stage 2E priority streams：Business Programs、Entrepreneurship、Finance、International Business、Marketing、Engineering (No Doctorate)、Computer Science、Nursing、Economics、Psychology。未生成 final/completed universe、final selection memberships、canonical university 或 frontend export；未恢复 Stage 3A stash，未改 frontend。

### 来源与数据结果

- 使用 8 个公开可访问的学校/学院官方页面：University of Minnesota Carlson、UC Berkeley Haas、Indiana University、Boston College、University of South Carolina Moore、Loyola Quinlan、Olin College、University of Iowa Nursing。
- 所有 accepted records 均为 `official_institutional`、`official_school_or_college_page_direct`、`edition_direct`，每个 direct field 都有短 `direct_quote` evidence anchor，且 source ID 可在本 batch source manifest 解析。没有 manual seed、搜索摘要、AI 记忆、非官方转载或访问控制绕过。
- 结果：15 verified accepted、0 partial、0 unresolved；coverage 为 Business 3、Entrepreneurship 3、Finance 2、International Business 3、Marketing 2、Engineering No Doctorate 1、Nursing 1。Computer Science、Economics、Psychology 为 `not_collected_in_batch`，仍作为 coverage/gap rows 存在。
- 三条 tie record 有官方页面明确 tie 文本；其他 `tied=false` 仅表示本页未观察到 tie，不是完整 cutoff 的 tie 结论。15 个 record-level identity mapping 都已 resolved 为 8 个稳定 canonical identity；UNITID 全部保持 null/not collected，不猜测。

### Validation、测试与风险

- 新增 Stage 2G-A full-artifact validator、CLI `validate-priority-program-batch`、从已复核官方 observations 生成 bundle 的 CLI `prepare-priority-program-batch`。正式 validation 强制 seed batch、identity mappings、source manifest、candidate observations、coverage matrix、gap report 和 result output；缺少 source manifest 时 fail closed。
- validator 拒绝 partial/unresolved accepted seeds、manual/non-official source、缺失 field-level anchor、无法解析 source、National/Global/Graduate record、非 priority category 以及任何 completed Top-20 claim。
- 新增 10 个回归测试，覆盖 official direct record、incomplete coverage、not-collected row、partial/anchor/source failure、identity reuse、National contamination、防止 final outputs 与 CLI full-artifact fail-closed。
- 初次生成/validation 写文件被本地 sandbox 拒绝，属于执行权限限制而非业务测试失败；在显式受限目录写入授权后，使用同一正式 CLI 成功生成 artifacts 与真实 `validation-result.json`，未用替代脚本绕过。
- 风险：10 条 stream 均未完成 Top-20 + boundary ties；Computer Science、Economics、Psychology 仍无本批 direct record。下一步建议继续 Batch 2（约 15 条 official verified records），同时保持所有 coverage 为 incomplete，直至逐 stream 获得完整 cutoff 证据。

## 2026-07-12｜Stage 2G-B：Full Program Ranking Official-Source Sweep

- 目标：从按约 15 条记录分批的 Stage 2G-A 策略加速为一次覆盖全部 28 条 Stage 2A 纳入范围本科 program streams 的官方来源 sweep；不降低证据要求，也不生成 completed/final university universe、selection memberships 或 frontend export。
- 方法：以既有 pilot、batch-01、batch-02、batch-03 与 Stage 2G-A artifacts 为只读去重基线；仅新增学校/学院公开页面直接同时支持机构、2026 edition、undergraduate category 与 numeric rank 的记录。每条 accepted record 均保存 field-level direct-quote evidence anchors；没有满足所有字段的页面不升格为 accepted seed。
- 新增数据：新增 26 条 verified official institutional records；来源为 UC Berkeley Haas、Indiana University、Minnesota Carlson、Boston College、UC Berkeley CDSS 和 Harvey Mudd College。Texas A&M 页面只披露 public-institution ranking，不能与全体机构 numeric rank 混合，故未进入 accepted seeds。
- 覆盖：聚合 36 条既有 accepted program records 后，28/28 streams 在 coverage matrix 中出现；26 个 stream 仍为 `incomplete`，Economics 与 Psychology 为 `no_verified_records`。没有 stream 被标记 `complete`，因为没有任何 stream 具备完整 first-20-entry plus boundary-tie evidence。
- 去重与身份：新 validator 从既有 artifacts 回验 `(category_id, school_display_name, numeric_rank)`；重复组合 fail closed。新记录复用可识别 canonical identity；所有 UNITID 仍为 null，未猜测或自动模糊合并。
- 新增能力：`official_program_sweep.py`、CLI `prepare-official-program-sweep` 与 `validate-official-program-sweep`；正式 validation 强制 seed batch、identity mappings、source manifest、candidate observations、coverage matrix、gap report、duplicate/dedupe report、existing-artifact root 和 result output。
- 测试与验证：新增 sweep 约束测试，覆盖既有记录去重、partial 拒绝、缺 anchor 拒绝、complete 必须有 Top-20/boundary proof、28 stream 全量覆盖、National/Global/Graduate 隔离与禁止 frontend/final output。完整离线验证结果见本轮 report 和 validation artifact。
- 风险与下一步：官方学校页面通常仅公开本校若干名次，无法证明 cutoff completeness；完成 candidate/final universe 仍被禁止。建议下一步进入 completed program corpus validation / gap repair，仅在取得完整 Top-20 + boundary ties 的合法证据后将单个 stream 标记 complete。

## 2026-07-12｜Stage 2G-C：Program Ranking Remaining Gap Repair

- 目标：以 Stage 2G-B 的 28-stream coverage 为基线做定向 repair，不重跑全量 sweep；优先 Economics、Psychology 与 coverage 最低的 engineering streams。禁止生成 final universe、selection memberships 或 frontend export。
- Economics/Psychology：CU Boulder 官方 Psychology and Neuroscience 页面直接支持 2026 undergraduate Psychology #15，故 Psychology 从 `no_verified_records` 变为 `incomplete`（总 1 条）。Baylor 官方页面给出 Economics #99，超出 PathOS Top-20 scope，仅保存为 `outside_top20_scope` candidate observation；Economics 仍为 `no_verified_records`，没有伪造 Top-20 seed。
- 新增数据：18 条 official institutional、edition-direct、field-anchored accepted records。Texas A&M Engineering 新增 7 条 overall Top-20 engineering records；Bucknell 新增 5 条；Rose-Hulman 新增 5 条；CU Boulder 新增 Psychology 1 条。新 records 仅覆盖 Aerospace、Civil、Computer、Electrical、Industrial、Materials、Mechanical、Engineering Doctorate、Engineering No Doctorate、Psychology。
- 覆盖：修复后，新增 stream 的 previous/new/total 分别详见 repair coverage matrix；所有已有记录 stream 仍为 `incomplete`，仅 Economics 为 `no_verified_records`，没有任何 stream 声称 complete，因为没有 full first-20-entry plus boundary-tie proof。
- 验证与去重：新增 dedicated gap-repair validator 与两个 CLI。正式 path 强制 seed batch、identity mappings、source manifest、candidate observations、coverage、gap report、dedupe report、prior-artifact root 和 result output。prior scan 显式排除当前 repair bundle，避免自身被误判为既有记录；重复 `(category_id, school_display_name, numeric_rank)`、partial/unresolved、anchor 缺失、National/Global/Graduate 混入和 final-output flags 均 fail closed。
- 技术修复说明：首次 formal validation 正确检测到当前 bundle 被 prior scan 重新读入；根因定位后将 prior scan 限定为 pre-repair artifacts，并重新从相同 input 生成 bundle。没有修改来源、学校、排名或证据门槛。
- 跨阶段回归：新增 repair bundle 后，Stage 2G-B validator 曾会把该后续 bundle 计入其冻结 baseline。已用回归测试复现，并将 Stage 2G-B 的 baseline scan 明确排除自身和后续 gap-repair bundle；现 Stage 2G-B 与 Stage 2G-C validators 均可独立重跑。
- 风险与下一步：尽管新增 18 条高置信度数据，28 条 stream 仍未具备 complete Top-20 + boundary ties。建议继续第二轮 focused gap repair，不建议现在进入 completed program corpus validation。

## 2026-07-12｜Stage 2H：Program Top-20 Completion Attempt

- 目标：将既有零散 gap repair 切换为全量 28 条本科 program stream 的 Top-20 completion attempt；验收只认可 first 20 eligible entries 加 boundary tie group，不以 `numeric_rank <= 20` 或零散学校页面代替完整榜单。
- 输入与去重：只读整合 Pilot、Batch 01–03、Stage 2G-A、2G-B、2G-C 与其 coverage/gap/dedupe artifacts。现有 80 条 accepted direct-evidence program records 保留且以 `(category_id, school_display_name, numeric_rank)` 复核为 0 duplicate；本轮没有新增 accepted record。
- 正常来源尝试：以普通访问方式尝试 U.S. News Business 与 Computer Science public ranking URLs，均返回 non-retryable access error。未登录、未绕过 paywall/CAPTCHA/robots、未改请求或使用隐藏接口；因此它们仅作为 `completion_attempt_only` source-limit 记录，不能产生 accepted seed。
- Economics/Psychology：Economics 再次未获得合格 2026 Top-20 direct evidence；既有 Baylor No. 99 只保留为 `outside_top20_scope` observation，Economics 改记 `manual_seed_needed`，不再无限阻塞。Psychology 保留 CU Boulder No. 15 accepted record，但仍为 `incomplete`，因为一条记录不能证明 cutoff 与边界并列。
- 覆盖结论：28 / 28 stream 已评估；`complete=0`、`incomplete=27`、`manual_seed_needed=1`、`no_verified_records=0`（Economics 的原 no-verified 状态被更精确的 manual-seed-needed 状态取代）。`program_top20_completion_ready=false`、`completed_program_corpus_gate_ready=false`；未生成 final universe、selection memberships、canonical university 或 frontend export。
- 新增能力：`program_top20_completion.py`、prepare/validate CLI、full-artifact bundle、readiness/gap/manual-seed reports 与防回归测试。validator 强制全部 28 条 stream 可见，拒绝 fabricated accepted seed、重复统计、缺失 boundary proof 的 complete 声明、遗漏 Economics manual seed disclosure 以及任何 final-output flags。
- 验证：Stage 2H 专用 tests 与 full-artifact validation 已执行；提交前还需重新运行全量 Python tests、既有 completion/gap/sweep/national/candidate/corpus/discovery/fixture/migration validation 与 `git diff --check`。
- 风险与下一步：完整 Top-20 数据仍受官方排名页可访问性限制。建议进行 Claude Gate review，审查合法完整来源或用户提供、可审计的 per-stream manual seeds；该建议不是 completed program corpus acceptance，也不允许生成 final universe。

## 2026-07-12｜Stage 2I：Source-Limited University Universe Candidate v2

- Gate 2H：Claude 独立审核对 `a21b004` 给出 **A. PASS**，允许在不把 program corpus 误写为 complete 的前提下，使用已验收 National completion 与 Stage 2H accepted program corpus 生成 v2 planning candidate。
- 输入：只读取 Stage 2F accepted National Top-50 的 50 条 verified manual-seed records、Stage 2H 聚合的 80 条 verified in-scope program records、resolved identity mappings、Stage 2H readiness/gap disclosures 与既有 v1 artifacts。partial、unresolved、source-blocked attempt-only、Baylor Economics #99 outside-scope observation、Global/Graduate/non-U.S.-News ranking 均不能成为 v2 support。
- 结果：130 条 supporting record occurrences 合并成 62 所 deterministic candidate universities；National-only 45、Program-only 12、Both 5。5 个 Both identity 各保留 `national_top_50_candidate` 与 `program_top_20_candidate` 两条 atomic membership；共 67 条 candidate membership，禁止使用 `both` 作为 stored reason。排除统计为 partial 2、unresolved 0、outside-scope 1；duplicate ranking record 为 0，duplicate identity occurrences merged 为 68；UNITID 全部保持 null，未做模糊合并或 deep identity enrichment。
- 状态披露：所有 artifacts 强制 `source_limited=true`、`incomplete=true`、`not_final=true`；`final_universe=false`、`official_selection_memberships_generated=false`、`frontend_export_generated=false`。National Top-50 已 accepted；program streams 为 complete 0、incomplete 27、Economics manual_seed_needed 1，故 program Top-20 corpus 仍不完整。candidate v2 仅可支持 future deep-dataset planning，不能进入正式产品或 frontend。
- M-1 来源政策修复：`docs/database-source-policy.md` 现明确 CollegeData 只可用于带 field-level provenance 的 detail enrichment；THE、QS、xuanxiao.org 只可写入独立 non-U.S.-News reference，绝不能写入或覆盖 U.S. News ranking fields。detail 冲突优先学校官网/CDS、IPEDS/NCES、College Scorecard、CollegeData/secondary；U.S. News rank 仅可来自官方、已审核 manual seed 或学校官方直接引用页面。
- 验证：新增 v2 deterministic generation、National/program input count、partial/outside-scope exclusion、identity dedupe、atomic membership、Economics/incomplete disclosure、final-output flags 与 source-policy boundary tests。正式 full-artifact validation 对生成结果通过；提交前还需重跑全量 tests 与既有 validators。未采集 detail data、未改 frontend、未恢复 Stage 3A stash、未连接 Supabase。
- 下一步：建议 Gate 2I Claude review，审计 v2 deterministic provenance 与 M-1 source-policy boundary；该 Gate 不是 final universe acceptance。

## 2026-07-12｜Stage 3：Program-Centric MVP Detail Pack

- 目标：以 Gate 2I 已验收的 source-limited Candidate v2（62 所学校、67 条 atomic memberships）为 planning 输入，生成黑客松 demo 所需的专业中心详情包；它不是 final universe，也不生成正式 selection memberships、frontend export 或任何前端修改。
- 决策：不伪造 program-level tuition。NCES/IPEDS IC2023_AY 仅提供 institution-level 本科 tuition 与 required fees，因此所有可展示金额明确标为 university-level applied tuition、`program_specific=false`。公立校同时保存 in-state / out-of-state，并以 out-of-state total 作为 demo default；私立校保存 single undergraduate rate。没有可靠身份匹配或 tuition 记录时，写 `not_published` 与 null reason。
- 身份与 majors：HD2024 只采用 candidate display/source/alias 到机构名的 exact normalized match，避免 campus/system 猜测；51 所精确解析、11 所保留 unresolved。C2023_A 的 bachelor-degree award areas 与官方 CIP 名称用于结构化 `areas_of_study`，明确不是 current catalog assertion；51 所有该清单，11 所记录 gap。
- 专业：优先读取已有 accepted U.S. News program records；不足五个时才用 IPEDS reported bachelor award areas 补作 `ipeds_reported_award_area` demo candidate，并明确不是学校 current major list 或排名。54 所有五个 provenance-backed demo programs，8 所有明确少于五个的 gap reason。
- 师生比：本轮没有使用能严格支持该字段的 selected input；62 所均保留 explicit null reason，而非由 enrollment/staff 等不相关字段推断。该 gap 符合 Stage 3 的诚实披露边界，后续应以 Common Data Set、IPEDS/College Scorecard 或官方 facts page 补齐。
- 工程：新增 deterministic `stage3_program_mvp.py` generator/validator、CLI generate/validate commands、Stage 3 regression tests 与八个 artifact。正式写入路径调用 `validate_source_policy_use("IPEDS", "detail", has_field_provenance=True)`；summary 强制 `source_policy_violations=0` 与 `ranking_field_contamination=0`。
- 安全验证：本科 tuition guard 明确拒绝 COA、graduate/MBA/law/medical/professional tuition；回归测试同时确认合法的 `undergraduate tuition` 文本不会被错误视为 graduate tuition。highest/lowest 仅针对可比较 tuition；51 所因统一 university-level rate 允许相同，11 所为 null。
- 风险与下一步：detail pack 仍 source-limited、incomplete、not final。应先审核 Stage 3 字段 provenance 和对 11 个 identity gap 的处理，再进行 student-faculty ratio、官方 catalog、官方 tuition page 或 UNITID identity enrichment；不得将本包直接作为正式产品数据。

## 2026-07-13｜Stage 3B：Demo Critical Gap Fill

- 目标：在不改 Candidate v2、Stage 3 artifacts、frontend 或排名 corpus 的条件下，以独立 overlay 补最影响 demo 的 detail gaps；不生成 final universe、正式 selection memberships 或 frontend export，也未恢复 Stage 3A stash。
- 基线一致性：Stage 3 summary 的实际不足五个 demo programs 为 8 所，但 6 所已有五个 programs 的 row 残留旧 `top_5_gap_reason`。Stage 3B 从实际 program count 派生 gap：清除这 6 条 stale reason，保留真实不足五项的 gap；Stage 3 原始 artifact 保持只读。
- Ratio：从公开 College Scorecard institution-level release 的直接 `STUFACR` 字段为 62/62 所生成 student-faculty ratio，保留 UNITID row anchor、release reference、definition/extraction notes。所有结果 `derived_ratio=false`；未将该联邦字段表述为学校 facts-page ratio，也未用第三方来源。
- Identity / tuition / majors：对 11 个原 identity gap 创建版本控制的 explicit reviewed alias mapping。每个 mapping 必须指向唯一 exact IPEDS HD2024 `INSTNM`，并排除同系统/同名其他 campus。11/11 通过该 exact path 解析，随后只用既有 IPEDS inputs 补 university-level undergraduate tuition 和 bachelor award areas；未猜 UNITID，也未改排名字段。
- Demo programs：仅从学校官方本科页面补充。Columbia、Ohio State、Olin、South Carolina、UT Austin、UVA、UW 的 7 个实际 gap school 补至五项；UNC Chapel Hill 保留 3 个经官方本科目录支持的 Asian Studies concentrations，仍为明确 gap。新增项全部为 medium-confidence official undergraduate demo supplement，不是 U.S. News ranking。
- 结果：identity/tuition/majors original gaps 11 均 resolved；program gaps original 8、resolved 7、remaining 1；student-faculty ratio resolved 62。demo readiness 在与 Stage 3 相同的四维覆盖口径下从 0.629 升至 0.996；source-policy violations 与 ranking-field contamination 均为 0。
- 验证：新增 deterministic generator、formal generate/validate CLI、independent artifacts、5 个 Stage 3B regression tests；validator 检查 Candidate v2 62 校范围、immutable Stage 3、stale-gap 清理、ratio provenance、reviewed exact aliases、undergraduate-only tuition/program sources、U.S. News field isolation 与 final-output prohibitions。
- 风险与下一步：overlay 仍 source-limited、incomplete、not final；UNC 仍未满五个 demo programs，任何后续补充必须来自可复核的官方本科页面。进入 frontend demo 前仍应保持本包和 final database/universe 的边界。

## 2026-07-13｜Stage 3C：Academic + Geo Enrichment

- 目标：构建独立、deterministic 的 Academic + Geo overlay，补强官方本科 major provenance、UNC demo-program gap、undergraduate tuition-deepening/highest-lowest basis、Census 四区与最近 place；不改 Candidate v2、Stage 3、Stage 3B、frontend 或 Stage 3A stash。
- Academic：UNC 2026 official Undergraduate Programs of Study catalog 的直接短摘录支持 `Computer Science Major, B.S.` 与 `Economics Major, B.A.`。二者作为 official undergraduate demo supplements 写入 Stage 3C，U.S. News category/rank 均为 null，因此 UNC 从 3 项补至 5 项而没有新增 ranking record。官方 majors uplift 是 best-effort：1 所有 reviewed official undergraduate-program source，61 所保留带 limitation 的 IPEDS bachelor-degree award-area fallback；没有任何 IPEDS area 被写成学校 catalog。
- Tuition：62 所继续使用经来源验证的 institution-level undergraduate tuition confirmation；本轮没有新增 college surcharge、program-level fee 或 mixed differential。51 所的 highest/lowest basis 是 `university_level_same_for_all`，11 所为 `not_published`；没有从缺失数据、course fee、COA、room/board、books、transportation、graduate/MBA/law/medical/professional tuition 推断金额。
- Geography：所有 62 所按受控 Census 四区映射到 Northeast/Midwest/South/West。Stage 3/3B 原始 longitude 为 null 的展示缺口只在 Stage 3C overlay 中从既有 IPEDS `LONGITUD` field-level provenance 恢复；不回写上游。正常 Census 2024 Gazetteer ZIP 下载返回 HTTP 403，普通 TigerWeb query 被执行环境拒绝；未绕过限制，未用未审查 fallback，故全部 `nearest_towns=[]` 并记录 `source_unavailable_in_execution_environment`。
- 验证：新 generator/validator 检查 62-ID scope、Stage 3/3B SHA-256 immutability、官方本科 observation、ranking isolation、forbidden tuition、Census taxonomy、Haversine-only contract、cache exclusion 与 final-output flags。source-policy violations 与 ranking-field contamination 均为 0。
- 风险与下一步：nearest places 是唯一明显的 Stage 3C geo blocker；仅在正常可访问的官方 Census cache 可用时重试，不得猜 town。Stage 3C 仍 source-limited/not-final，建议独立 review 后才进入 Stage 3D People + Narrative。

## 2026-07-13｜Gate 3C Medium-1：Geo Readiness Clarification

- 背景：Gate 3C 对 `3de0bb8` 给出 **CONDITIONAL PASS**。审计确认 nearest towns 的 0 / 62 缺口已被诚实披露，但单一 headline `demo_readiness_after=1.0` 容易被误读为所有 Geo enrichment 已完成。
- 修复：Stage 3C summary 现将 program 与 Geo nearest-town 口径拆开：`demo_program_readiness_after=1.0`；保留的 `demo_readiness_after=1.0` 明确标为 `legacy_program_only`；`geo_nearest_towns_readiness=0.0`、`nearest_town_coverage_count=0`、`nearest_town_total_count=62`、`nearest_town_completion_status=incomplete_source_unavailable`。Region readiness 仍为完成，但 Stage 3C 整体明确为 Academic + partial Geo overlay。
- 披露与验证：gap disclosure 保留 `source_unavailable_in_execution_environment`，明确 Census Gazetteer 与 Census TigerWeb 在当前环境不可用，且没有绕过、猜测或伪造距离。formal Stage 3C validator 现同时检查 summary、gap disclosure 和必需 report wording；它允许 Academic + partial Geo overlay 通过，但拒绝把 nearest towns 写成 complete。
- 边界：没有开始新的 nearest-town 采集、没有引入新地理来源；没有修改 Candidate v2、Stage 3、Stage 3B、frontend、final universe、正式 selection memberships 或 frontend export；Stage 3A stash 未恢复。

## 2026-07-13｜Stage 3C2：Nearest Towns Gap Repair

- 目标：只修复 Stage 3C 的 nearest-town gap；保持 Candidate v2 固定 62 所、Stage 3/3B/Candidate v2 只读，且不改变 ranking fields、frontend、final universe、正式 selection memberships 或 frontend export。
- 来源：使用用户提供并审核的 U.S. Census 2024 National Places Gazetteer cache（`2024_Gaz_place_national.zip`，SHA-256 `cf262fc92b2326f7a8c62a89d156a60eb17d64d6d35f7a62310c43bb08972c06`）。cache 继续 gitignored；commit 仅保留 source manifest、选择后的 structured observations、计算、披露与 validation artifact。
- 方法：从 Census `NAME`、`LSAD`、`USPS`、`INTPTLAT` 与 `INTPTLONG` 读取 permitted Census places；仅输出 city、town、incorporated place 或 CDP，拒绝 county、campus、neighborhood、school facility、metro area 与未分类标签。每校按 deterministic Haversine 直线距离选择 3 个不同 place，保留学校/place 坐标、公里/英里、source ID/reference、`campus_city_included` 与 “not driving distance; not travel time” notes。
- 结果：62 / 62 schools resolved，186 nearest-town observations，`geo_nearest_towns_readiness=1.0`，无 unresolved university。Census cache 不含人口数，`population_class` 均保持 null，并带 `not_provided_by_census_2024_places_gazetteer` disclosure；没有估计人口或距离。
- 验证与边界：新增 deterministic generator、formal validator、CLI 与 regression tests。validator 复算每条 Haversine distance，拒绝 forbidden place type、未带 source 的 observation、driving/travel-time claim、cache 进入 Git、范围扩张、ranking contamination 和任何 final-output flag。`source_policy_violations=0`、`ranking_field_contamination=0`。

## 2026-07-13｜Gate 3C2 Medium-1：Campus-City Flag Normalization

- 背景：Gate 3C2 对 `b3a8265` 给出 **CONDITIONAL PASS**。nearest-town places 与 Haversine distances 均可复核，但 `campus_city_included` 因 school state 使用 USPS 两字母缩写、Census place state 使用全称而系统性为 false。
- 修复：生成器现对学校与 Census place 的 state 统一转换为 Census 全称后的规范化值，再与规范化 city 一起比较；不会改变 place selection、排序或距离。修复后 46 / 62 所学校的 campus city 入选最近 places，且每所至多一条对应 place。
- 防回归：新增 ASU（Tempe / AZ vs Arizona）、Harvard（Cambridge / MA vs Massachusetts）、Brown（Providence / RI vs Rhode Island）覆盖，并断言同校其他 nearest places 不得误标。formal validator 逐条重算 normalized city/state predicate，拒绝任何 false negative 或 false positive；summary/report 同时披露 `campus_city_included_university_count=46` 与 `campus_city_included_place_count=46`。
- 边界：未引入新地理来源，仍只使用 reviewed Census cache；没有修改 Stage 3、Stage 3B、Stage 3C、Candidate v2、frontend、ranking fields 或 final-output artifacts，Stage 3A stash 未恢复。

## 2026-07-13｜Stage 3D：People + Narrative Enrichment

- 目标与边界：为固定 Candidate v2 的 62 所学校建立独立、deterministic、source-limited 的 People + Narrative overlay；不回写 Candidate v2、Stage 3、Stage 3B、Stage 3C 或 Stage 3C2，不修改 frontend、ranking fields、final universe、正式 selection memberships 或 frontend export，也未恢复 Stage 3A stash。
- 数据契约：每个 Stage 3C top-5 demo-program slot 都有一条 Stage 3D row。`identified` 必须由 source-backed person identity、short direct quote、direct major match 和允许的学生关系支持；`无` 只可在 non-empty `reviewed_scope` 与 `reviewed_source_ids` 已定义的已审查来源范围内使用。为避免把未审查误写成“不存在”，本初始输入批次的 310 个 slots 全部明确为 `source_review_not_completed`，不显示为「无」。
- 关系与叙事保护：严格区分 `graduated`、`attended_no_degree`、`alumnus_unspecified`、`faculty_only`、`honorary_degree_only`、`donor_only` 与 `unclear`；只有前三者可进入学生/校友输出。major、degree、就读、history 和 interesting fact 均需要自己的短 evidence anchor。叙事正文只能是短 paraphrase，不能复制长 biography、history 页面或编造故事。
- 初始 coverage：62/62 所学校均有 Stage 3D university row，310/310 top-program slots 有显式 collection status；本批尚未提交任何 approved affirmative people、attendance、history 或 interesting-fact observation，因此 identified、scoped 「无」、attendance、history 和 interesting-fact counts 均为 0。该状态是可审计的输入来源缺口，不是任何人物、专业或历史事实的否定声明。
- 工程与政策：新增 `stage3d_people_narrative.py` generator/validator、generate/validate CLI、structured source/observation input contracts、independent artifacts/report 与 regression tests。正式 positive-source ingestion path 调用 `validate_source_policy_use(..., "detail", has_field_provenance=True)`；validator 拒绝 ranking fields、fuzzy person merge、faculty/donor/honorary student claim、未锚定事实、未披露的「无」以及 upstream artifact drift。`source_policy_violations=0`、`ranking_field_contamination=0`。
- 风险与下一步：Stage 3D 的机制和透明 gap disclosure 已就位，但仍需要逐学校审查学校官方 alumni/archive/history sources 后才可填入 affirmative people/narrative records 或 scoped 「无」。在该 collection 完成并独立审核前，Stage 3D 仍是 incomplete/not-final demo overlay，不能作为正式人物数据库或 frontend export。

## 2026-07-13｜Stage 3D-Fill：Reviewed People + Narrative Source Fill

- 目标与边界：新增独立 reviewed-source fill overlay，不回写 Candidate v2、Stage 3/3B/3C/3C2/3D framework，不修改 frontend、ranking fields、final universe、正式 selection memberships 或 frontend export，也未恢复 Stage 3A stash。
- 机制：每个 Stage 3C top-5 demo-program slot 都由 deterministic generator 输出 `identified`、scoped 「无」或 `source_review_not_completed`。后两者严格区分：只有明确记录 non-empty reviewed source scope/IDs 且无合格证据时才可写「无」；未审查绝不写成「无」。正向 people、attendance、history、anecdote 均要求 resolved identity（如适用）、manifest source、短 direct quote 与短 paraphrase。
- 本批 source intake：以 normal public access 复核 Harvard 官方历史页，并只纳入一条可直接支持的短历史事实：Harvard 将其机构创立追溯至 1636 年（`source_harvard_official_history_2026`）。该条目为短 paraphrase 加短 quote，不支持人物、就读、专业或佚事。其余 61/62 history 与 310/310 program slots 仍是明确的 `source_review_not_completed` gap；没有虚构 scoped 「无」或任何未审查正向事实。
- 工程：新增独立 generator、full-artifact validator、CLI、source/observation contracts、artifacts、report 与 regression tests。validator 保护 Candidate 62 校范围、310 slot 范围、relationship allowlist、short quote/paraphrase、U.S. News ranking isolation、immutable upstream fingerprints、final-output flags 与 deterministic regeneration；`source_policy_violations=0`、`ranking_field_contamination=0`。
- 风险与下一步：该 commit 建立可安全填充的 intake path，但并不宣称 People/Narrative data collection 已完成。下一次只有在官方 alumni/archive/history 页面可正常访问并逐条复核后，才可增加 affirmative observations 或已审查 scoped 「无」。

## 2026-07-14｜Stage 3D-Fill Bulk Completion v2

- 目标与边界：建立独立 Bulk v2 People/Narrative overlay，固定 Candidate v2 的 62 校范围；未回写 Candidate v2、Stage 3/3B/3C/3C2/3D framework、Stage 3D-Fill seed、Batch 1/2 或 People Pilot，也未修改 frontend、ranking fields、final universe、正式 memberships 或 frontend export；Stage 3A stash 未恢复。
- 来源与证据：本轮复用 Batch 1/2 的 16 条 reviewed history、16 条 reviewed anecdote 和 People Pilot 的 10 条 reviewed attendance，并以正常访问、人工复核的 MIT、Caltech 与 UC Berkeley 官方页面新增 3 条 history 和 3 条 anecdote。每个正向短 quote 已进入 gitignored reviewed-excerpt cache，生成器对 SHA-256、source reference 和 substring 执行 fail-closed 的 `local_cache_substring_check`；没有提交网页快照或长原文。
- 覆盖与披露：history 为 19/62、anecdote 为 19/62、notable attendance 为 10 条；其余 43 校 narrative 缺口和全部 310 个未审查 program-person slots 保持 `source_review_not_completed`，没有被写成「无」。这是一层 cache-verified re-packaging/守卫加固，不把已存在的来源复用或少量新增来源错误表述为 complete dataset。
- 质量护栏：新增独立 generator、CLI、validator、artifacts、report、cache manifest 和 regression tests；source-policy guard 在 Bulk 写入路径被测试调用。人物 ID 禁止纯姓名 slug；attendance 只允许 `graduated`、`attended_no_degree`、`alumnus_unspecified`；职业不会推断专业或 program match。`source_policy_violations=0`，`ranking_field_contamination=0`。
- 风险与下一步：该 Bulk v2 骨架已可安全接受高吞吐量的官方 history/about/alumni intake，但本次并未虚构或批量抓取 46 个尚未逐条审阅的学校。后续应通过正常可访问官方页面逐源写入 observation 与最小 cache excerpt，再重新生成和 Gate review；仍是 source-limited、incomplete、not-final。

## 2026-07-14｜Stage 3D-Fill Bulk People Completion v1

- 目标与范围：在固定 Candidate v2 的 62 所学校内完成 notable-attendance 学校覆盖，并保持 program-specific people 暂缓。本阶段建立独立 overlay，不回写 Candidate v2、Stage 3/3B/3C/3C2/3D framework、Stage 3D-Fill 既有 batches、People Pilot 或 Bulk v2；未修改 frontend，未生成 final universe、正式 memberships 或 frontend export，Stage 3A stash 未恢复。
- Reviewed intake：复用已通过 hardening 的 People Pilot 10 条 attendance，并从 52 个学校官方 institutional/alumni/profile 来源各新增 1 条高置信 attendance。关系严格限制为 `graduated`、`alumnus_unspecified` 或 `attended_no_degree`；最终分布为 41 / 18 / 3。major 未被来源明确支持时保持 null，并标注 `major_not_stated_in_accepted_source`，没有从职业或名气推断专业。
- 覆盖：notable attendance 从 10 条 / 10 校提升为 62 条 / 62 校；每校恰有 1 条 reviewed record。program people 保持 0 / 310，全部 slots 继续为 `source_review_not_completed`，没有制造「无」或扩大 program-person intake。
- Provenance 与 identity：全部 62 条 positive attendance 使用短 direct quote、`local_cache_substring_check`、gitignored reviewed-excerpt cache 与 SHA-256；`manual_verbatim_check=0`、`cache_missing_count=0`。canonical person ID 由 normalized name、candidate context 与 source-backed disambiguator 组成，禁止纯姓名 ID、fuzzy merge 与跨 context 自动合并。
- 工程：新增 deterministic generator、fail-closed validator、generate/validate CLI、structured source/cache/attendance inputs、独立 artifacts、report、tests 与本日志。validator 拒绝 cache SHA/substring 失败、未允许的关系、ranking contamination、缺失 source URL、纯姓名人物 ID、上游范围变化与 program-person 扩张；`source_policy_violations=0`、`ranking_field_contamination=0`。
- 状态与下一步：该层仍为 `source_limited`、`incomplete`、`not_final`。下一步应先进行独立 Gate review；按本阶段约束，在 Gate 前不继续扩展 program people，也不进入 frontend/export。

## 2026-07-14｜Stage 3D-Fill Bulk People v2：Top-1 Slot Pipeline

- 目标与边界：为固定 Candidate v2 的 62 所学校建立独立 Top-1 demo-program person slot pipeline；每校处理一个 slot，但本轮只实现 reviewed-source intake 机制，不采集真实人物。Candidate v2、Stage 3/3B/3C/3C2/3D framework、Stage 3D-Fill Batch 1/2、Bulk People v1 与 frontend 均保持只读；未生成 final universe、正式 memberships 或 frontend export。
- Schema：新增版本化 slot schema，强制 `candidate_id`、canonical identity、不可变 Top-1 program provenance、人物/关系/program-match/source/evidence/reviewed-scope/null 字段。`slot_status` 只能是 `identified_person`、`source_review_not_completed` 或 `no_qualifying_person_found`；不存在第四种状态。
- Validator：identified path 必须同时具备允许的 attendance relationship、source-stated direct/related program match、source-disambiguated person ID、两组 short direct-quote anchors 与 SHA-256 cache-backed `local_cache_substring_check`。纯姓名 ID、fuzzy merge、跨来源未确认身份、职业/公司/名气/研究领域推断、faculty/donor/honorary/unclear relationship、manual-only quote、ranking field contamination 和 upstream SHA drift 均 fail closed。`no_qualifying_person_found` 仅接受 non-empty reviewed scope 与 reviewed source IDs。
- 空 overlay 结果：62 / 62 Top-1 slots 已处理；`identified_person=0`、`source_review_not_completed=62`、`no_qualifying_person_found=0`。没有把未审查资料写成「无」，people observations、source/cache manifests、matches 与 exclusions 均为空。所有 program provenance 逐项复制 Stage 3C 的既有 Top-1 record。
- 测试与验证：先确认 7 个初始目标测试因模块缺失而红灯，再实现 generator/validator/CLI；补充同名未确认必须进入 `same_name_unresolved` exclusion 的回归覆盖后，专用 tests 达到 8 / 8 绿灯。独立 artifact validator 通过 22 项检查；`source_policy_violations=0`、`ranking_field_contamination=0`、`manual_verbatim_check_count=0`。完整 Python、schema/migration、deterministic regeneration 与 non-mutation 结果记录在本轮最终实施报告中。
- 风险与下一步：pipeline 已能安全接收未来 reviewed Top-1 program-person observations，但当前 positive coverage 仍为 0 / 62；这不是人物不存在的声明。本轮保持 `source_limited`、`incomplete`、`not_final`，等待后续明确授权后再逐校进行 reviewed intake。

## 2026-07-14｜Stage 3D-Fill Bulk People v2：Reviewed-Source Intake Batch A

- 目标与范围：只处理 Harvard、Princeton、MIT、Stanford、Yale、UC Berkeley、Columbia、Cornell、Duke 与 University of Michigan 这 10 所批准学校；每校复核 1 条 notable attendance，并处理其不可变 Top-1 demo-program person slot。Batch A 是独立 overlay，不回写 Candidate v2、Stage 3/3B/3C/3C2/3D、Bulk People v1 或 frontend，也不生成 final universe、memberships 或 frontend export。
- Attendance intake：复用 Bulk People v1 已通过官方来源、短 direct quote、gitignored local cache 与 SHA-256 验证的 10 条 attendance records。Batch A generator 再次逐条核对 source/candidate relationship、允许关系、source URL、verified quote allowlist、cache SHA 与 substring；结果为 10 / 10 identified attendance，`manual_verbatim_check=0`、`cache_missing=0`。
- Program-person intake：只有 Princeton 的 Jeff Bezos record 同时明确支持 Princeton attendance 和 Electrical Engineering and Computer Science undergraduate degree，因此以 `direct_related_program_match` 对应不可变 Computer Science Top-1 slot。其余 9 个 slots 没有经本批审查的明确 major/program match，继续保持 `source_review_not_completed`；没有根据职业、公司、名气或研究方向推断专业，也没有生成 `no_qualifying_person_found`。
- Identity 与政策：Jeff Bezos 继续使用 normalized name、Princeton candidate context 与 reviewed Princeton source ID 组成的 deterministic canonical person ID；禁止 name-only ID、fuzzy merge 和跨 context 自动合并。所有 positive facts 使用 `local_cache_substring_check`，source-policy violations 与 ranking-field contamination 均为 0。
- 工程与测试：新增 Batch A generator/validator、generate/validate CLI、reviewed observation input、11 个独立 JSON artifacts、report 与 7 个 TDD regression tests。validator 固定 pipeline v2 与 Bulk People v1 input SHA，拒绝 forbidden relationship、职业推断、缺失 attendance/program anchors、manual quote、cache/allowlist mismatch、未披露的 scoped none 与 deterministic drift。
- 状态与下一步：Batch A 为 `source_limited`、`incomplete`、`not_final`；program-person coverage 为 1 / 10（本批）且不能外推为 62 校完成。提交后应停止并等待独立 Gate review，不继续扩大 program people intake。

## 2026-07-13｜Gate 3D-Fill High-1：Verbatim History Anchor

- 背景：Gate 3D-Fill 对 `44276ed` 给出 **CONDITIONAL PASS**；Harvard 1636 founding fact 的原有 `direct_quote` 是释义式短语，而不是 cited official history page 的逐字原文。
- 修复：Harvard history observation 现使用该官方页的逐字短句：`On October 28, 1636, Harvard, the first college in the American colonies, was founded.`；history factual paraphrase 仍保持独立的短摘要，事实含义未变。
- 流程护栏：所有 Stage 3D-Fill direct-quote anchor 必须记录 `quote_verification_method`，允许 `manual_verbatim_check` 或 `local_cache_substring_check`。Harvard 记录为 `manual_verbatim_check`；source manifest 同时保存经审查的短 quote allowlist，generator/validator 因而拒绝将改写的 paraphrase 标为 `direct_quote`。
- 边界：没有扩展 reviewed source intake、人物、就读、历史或 anecdote 数据；没有把未审查内容写为「无」，且没有修改 frontend、上游 artifacts、ranking fields、final universe、正式 memberships 或 frontend export；Stage 3A stash 未恢复。

## 2026-07-13｜Stage 3D-Fill Batch 1：Reviewed History + Anecdotes

- 目标：在固定 62 所 Candidate v2 范围内建立独立 Batch 1 reviewed source-intake overlay；优先 history 和可展示的 interesting facts，少量 attendance/program people 仅在来源直接支持时填入。上游 Candidate v2、Stage 3/3B/3C/3C2/3D framework 与 Stage 3D-Fill seed 均只读。
- 来源：仅使用本批正常访问并人工复核的学校官方 history 页面：Harvard、Princeton、Stanford、University of Pennsylvania、Northwestern、Vanderbilt、University of Notre Dame 与 Carnegie Mellon。每个 affirmative record 只保存短 paraphrase、manifest URL 和逐字短 quote；quote 以 `manual_verbatim_check` 标记并与 source manifest reviewed short-quote allowlist 匹配。未保存网页快照或长原文。
- 覆盖：本批填入 8/62 history summaries 和 8/62 anecdotes；54 所 history、54 所 anecdotes 仍为 `source_review_not_completed`。没有新增 notable attendance 或 program-specific person；全部 310 个 program slots 保持未审查 source gap，而非伪造「无」。
- 工程与政策：新增独立 Batch 1 generator、validator、CLI、inputs、artifacts、report 与 regression tests；validator 固定 Candidate/Stage 3C/Stage 3D-Fill seed fingerprints，拒绝 quote allowlist 外的 paraphrase、excluded person relationship、ranking contamination、final output flags 或范围扩张。`source_policy_violations=0`、`ranking_field_contamination=0`。
- 风险与下一步：本批是 reviewed intake 的小批量开始，不能称为 62 所学校的完整人物/叙事数据库。后续继续按正常可访问官方 archive/alumni/history 页面增量收集；找不到合格来源时继续保留 source gap，不得猜测。

## 2026-07-13｜Stage 3D-Fill Batch 2：Reviewed History + Anecdotes Expansion

- 目标与范围：在 Claude 暂不可独立 Gate review 时执行小批量、低风险、可审计的 reviewed-source expansion；固定 Candidate v2 62 校范围，新增 8 条 history 与 8 条 anecdote，未回写 Candidate v2、Stage 3/3B/3C/3C2/3D、Stage 3D-Fill seed 或 Batch 1 artifacts。
- 来源与方法：仅纳入正常访问并人工逐字复核的学校官方 history/about 页面：University of Chicago、UCLA、Johns Hopkins、University of Washington、UT Austin、Georgetown、Emory 与 University of Rochester。每条记录只保存短 factual paraphrase、official source reference、短 direct quote 与 `manual_verbatim_check` allowlist entry；未提交网页快照、长文本或完整 biography。
- 覆盖：Batch 2 为 8/62 reviewed history、8/62 reviewed anecdotes；与不可变 Batch 1 合计为 16/62 history、16/62 anecdotes。notable attendance 与 program-specific people 均为 0；310 个 demo-program slots 均保持 `source_review_not_completed`，没有把未审查的来源缺口写成「无」。
- 质量与边界：generator/validator 检查 Candidate scope、Batch 1 non-duplication、source manifest/short-quote allowlist、relationship allowlist、paraphrase 与 quote 长度、upstream fingerprints、ranking isolation 与 final-output prohibitions。`source_policy_violations=0`、`ranking_field_contamination=0`；没有 frontend、final universe、正式 selection memberships、frontend export、tag、push、merge、rebase 或 Stage 3A stash restore。
- 验证与下一步：Batch 2 package 会标记 `ready_for_claude_gate_review=true`，这只表示未来 Batch 1 + Batch 2 联合审计的输入已就绪，不是 PASS 或 complete 结论。Claude 恢复后应先做联合 Gate review；未覆盖学校仍须继续保持 scoped source gap，不能据此推出人物或历史事实不存在。

## 2026-07-10｜Stage 2A：Ranking Discovery and Scope Inventory

### 目标

确认执行日的 ranking edition，建立 family/category inventory、来源可访问性审计、manual seed 机制和 Stage 2B 输入；不生成 university universe、不采集学校详情、不改动前端。

### 隔离工作区

- worktree：`/Users/jiayihuang/PathOS-db-ranking`
- branch：`feature/database-ranking-discovery`
- base：`pathos-db-gate1-pass`（`03f74100701a99a48dfdc2b3a02846fe7a013c0b`）
- 原主工作区的 `frontend/package-lock.json` 未复制、未修改、未暂存。

### 方法与来源

- 使用 U.S. News 通过 PR Newswire 发布的官方 2026 Best Colleges 新闻稿确认 edition 和 2025-09-23 publication date。
- 使用 Arizona State、University of Florida、University of Arizona、Georgia Tech、Kansas State、Hope College 和 Valdosta State 的官方发布交叉确认本科类别和发布时间。
- 直接 U.S. News ranking pages 被 robots 控制阻断，已记录 `blocked`，未尝试登录、付费墙、CAPTCHA、robots 或其他访问控制绕过。

### 结论与输出

- 最新发现的 Best Colleges edition：`2026 Best Colleges`；版本/发布日期高置信度，作为截至发现日「最新」为中等置信度，后续运行必须重查。
- Family inventory：9 个；National Universities 和 undergraduate academic programs 分别进入 A/B，Global、Graduate、Online 及机构/体验类别明确排除。
- Category inventory：28 个纳入、2 个排除，保存在 `data-pipeline/data/ranking-discovery/2026-best-colleges/`，不写入 `ranking-scope.json`。
- 所有 28 个纳入 category 与 National Universities stream 均为 `needs_manual_seed`，因为尚无完整、合法、稳定的 cutoff record feed。
- 新增 manual seed schema、validation、duplicate/source/cutoff 检查及 staging-only 入口；没有 seed record 或真实学校数据。

### 新增和修改文件

- `data-pipeline/data/ranking-discovery/2026-best-colleges/`：来源、family、category 和 manifest 输出。
- `data-pipeline/schemas/v1/ranking-family-inventory.json`
- `data-pipeline/schemas/v1/ranking-category-inventory.json`
- `data-pipeline/schemas/v1/manual-ranking-seed-batch.json`
- `data-pipeline/src/pathos_data/ranking_discovery.py`
- `data-pipeline/src/pathos_data/__main__.py`
- `data-pipeline/tests/test_ranking_discovery.py` 与 test-only fixtures。
- `data-pipeline/reports/ranking-discovery-report.md`
- `docs/database-data-contract.md`、`docs/database-development-log.md` 与 manual seed README。

### 风险、未解决问题与准入

直接 ranking pages 无法访问导致完整 record coverage 尚未建立。Stage 2B 的 manual-seed collection / 覆盖补齐已具备明确输入；最终 universe generation 仍不准入，直至 National Universities Top 50 与所有纳入 category 的 cutoff records 经来源、去重与 canonical validation 完成。

### 验证结果

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`：19 / 19 通过，包含 Stage 2A 的 schema、duplicate、Global/Graduate exclusion、manual seed、cutoff、source、edition 和 versioning 测试。
- `PYTHONPATH=src python3 -m pathos_data validate-ranking-discovery --family-inventory ... --category-inventory ...`：通过。
- `PYTHONPATH=src python3 -m pathos_data validate --fixture tests/fixtures/test-university-raw.json`：通过。
- `npx tsc --noEmit`：退出码 0；未修改 frontend 文件。
- `git diff --check`：无空白错误。
## 2026-07-15｜Stage 3D-Fill Bulk People v2：Cross-Batch Deduplication

- 目标与范围：修复 Batch A + Batch B 联合 Gate review 发现的跨批人物重复；新增独立 combined validation layer，不删除或回写不可变 Batch A/B artifacts，也不开始剩余学校 intake。Candidate v2、Stage 3/3B/3C/3C2/3D framework 与 frontend 均保持只读；未生成 final universe、正式 memberships 或 frontend export。
- 去重语义：累计 notable attendance 的唯一键固定为 `(candidate_id, canonical_person_id)`。30 条不可变输入中检测到 1 个重复键（University of Michigan / James Earl Jones），combined overlay 输出 29 个唯一人物；原始重复保留在 audit artifact，来源、origin batch 与 evidence provenance 合并保留，`post_merge_duplicate_count=0`。
- Fail-closed validator：加载任意 Batch A/B/未来 C/D 目录，逐批验证 policy/non-final boundary、attendance relationship 与 provenance；对已知 A/B 额外固定 attendance/summary SHA-256。跨批严格字段或非空 degree/major 冲突、批内重复、合并输出残留重复、deterministic drift、policy/ranking contamination 均拒绝通过。
- 测试与验证：新增 7 个回归测试，覆盖 A+B 重复检测、同人不同 source 的 provenance merge、同名不同学校不误合并、相同 person ID 不同 candidate 不误合并、残留重复 fail closed、deterministic/policy boundary 以及 generate/validate CLI。专用 tests 7/7、全量 Python tests 208/208、combined validator、schema/migration、byte-identical regeneration 与 `git diff --check` 均通过；`source_policy_violations=0`、`ranking_field_contamination=0`。
- 状态与下一步：combined layer 保持 `source_limited`、`incomplete`、`not_final`。本次提交后停止并等待下一次 Gate review，不继续 Bulk Completion。

## 2026-07-15｜Stage 3D-Fill Bulk Completion Wave 1：Program-Specific People

- 目标与范围：在固定 Candidate v2 62 校范围内选择 20 校，逐校处理既有 top-5 demo programs，共 100 个 program-person slots。该层是独立 overlay；Candidate v2、Stage 3/3B/3C/3C2/3D framework、Batch A/B、frontend 均保持只读，未生成 final universe、正式 memberships 或 frontend export。
- Reviewed intake：20 个 slots 获得 source-backed `identified_person`；其余 80 个 slots 保持 `source_review_not_completed`，没有把未审查资料写成「无」，`no_qualifying_person_found=0`。正向记录只接受 `direct_program_match` / `direct_related_program_match` 与 `source_stated_exact_program` / `source_stated_related_program`，职业、公司、成就、研究方向和名气均不得用于专业推断。
- Evidence 与 cache：全部 20 个正向记录具有 attendance 与 program-match 双 evidence anchors，使用 20 个学校官方 institutional sources、短逐字 quote、gitignored reviewed-excerpt cache、SHA-256 与 `local_cache_substring_check`；`manual_verbatim_check=0`、`cache_missing=0`。本轮新增 cache 只保存 URL 与短 reviewed quote，不提交网页快照或长文本。
- Manifest pins：新增版本化 `immutable-input-pin-manifest.json`，固定 Candidate v2、Stage 3C demo-program overlay、Batch A/B program-person 与 summary/attendance 输入。旧 combined dedup Python 中的硬编码 batch SHA 已移除，通用校验改为可选 manifest-driven pins；Wave 1 生成器强制使用该 manifest。
- Program-person dedup：累计唯一键固定为 `(candidate_id, canonical_person_id)`。Batch A/B 与 Wave 1 共 25 次 identified occurrence，合并为 20 个唯一 program people；5 个跨批重复键在独立 audit artifact 中披露并保留 origin provenance，合并后重复为 0。同名人物在不同 candidate（例如不同学校上下文）不会被误合并。
- 工程：新增 deterministic generator、fail-closed validator、generate/validate CLI、输入 manifests/observations、独立 artifacts、report 与 11 个 Wave 1 TDD tests；同时保持既有 combined dedup 7 个回归测试通过。validator 覆盖 20 校/100 slots、program provenance、可分别引用逐字原文的 attendance/program 双证据、relationship/match allowlists、cache SHA/substring、identity、ranking isolation、scoped-none gate、manifest drift、跨批去重和 byte-identical regeneration。
- 风险与下一步：覆盖仅限 20 所学校的 top-5 slots，80 个 slots 尚未完成 source review；正向记录也不代表完整杰出人物清单。该层继续标记 `source_limited`、`incomplete`、`not_final`，提交后停止并等待 Gate review，不继续 Wave 2、tag 或 push。

## 2026-07-15｜Stage 3D-Fill Bulk Completion Wave 2：Program-Specific People

- 目标与范围：在 Wave 1 Gate PASS 后复用同一 pipeline，选择另外 20 所未进入 Wave 1 的 Candidate v2 学校，逐校处理既有 top-5 demo programs，共 100 个 slots。Wave 2 是独立 overlay；Wave 1 artifacts、Candidate v2、Stage 3/3B/3C/3C2/3D framework、ranking 与 frontend 均保持只读，未生成 final universe、正式 memberships 或 frontend export。
- Reviewed intake：8 个 slots 获得 `identified_person`，92 个 slots 保持 `source_review_not_completed`，`no_qualifying_person_found=0`。本轮不新增 notable-attendance rows，而是复用并重新核验 8 条就读证据；只有同一官方来源明确陈述学校关系和 degree/program 时才进入正向记录。match 仅使用 `direct_program_match` / `direct_related_program_match` 与 `source_stated_exact_program` / `source_stated_related_program`，没有使用职业、公司、职位、研究方向或名气推断专业。
- Evidence 与 cache：8 条正向记录来自学校官方 institutional/alumni/profile 页面，分别保留 attendance 与 program-match anchors；16 个 anchor 全部通过 gitignored reviewed-excerpt cache、SHA-256 与 `local_cache_substring_check`。`manual_verbatim_check=0`、`cache_missing=0`，cache 正文不进入 commit。
- Immutable pins 与去重：新增 Wave 2 input pin manifest，固定 Candidate v2、Stage 3C demo-program overlay、Wave 1 cumulative program-person output、Wave 1 summary 和 Bulk People v1 attendance evidence。累计输入 28 条 identified occurrence，输出 28 个唯一 `(candidate_id, canonical_person_id)`；Wave 2 新增重复键 0，合并后残留重复 0。
- 工程与验证：新增 Wave 2 generator/validator、generate/validate CLI、输入 manifests/observations、11 个独立 JSON artifacts、report 与 8 个 TDD tests。先观察模块和 CLI 缺失导致 8 个测试红灯，再实现并转绿。专用 tests 8/8、全量 Python tests 227/227、formal Wave 2 validator、fixture/schema/migration validation、byte-identical artifact/report regeneration 与 `git diff --check` 均通过；`source_policy_violations=0`、`ranking_field_contamination=0`。
- 风险与下一步：本轮仅完成 20 校的 slot processing，不代表 20 校全部找到人物，也不代表 program-person dataset 完成。92 个 slots 仍是尚未完成来源审查的透明缺口；后续应先进行独立 Gate review，再决定是否处理剩余 Candidate v2 学校。该层继续标记 `source_limited`、`incomplete`、`not_final`。

## 2026-07-15｜Stage 3D-Fill Bulk Completion Wave 3：Remaining Program-Specific People

- Preflight 与范围：在 clean worktree 和 Wave 2 commit `cd42b2ce9ade7063c4ceb3ec4952cfbaaf65a85c` 上开始。Wave 3 不维护人工学校名单，而是从不可变 Candidate v2、Wave 1 program-person slots 和 Wave 2 program-person slots 自动计算差集；62 - 20 - 20 得到恰好 22 所学校且前两波无交集。若该差集不是 22，generator fail closed。
- Reviewed intake：处理剩余 22 所学校全部既有 top-5 demo programs，共 110 个 slots。10 个 slots 获得 `identified_person`，100 个保持 `source_review_not_completed`，`no_qualifying_person_found=0`，没有把未审查缺口渲染成「无」。正向记录仅接受允许的 attendance relationship、`direct_program_match` / `direct_related_program_match` 和 source-stated exact/related basis；职业、公司、研究方向、名气或普通 alumni 身份均不能推断专业。
- Evidence 与 cache：10 条正向记录来自学校官方 institutional/alumni/profile sources，分别生成 attendance 与 program-match evidence anchors；20 个短 quote anchors 全部通过 gitignored reviewed-excerpt cache、SHA-256 和 `local_cache_substring_check`。`manual_verbatim_check=0`、`cache_missing=0`，cache 仅保存来源 URL 和短 reviewed excerpts，不进入 commit。
- 累计 dashboard 与去重：Wave 1 + Wave 2 + Wave 3 合计覆盖 62 所学校和 310 个 slots；累计状态为 38 identified、272 source review not completed、0 scoped no-qualifying。按 `(candidate_id, canonical_person_id)` 合并 38 次正向 occurrence 后得到 38 个唯一人物，输入重复 0、合并后重复 0；累计 artifact 保留 `origin_waves` / `origin_batches` provenance，不回写 Wave 1 或 Wave 2。
- 工程：新增自动 scope generator、fail-closed validator、generate/validate CLI、versioned immutable input pin manifest、reviewed source/cache manifests、program-person observations、独立 Wave 3 artifacts/report 与 10 个 TDD tests。测试覆盖 dirty/stale preflight、remaining scope、110 slots、双证据、inference/relationship/ranking rejection、manual-only/cache SHA rejection、gap 语义、cross-wave dedup、累计 dashboard、上游不变和 deterministic regeneration。专项 tests 10/10、全量 Python tests 237/237、23 项 Wave 3 validator、fixture/schema/migration validation、artifact/report byte-identical regeneration 与 `git diff --check` 均通过。
- 边界与风险：Wave 2 尚未完成独立 Claude Gate，Wave 3 也尚未 Gate；本记录不声明任一波 PASS。Candidate v2、Stage 3/3B/3C/3C2/3D framework、Wave 1/2、ranking 和 frontend 均只读；未生成 final universe、正式 memberships 或 frontend export。尽管 slots 已全部 processed，272 个 slots 仍未完成 reviewed-source intake，因此状态继续为 `source_limited / incomplete / not_final`。下一步应等待 Wave 2 + Wave 3 Gate review，不得提前 tag、push 或进入 final export。

## 2026-07-16｜Stage 3D-Fill Program People Coverage Expansion Wave 4

- Preflight 与范围：在 clean worktree、Wave 3 commit `ddcfcedd753cb85f3b1aa95ed356a7eed268d0ce` 上开始；没有未提交 Claude/Gate helper。Wave 4 从不可变 Candidate v2、Stage 3C demo-program overlay 与 Wave 1/2/3 slot artifacts 自动推导 272 个 `source_review_not_completed` slots，按已声明的 A/B/C program-family priority、candidate ID 与 slot number 稳定排序，尝试前 100 个高价值 slots；没有手写完整 slot 名单或扩大 62 校范围。
- Reviewed intake：100 个 attempted slots 中，14 个获得 `identified_person`，86 个继续保持 `source_review_not_completed`，`no_qualifying_person_found=0`，没有把未完成审查写成「无」。正向记录只接受允许的 attendance relationship、`direct_program_match` / `direct_related_program_match` 与 `source_stated_exact_program` / `source_stated_related_program`；职业、公司、职位、研究方向、名气或普通 alumni 身份均不得推断专业。
- Evidence 与 cache：14 条正向记录来自学校官方 institutional/alumni/department/profile pages，具有 attendance 与 program-match 双 anchors；28 个短 direct-quote anchors 全部通过 gitignored reviewed-excerpt cache、SHA-256 与 `local_cache_substring_check`。`manual_verbatim_check=0`、`cache_missing=0`，cache 正文未进入 commit。
- 累计覆盖与去重：Wave 1+2+3+4 仍处理固定 310 slots；累计 identified 从 38 增至 52，`source_review_not_completed` 从 272 降至 258，scoped `no_qualifying_person_found` 仍为 0。按 `(candidate_id, canonical_person_id)` 合并 52 个正向 occurrence，得到 52 个 unique program people，输入重复与合并后残留重复均为 0；保留 origin-wave provenance，不回写 Wave 1/2/3。
- 工程与 validator：新增独立 Wave 4 generator、fail-closed validator、generate/validate CLI、immutable pin manifest、reviewed source/cache manifests、observations、9 个 artifacts、report 与 10 个 TDD tests。validator 检查 pending-slot derivation、priority selection、dual evidence、source-stated match、relationship/identity policy、cache substring/SHA、gap semantics、cumulative dedup/dashboard、ranking isolation、upstream immutability 与 deterministic regeneration。
- 边界与风险：Candidate v2、ranking、Stage 3/3B/3C/3C2/3D framework、history/anecdote/attendance、Wave 1/2/3 与 frontend 均保持只读；未生成 final universe、formal memberships、frontend/preview export 或 Stage 4A overlay。258 个 program-person slots 仍为透明来源缺口，本层继续标记 `source_limited / incomplete / not_final`；提交后停止并等待独立 Gate review，不 tag、不 push。

## 2026-07-16｜Stage 3D-Fill Program People Coverage Expansion Wave 5

- Preflight 与范围：在 clean worktree 和 Wave 4 checkpoint `daa926010e83183f40782e38471a2f38439f8c00` 上开始，未发现未提交 audit/helper 文件，也未恢复 Stage 3A stash。Wave 5 从 immutable Wave 1–4 inputs 自动重建 310-slot 当前状态，确认 52 identified / 258 `source_review_not_completed`，再以 school-spread round robin 和 Tier 1/2/3 program priorities 选择 100 个 remaining slots；覆盖全部 62 校，每校最多 2 个尝试槽位，99 个属于 Tier 1、1 个属于 Tier 2。
- Reviewed intake：100 个 attempted slots 中，10 个转为 `identified_person`，90 个继续保持 `source_review_not_completed`，`no_qualifying_person_found=0`。新增 positive 覆盖 Brown CS、BU CS、CMU EE、Cornell CS、Dartmouth Economics、Georgia Tech BME、Johns Hopkins Molecular Microbiology/Immunology、MIT EECS、Purdue CS 与 Rice Biochemistry/Biosciences；每条均由学校官方 department/alumni/profile 页面直接陈述 attendance 与 exact/related program relationship，没有使用职业、公司、名气或研究方向推断专业。
- Evidence、cache 与 identity：10 条 positive records 的 20 个 attendance/program anchors 均为短 direct quotes，写入 gitignored reviewed-excerpt cache，并通过 SHA-256 与 `local_cache_substring_check`；`manual_verbatim_check=0`、`cache_missing=0`。人物 ID 使用 normalized name、candidate context 与 source-backed disambiguator；按 `(candidate_id, canonical_person_id)` 合并累计 62 次 occurrence，unique people 为 62，输入重复与 post-merge duplicate 均为 0。
- 累计覆盖：Wave 1+2+3+4+5 的 program-person identified 从 52 增至 62 / 310，透明来源缺口从 258 降至 248，scoped `no_qualifying_person_found` 仍为 0。所有 310 slots 继续由累计 dashboard 逐项核算；attempted 不等于 identified，未审查也不渲染成「无」。
- 工程与验证：新增独立 Wave 5 generator、fail-closed validator、generate/validate CLI、immutable input pins、reviewed source/cache/observation inputs、9 个 artifacts、report 与 7 个 TDD tests。先确认模块/CLI/input 缺失产生预期红灯，再实现并转绿。Wave 5 tests 7/7、全量 Python tests 254/254、formal validator、fixture/schema/migration validation、artifact/report byte-identical regeneration 与 `git diff --check` 均通过；`source_policy_violations=0`、`ranking_field_contamination=0`。
- 边界与风险：Candidate v2、ranking、Stage 3/3B/3C/3C2/3D framework、history/anecdote/attendance、Wave 1/2/3/4 与 frontend 均保持只读；未生成 final universe、formal memberships 或 frontend export。248 个 slots 仍是来源审查缺口，因此本层继续为 `source_limited / incomplete / not_final`；提交后停止并等待 Gate review，不 tag、不 push。
