# Stage 3C Academic + Geo Enrichment 设计规格

**状态：** 设计规格，尚未实施。
**基线：** `78097a86caa74c720e5c3475800c3c147f1f4fa4`（`pathos-stage3b-demo-gap-fill-pass`）。
**输入定位：** Candidate v2、Stage 3 MVP Detail Pack、Stage 3B Demo-Critical Gap Fill 均为只读输入。
**输出定位：** Stage 3C 是 source-limited、not-final 的 Academic + Geo enrichment overlay，不是 final database、final university universe、正式 selection memberships 或 frontend export。

---

## 1. Purpose / Goal

Stage 3C 在不扩大 Candidate v2 的 62 所大学范围、也不回写 Stage 3 或 Stage 3B 的前提下，提升 demo 所需的学术、收费与地理字段质量：

1. 用学校官方本科 majors / programs / areas-of-study / catalog 页面补强专业来源；
2. 仅用官方本科收费页面补强 college-level surcharge、program-level extra fee 与可比较的 tuition 差异；
3. 在证据足够时计算 demo programs 的最高与最低本科收费；
4. 为全部学校提供一致的美国区域分类；
5. 为全部可定位学校提供最近三个城镇及可复核的直线距离；
6. 尝试仅用 UNC Chapel Hill 官方本科页面补足其剩余两个 demo programs。

该阶段的目标是提高 demo 的解释性与来源透明度，而不是将零散 detail evidence 表述为完整学校数据库。

## 2. Current Baseline

- Candidate v2 固定为 62 所 source-limited candidate universities 与 67 个 atomic memberships。
- Stage 3 与 Stage 3B 均不属于 final universe 或 final database，且没有产生正式 memberships 或 frontend export。
- Stage 3B 已为 62/62 学校写入 overlay，并为 62/62 学校提供 College Scorecard/IPEDS provenance-backed student-faculty ratio。
- Stage 3B 已通过显式 alias mapping + exact IPEDS `INSTNM` 解析 11 个 identity/tuition/majors gaps；没有 fuzzy UNITID。
- Stage 3B 已补足 8 个实际 demo-program gaps 中的 7 个。UNC Chapel Hill 仍只有 3 个可证实的 demo programs，gap reason 为 `fewer_than_five_official_undergraduate_demo_programs_available_after_stage3b`。
- 6 条遗留 `top_5_gap_reason` 已仅在 Stage 3B overlay 中清除；Stage 3 原始 artifact 未被修改。
- Stage 3B demo readiness 为 `0.996`，但这不是 final-data readiness。
- `source_policy_violations = 0` 与 `ranking_field_contamination = 0` 必须持续成立。

## 3. In Scope

1. **Official academic source uplift**：为 62 所学校建立官方本科 majors/programs source status，必要时结构化提取官方 major 条目。
2. **Demo-program overlay**：仅将官方本科页面直接支持的 UNC 项目补入 demo program overlay；既有 U.S. News rank fields 保持不变。
3. **Undergraduate tuition deepening**：记录官方 undergraduate university-level tuition 的确认状态，以及明确适用的 college/program surcharge、differential tuition 或 required program fee。
4. **Highest/lowest tuition logic**：只依据可比较的本科 college/program-level required fee 或已知统一 university-level tuition 计算。
5. **Region**：为 62 所固定 candidate university 写入统一、稳定、可验证的 region。
6. **Nearest towns**：使用受控地理源生成最多三个城镇及 Haversine straight-line distance。
7. **Provenance、gap disclosure、determinism、validation、tests、development log**。

## 4. Out of Scope

- 杰出学生、名人校友及其专业、学校历史、佚事或 interesting facts；这些全部移交 Stage 3D People + Narrative Enrichment。
- 新学校、Candidate v2 范围扩张、UNITID fuzzy matching、重新采集 U.S. News ranking。
- final university universe、正式 selection memberships、正式 frontend export、前端代码或地图组件修改。
- 恢复或修改 Stage 3A stash。
- 提交完整网页、网页镜像或大段网页正文；只提交结构化 observation、source manifest、短 evidence anchor 与披露。
- 用非官方网页、搜索摘要、AI 记忆、room and board、COA 或 graduate/professional tuition 填充本科 detail 字段。

## 5. Data Sources and Source Policy

### 5.1 Academic / tuition source priority

| Field family | Permitted priority | Required restriction |
| --- | --- | --- |
| Official undergraduate majors | official university majors/programs page → undergraduate catalog → official areas-of-study page | 每个 source 必须明确支持本科范围；IPEDS completion award areas 只能作 federal fallback。 |
| Demo programs | existing verified U.S. News program record → official undergraduate program page | 官方 major 只能是 demo program，不能写入或覆盖 U.S. News category/rank。 |
| Undergraduate tuition / fees | official bursar / student accounts / tuition page → official college/program fee page → official Common Data Set → IPEDS | 必须排除 graduate, MBA, law, medical, professional tuition 与 COA components。 |
| Region | controlled state-to-region mapping embedded in Stage 3C source-controlled data | 不能混用多个 region taxonomy。 |
| Town coordinate / identity | U.S. Census Gazetteer Places → U.S. Census incorporated places reference → GeoNames fallback | GeoNames fallback 必须记录 dataset version、license/attribution note；不得默认使用无明确许可的商业汇编。 |

### 5.2 Ranking isolation

- `validate_source_policy_use()` 必须在 Stage 3C generator 的每个 detail-source ingestion path 调用。
- CollegeData（如未来使用）只允许进入 `detail` domain，且必须有 field-level provenance；本设计不依赖它。
- THE、QS、xuanxiao.org 及任何非 U.S. News ranking source 不得写入 `usnews_ranking` domain，也不得覆盖 `usnews_category`、`usnews_rank`、National 或 undergraduate program ranking fields。
- 学校官方本科 program page 只能写入 `official_*` detail fields 或 `source_basis=official_school_program_page`；它不是 U.S. News rank evidence。
- 每次生成的 summary 与 validator result 都必须报告 `source_policy_violations = 0` 和 `ranking_field_contamination = 0`。

### 5.3 Source retention

- Git 只保留 source manifest、结构化 observation、访问日期、URL/reference、短摘录与 extraction notes。
- 任何下载的 Gazetteer、GeoNames 或官方 PDF/CSV 缓存放在 gitignored `data-pipeline/cache/stage3c-*` 下；cache 不进入 commit。
- 不保存完整 HTML 页面、网页截图或大段版权内容。

## 6. Artifact Plan

Stage 3C future implementation 必须只写入以下独立目录，不覆盖任何 Stage 3/3B path：

`data-pipeline/artifacts/stage3c-academic-geo-enrichment/`

| Artifact | Purpose |
| --- | --- |
| `stage3c-universities.json` | 62 条派生 university overlay；region、nearest_towns、输入引用与 overlay notes。 |
| `stage3c-official-major-sources.json` | 每校官方本科专业来源状态、source manifest reference、limitation。 |
| `stage3c-official-majors.json` | 仅由学校官方本科来源结构化提取的 majors/programs；没有官方 source 时不伪造条目。 |
| `stage3c-demo-programs-overlay.json` | 从 Stage 3B 继承 demo programs，并仅追加有官方本科证据的 UNC program。 |
| `stage3c-tuition-deepening.json` | 每校官方 tuition/fee deepening status 和明确的 fee observations。 |
| `stage3c-highest-lowest-tuition.json` | 每校最高/最低 tuition calculation、basis、source references 或 null reason。 |
| `stage3c-gap-disclosure.json` | source limitations、unresolved official sources、town/tuition gaps。 |
| `stage3c-summary.json` | 可审计统计、readiness before/after、policy counters、remaining gaps。 |
| `stage3c-validation-result.json` | full-artifact validator 的真实结果。 |

Supporting version-controlled inputs may live under `data-pipeline/data/stage3c/`:

- `official-major-observations.json`
- `official-tuition-fee-observations.json`
- `region-classification.json`
- `town-source-manifest.json`

报告路径：`data-pipeline/reports/stage3c-academic-geo-enrichment-report.md`。开发日志仍为 `docs/database-development-log.md`。

## 7. Source Manifest Schema

每个 Stage 3C source manifest row 必须包含：

```json
{
  "source_id": "source_unique_stable_id",
  "candidate_id": "candidate-v2:example",
  "source_type": "official_institutional | census_gazetteer | geonames_fallback | ipeds_federal",
  "field_domain": "official_majors | tuition_detail | geography",
  "source_title": "Human-readable source title",
  "source_url_or_reference": "https://... or local controlled dataset reference",
  "publisher": "Institution or government publisher",
  "accessed_date": "YYYY-MM-DD",
  "license_or_use_note": "Required for non-government reusable datasets",
  "official_institutional": true,
  "field_level_provenance_required": true,
  "limitation_note": "Short, factual limitation or null"
}
```

`source_id` 必须唯一、可被所有 observation/evidence anchor 解析。`official_institutional=true` 只能用于学校或学院直接发布的页面、catalog 或 PDF。Census/IPEDS 记录不得误标为学校官方来源。

## 8. Official Majors / Programs Schema

### 8.1 Per-university source status

```json
{
  "candidate_id": "candidate-v2:example",
  "canonical_id": "institution:example",
  "display_name": "Example University",
  "official_major_source_status": "official_full_undergraduate_major_list_found",
  "official_major_source_url": "https://...",
  "official_major_source_title": "Undergraduate Majors",
  "source_id": "source_example_undergraduate_majors",
  "evidence_anchor": {"source_id": "source_example_undergraduate_majors", "evidence_type": "direct_quote", "quote": "Undergraduate majors"},
  "extraction_notes": "Structured major names only; no course catalog copied.",
  "confidence": "high",
  "null_reason": null
}
```

Allowed `official_major_source_status` values:

- `official_full_undergraduate_major_list_found`
- `official_undergraduate_programs_found`
- `official_areas_of_study_found`
- `official_catalog_found`
- `only_ipeds_award_areas_available`
- `not_found`

`only_ipeds_award_areas_available` must say that it is a federal reported bachelor-degree award-area fallback, not a current official catalog assertion. `not_found` requires a non-empty `null_reason`.

Official coverage is intentionally best-effort, not a 62-school completion gate: a school with no accessible official undergraduate list remains valid with `only_ipeds_award_areas_available` (when Stage 3B has that federal fallback) or `not_found`. Such a school must carry a source limitation, but it does not block Stage 3C or cause an inferred major list to be written.

### 8.2 Official major row

```json
{
  "candidate_id": "candidate-v2:example",
  "major_name": "Computer Science",
  "normalized_major_name": "Computer Science",
  "degree_type": "BS",
  "college_or_school": "College of ...",
  "list_type": "official_undergraduate_majors",
  "source_id": "source_example_undergraduate_majors",
  "evidence_anchor": {"source_id": "source_example_undergraduate_majors", "evidence_type": "direct_quote", "quote": "Computer Science, B.S."},
  "undergraduate_status": "undergraduate",
  "confidence": "high",
  "null_reason": null
}
```

Allowed `list_type` values are `official_undergraduate_majors`, `official_undergraduate_programs`, `official_areas_of_study`, and `official_catalog_programs`. `ipeds_award_areas_only` is a source status, not an official-major `list_type`.

Graduate-only, MBA, law, medical, professional-only, certificate-only and course-only observations are rejected unless an official source explicitly identifies an undergraduate degree program. No inference from a department name is allowed.

## 9. Demo Top Programs Overlay Rules

1. Stage 3B `top_5_programs_for_demo` is copied into the Stage 3C overlay; Stage 3/3B are never written.
2. Existing `source_basis=usnews_program_ranking` and their rank/category fields are immutable in meaning and value.
3. A program sourced from an official academic page uses `source_basis=official_school_program_page` (or `official_major_list`), `confidence=medium`, and `usnews_category=null`, `usnews_rank=null`.
4. The UI-facing wording must distinguish “排名专业” (verified U.S. News record) from “重点专业 / demo program” (official academic page).
5. UNC Chapel Hill may receive exactly the number of new records necessary to reach five. Each added record requires `official_institutional`, `undergraduate_status=undergraduate`, URL/reference, source ID, and short direct-quote anchor.
6. If two qualifying official UNC entries cannot be found, the overlay keeps fewer than five and retains a precise gap reason. No program is added from memory, reputation, a graduate catalog, or a third-party list.

## 10. Tuition Deepening Schema

Every university receives one deepening status row even when no differentiated fee is found:

```json
{
  "candidate_id": "candidate-v2:example",
  "canonical_id": "institution:example",
  "display_name": "Example University",
  "academic_year": "2025-26",
  "tuition_deepening_status": "university_level_only_confirmed",
  "official_tuition_source_url": "https://...",
  "official_bursar_source_url": "https://...",
  "official_program_fee_source_url": null,
  "source_id": "source_example_bursar_2025_26",
  "evidence_anchor": {"source_id": "source_example_bursar_2025_26", "evidence_type": "direct_quote", "quote": "Undergraduate tuition"},
  "extraction_notes": "Only university-wide undergraduate tuition is published.",
  "confidence": "high",
  "null_reason": null,
  "fee_observations": []
}
```

Allowed `tuition_deepening_status` values:

- `university_level_only_confirmed`
- `college_level_surcharge_found`
- `program_level_extra_fee_found`
- `mixed_base_plus_surcharge_found`
- `official_page_found_no_program_difference`
- `not_found`
- `insufficient_data`

Finding differentiated tuition is **not** a Stage 3C success requirement. A direct official confirmation that undergraduate tuition is university-wide is a successful `university_level_only_confirmed` outcome. When an official page has no published program difference, use `official_page_found_no_program_difference`; when no reliable conclusion can be drawn, use `insufficient_data` or `not_found`. No program difference may be inferred merely to enable a highest/lowest calculation.

Fee observations must use this contract:

```json
{
  "fee_name": "Engineering differential tuition",
  "applies_to_college_or_school": "College of Engineering",
  "applies_to_program": null,
  "undergraduate_only": true,
  "fee_type": "college_surcharge",
  "amount": 0.0,
  "currency": "USD",
  "academic_year": "2025-26",
  "residency_scope": "in_state | out_of_state | private_single_rate | all_undergraduate",
  "required_for_program": true,
  "calculation_notes": "Added to the published undergraduate base tuition only when applicable.",
  "source_id": "source_example_bursar_2025_26",
  "evidence_anchor": {"source_id": "source_example_bursar_2025_26", "evidence_type": "direct_quote", "quote": "..."}
}
```

Only a fee explicitly required for an undergraduate college or named undergraduate program may be used in program tuition display/calculation. A course/lab fee is retained, if useful, only as a non-comparable observation when the source does not establish it as required for the entire program.

## 11. Highest / Lowest Tuition Calculation Rules

1. Candidate calculations start from the Stage 3B validated university-level undergraduate tuition/required-fees display, not from COA.
2. A `program_level_only` basis is allowed only if two or more comparable, required undergraduate program-level totals exist.
3. A `college_level_or_program_level` basis is allowed only if at least two comparable required totals differ after applying explicit college/program fee observations.
4. If every demo program legitimately inherits the same university-level undergraduate tuition, highest and lowest may both name a demo program and use `university_level_same_for_all`. Notes must say there is no published comparable program-specific difference.
5. If fee applicability, residency treatment, academic year, or required status cannot be aligned, output `highest_tuition_program=null`, `lowest_tuition_program=null`, `highest_lowest_basis=insufficient_comparable_data`, and a concrete null reason.
6. `not_published` is used when no eligible undergraduate tuition base exists.
7. Calculations must persist selected residency/default basis, component amounts, source IDs, and a short calculation formula. For public institutions, retain both in-state and out-of-state data; a demo may use out-of-state only when notes explicitly state that choice.
8. Graduate, MBA, law, medical, professional tuition; room/board; books; transport; personal expenses; and estimated cost of attendance are forbidden inputs. A validator must fail closed if source text/metadata indicates such content.

## 12. Region Schema and Classification Rules

Stage 3C fixes `region` to **one taxonomy only**: the four U.S. Census regions `Northeast`, `Midwest`, `South`, and `West`. It will not mix Census divisions, subregions, or ad-hoc labels such as “Southwest” with this field. A future stage may add a separate `subregion` field, with its own taxonomy and validator, but Stage 3C will not create or populate it.

The version-controlled `region-classification.json` maps every U.S. state and District of Columbia to one Census region. The generator derives region solely from the school state after validating that state code appears in the controlled mapping.

```json
{
  "candidate_id": "candidate-v2:example",
  "state": "NC",
  "region": "South",
  "region_taxonomy": "us_census_four_regions",
  "source_id": "source_stage3c_us_census_region_mapping",
  "evidence_anchor": {"source_id": "source_stage3c_us_census_region_mapping", "evidence_type": "controlled_mapping", "quote": "NC -> South"},
  "null_reason": null
}
```

All 62 current candidates are U.S. institutions. An unknown/non-U.S. state code fails validation rather than being inferred.

## 13. Nearest Towns Schema

Each Stage 3C university overlay has `nearest_towns`, an ordered list of up to three distinct qualifying town/place rows:

```json
{
  "town_name": "Chapel Hill",
  "state": "NC",
  "place_type": "incorporated_place | census_designated_place | municipality | city | town",
  "population_class": "place_population_10000_to_49999",
  "distance_miles": 0.0,
  "distance_km": 0.0,
  "distance_method": "haversine_straight_line",
  "town_latitude": 35.9132,
  "town_longitude": -79.0558,
  "calculation_source": "campus coordinate + Census Gazetteer place coordinate",
  "source_id": "source_census_gazetteer_places_YYYY",
  "notes": "campus_city_included=true; school_latitude=35.9132; school_longitude=-79.0558"
}
```

Rules:

- A qualifying place candidate may be a city, town, municipality, incorporated place, or Census-designated place. It must record `place_type` from the source taxonomy or a documented controlled mapping.
- Counties are never town candidates. Campuses, neighborhoods, unincorporated labels, postal labels, and similar local names are excluded unless the selected source explicitly classifies the same entity as a Census place or municipality.
- Towns are sorted by ascending unrounded distance; output stores distance rounded only after sorting.
- A school’s campus city may appear and must say `campus_city_included=true`; it is not suppressed merely because distance is zero.
- `population_class` is derived only from the same controlled source’s population when available. If no population is published, it is `unknown` with a note; it is never inferred from city reputation.
- Duplicate town/state pairs and a town with missing coordinates are rejected.
- If a university lacks validated campus coordinates, its list is empty and gap disclosure records `campus_coordinate_unavailable_for_nearest_towns`.
- The interface must label this distance as straight-line; it must never call it driving distance or travel time.

## 14. Distance Calculation Rules

Stage 3C uses the deterministic Haversine great-circle formula with Earth radius `6371.0088 km`:

```text
a = sin²((lat2-lat1)/2) + cos(lat1) * cos(lat2) * sin²((lon2-lon1)/2)
distance_km = 2 * 6371.0088 * asin(sqrt(a))
distance_miles = distance_km * 0.621371
```

- Inputs are decimal-degree campus latitude/longitude from the validated Stage 3B overlay and town coordinates from the controlled town source.
- Each nearest-town calculation records `school_latitude`, `school_longitude`, `town_latitude`, `town_longitude`, and a `calculation_notes` value that explicitly says `Haversine straight-line distance; not driving distance`.
- Store `distance_km` and `distance_miles` rounded to two decimal places, while selection/sorting uses the unrounded value.
- `distance_method` is always exactly `haversine_straight_line`. Stage 3C does not call driving-distance APIs and does not calculate routing, drive-time, road distance, or estimated travel duration.
- Source manifests must distinguish the campus coordinate source from the town coordinate source, even when both are federal.

## 15. Gap Disclosure Rules

Gap disclosure is mandatory at university and aggregate levels. It must record at least:

- official major source status and why only IPEDS award areas/not found remains;
- UNC demo-program status and any remaining official-source gap;
- tuition deepening status, excluded tuition categories, and why no comparable fee difference exists;
- region mapping status;
- nearest-town coordinate/source availability and whether fewer than three towns were returned;
- source policy and ranking-contamination counters;
- the statement that Stage 3C is source-limited, incomplete, not final, not a final universe, has no official memberships, and has no frontend export.

No null may be silently converted into zero, “same tuition,” or “no programs.”

## 16. Validator Rules

The formal Stage 3C validator must fail closed unless all of the following hold:

1. candidate scope is exactly the Candidate v2 62 IDs; no added or missing university;
2. Stage 3 and Stage 3B input file hashes match the baseline hashes recorded during generation;
3. no file under Stage 3 or Stage 3B artifact directories is written by the generator;
4. all Stage 3C artifacts and source manifests are present, parseable, and source IDs resolve;
5. official major rows have `undergraduate_status=undergraduate`, an official source, and a short anchor;
6. IPEDS award areas are never labelled as official catalogs;
7. UNC additions are exactly official, undergraduate, non-ranking demo observations; if fewer than five remain, a non-empty gap reason exists;
8. all tuition fee observations are undergraduate-applicable and exclude forbidden graduate/professional/COA/room-board/books/transport/personal categories;
9. course/lab fees cannot participate in highest/lowest calculations unless `required_for_program=true` with direct source evidence;
10. highest/lowest outputs use only comparable published undergraduate components or correctly declare uniform/insufficient/not-published basis;
11. every region comes from the single controlled Census-four-region mapping;
12. every nearest-town row has valid coordinates, a resolvable town source, Haversine method, ordered unique towns, and matching miles/km formula within rounding tolerance;
13. `source_policy_violations == 0` and `ranking_field_contamination == 0`;
14. deterministic regeneration is byte-identical to supplied JSON artifacts;
15. all final-universe, official-membership, and frontend-export flags remain false; and
16. no frontend path appears in the staged diff, and gitignored cache input is not staged.

## 17. Test Plan

The implementation plan must create red-green tests before generator code. Minimum tests:

1. 62 candidate IDs are preserved and Stage 3/3B input bytes remain unchanged;
2. an official major source can add undergraduate majors while an IPEDS fallback remains explicitly non-official;
3. a graduate/MBA/law/medical/professional major observation is rejected;
4. UNC reaches five only when two direct official undergraduate observations are provided; otherwise its gap remains;
5. official academic observations cannot populate `usnews_category` or `usnews_rank`;
6. college/program fee source lacking undergraduate/required applicability is excluded from calculations;
7. prohibited tuition text/metadata causes validation failure;
8. uniform university-level tuition produces `university_level_same_for_all` rather than fabricated program differences;
9. comparable required college/program fees produce correct highest/lowest values and source trace;
10. region mapping rejects a state absent from the controlled Census-four-region map;
11. Haversine output is deterministic, ordered, and labelled straight-line;
12. missing campus coordinates yields a disclosed nearest-town gap rather than fabricated towns;
13. source-policy guard is invoked in official-major, tuition, and geography ingestion paths;
14. a staged cache path, frontend file, final-universe file, or official-membership output causes failure; and
15. deterministic regeneration reproduces every Stage 3C artifact byte-for-byte.

Full verification later includes all Python tests, formal Stage 3C validator, existing Stage 3/3B validators, Candidate v2/corpus/ranking validations, fixture/schema/migration validation, and `git diff --check`.

## 18. Determinism and Artifact Integrity

- All JSON writes use stable row ordering, stable key ordering, UTF-8, fixed indentation, terminal newline, and fixed rounding rules.
- Input artifacts are read-only. The generator records SHA-256 for each Stage 3 and Stage 3B input file in its summary; validator recomputes and compares those hashes.
- Web/source access is a controlled ingestion step that produces reviewed structured observations. Regeneration uses only committed observations/manifests plus approved gitignored source caches, not a live webpage response.
- Observation files must include access date and direct short anchor, preventing a dynamic page from changing generated output silently.
- Validation result must be generated by the validator command, never hand-authored as `passed`.

## 19. Non-Mutation Checks for Stage 3 / Stage 3B

Implementation must enforce all of the following before a Stage 3C commit:

1. snapshot SHA-256 hashes for all Stage 3 and Stage 3B input JSON files before generation;
2. run generator only with a Stage 3C output directory;
3. recompute hashes after generation and fail if any input differs;
4. inspect `git diff --name-only` and reject paths under Stage 3/Stage 3B artifact directories;
5. reject any `frontend/` diff; and
6. verify Stage 3A stash remains listed but is not restored, staged, or modified.

## 20. Requirement Coverage Matrix

| Product requirement | Current status | Stage / artifact owner | Rule for future presentation |
| --- | --- | --- | --- |
| U.S. News 综合排名 | Candidate v2 / National corpus accepted but source-limited | Completed prior ranking stages; immutable in Stage 3C | Do not overwrite with detail sources. |
| 本校排名前五的专业 | Stage 3B has 7 resolved historic gaps; UNC has 3 official demo programs | Stage 3C demo-program overlay | Only verified U.S. News entries are “排名专业”; official major supplements are demo programs. |
| 最高学费及其专业 | Mostly uniform university-level basis; no general differentiated computation | Stage 3C highest/lowest artifact | Calculate only from comparable official undergraduate components. |
| 最低学费及其专业 | Same limitation as highest | Stage 3C highest/lowest artifact | Uniform base may yield equal values with explicit basis. |
| 排名前五专业的学费 | Stage 3/3B university-level tuition and fees present where available | Stage 3C tuition deepening artifact | Never call university-wide tuition program-specific without disclosure. |
| 大学师生比 | 62/62 official federal ratio provenance resolved | Stage 3B immutable overlay | Stage 3C may reference, not reclassify it as school facts-page data. |
| 该大学所有涵盖的专业 | Many rows remain IPEDS award-area fallback | Stage 3C official major source/major artifacts | Label official list type honestly; IPEDS is not a catalog. |
| 所在地区 | Existing labels are not a single controlled taxonomy | Stage 3C universities overlay | Use only Census four-region classification. |
| 大学到附近最近 3 个城镇的距离 | Not yet generated | Stage 3C universities overlay | Haversine straight-line only; include town name and distance/source. |
| 杰出的学生，前五专业各一个，没有就写“无” | Not collected | Stage 3D People + Narrative | Official people/achievement evidence or explicit “无”; no Stage 3C work. |
| 名人是否就读这所大学及其专业 | Not collected | Stage 3D People + Narrative | Require authoritative biographical/alumni provenance. |
| 历史与佚事 | Not collected | Stage 3D People + Narrative | Require archives/official history or high-quality attributable source. |

## 21. Handoff to Stage 3D

Stage 3C will hand Stage 3D a fixed 62-university academic/geo overlay with source manifests, official-source statuses, tuition calculation basis, and geography provenance. Stage 3D may reference canonical IDs and display names but must not alter any Stage 3C academic, tuition, ranking, region, or town facts without a separate correction overlay.

Stage 3D inputs should be limited to official archives, official bios, official alumni/award pages, reputable institutional sources, and short evidence anchors. It owns people/narrative fields only: standout-student-per-demo-program status, notable alumni attendance/major, institutional history, and interesting facts. It must preserve `source_limited=true`, `incomplete=true`, and `not_final=true` until a later Gate accepts the combined detail corpus.

## 22. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Official pages are dynamic, blocked, or do not distinguish undergraduate scope | Retain only reviewed structured observations with short anchor; use status/gap rather than inference. |
| Catalog pages mix graduate and undergraduate content | Require explicit undergraduate status plus prohibited-term guard and direct anchor. |
| “Program fee” is actually a course/lab charge | Keep as non-comparable observation unless source proves program-wide required applicability. |
| Different academic years/residencies make amounts incomparable | Preserve academic year/residency; calculate only when aligned, else disclose insufficient data. |
| Region labels drift or mix taxonomies | Use one version-controlled Census four-region mapping. |
| Nearest-place sources have different place definitions/coordinates | Prefer Census Gazetteer; version source and label straight-line Haversine method. |
| Geographic source licensing is unclear | Use government public data first; GeoNames only with explicit attribution/version/permission note. |
| Detail sources contaminate rankings | Enforce `validate_source_policy_use()` and null U.S. News fields on official-major detail observations. |
| Large data/cache changes bloat repository | Commit only structured observations/manifests/artifacts; ignore downloads and page snapshots. |
| Frontend integration prematurely treats overlay as final | Retain explicit not-final flags and defer all export work to Stage 4. |

## 23. Acceptance Criteria

Stage 3C can be presented for independent review only when:

1. all artifacts listed in Section 6 exist in the Stage 3C output directory and cover exactly 62 Candidate v2 IDs;
2. Stage 3 and Stage 3B files are byte-identical before/after generation;
3. UNC either has five properly sourced demo programs or retains an explicit unresolved official-source gap;
4. every official-major source status is honest; IPEDS award areas are never represented as official catalogs;
5. all tuition deepening data is undergraduate-only, excludes forbidden costs, and has source/anchor/year/applicability;
6. highest/lowest results have an approved comparable basis or an explicit null/uniform basis;
7. all regions follow exactly the Census four-region mapping;
8. every nearest-town distance is a sourced Haversine straight-line distance or has a disclosed coordinate/source gap;
9. source-policy violations and ranking-field contamination both equal zero;
10. generator and validator are deterministic; test suite and full validation pass; gitignored cache is absent from staged content;
11. no frontend file, final universe, official selection membership, or frontend export is generated; and
12. the report and development log explicitly state that Stage 3C is source-limited and not a final database.

---

## Design Self-Check

- No implementation code, data observation, artifact, cache, ranking record, or frontend file is created by this specification.
- The single region taxonomy, town distance method, source priority, fee comparability rules, and Stage 3D handoff are explicit.
- Every requested product requirement appears in the coverage matrix with an owning stage and presentation boundary.
- Stage 3/3B immutability and Stage 3A stash non-restoration are explicit acceptance conditions.
