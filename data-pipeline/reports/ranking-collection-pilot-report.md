# PathOS Stage 2B1｜Controlled Ranking Record Collection Pilot

执行日期：2026-07-11（验证结果以 UTC 时间戳保存）
范围：仅 3 条代表性 stream；不是 university universe，也不构成任何 cutoff 的完整覆盖。

## Stream 选择

1. **National Universities**（`national-universities-pilot`，cutoff `numeric_rank <= 50`）：这是 A 集合的必经主流，用于验证官方排名发布来源与数字排名记录。
2. **Undergraduate Business Programs**（`undergraduate-business-programs-pilot`，cutoff `numeric_rank <= 20`）：这是 Stage 2A 已纳入的宽本科类别；多个学校官方页面提供公开交叉证据，并保留一个 #6 tie。
3. **Aerospace Engineering**（`engineering-aerospace-pilot`，cutoff `numeric_rank <= 20`）：这是细分 specialty，用于验证类别 identity，以及“被排名的学院/学校名称”不能被误写为 canonical program。

没有开始其余 26 条已纳入 stream。

## 来源与记录状态

| Stream | 来源形态 | source count | discovered | verified | partially verified | unresolved | ties | identity resolved / unresolved |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| National Universities | U.S. News 官方新闻稿的公开 PR Newswire 发布 | 1 | 3 | 3 | 0 | 0 | 0 | 3 / 0 |
| Undergraduate Business Programs | Carnegie Mellon、Ohio State、Georgia Tech 公开官方页面；Tepper、Cornell 候选 | 4 | 4 | 2 | 2 | 0 | 1 | 4 / 0 |
| Aerospace Engineering | Georgia Tech Aerospace 公开官方页面 | 1 | 1 | 1 | 0 | 0 | 0 | 1 / 0 |

- seed 中共有 **6 条 verified** records，均保留 source display name、numeric rank、displayed rank、`tied`、来源 URL 与每个 claimed direct field 的短 evidence anchor。
- Tepper #6 tie 直接支持 rank/tie，但页面没有直接写明 `2026 Best Colleges`；它按 `edition_inferred_from_release_cycle` 降级为 partial candidate，不能进入 staging。
- Cornell #8 business 候选只称其版本为 `2025-26`，按 `edition_ambiguous` 保持为 partial candidate。两个 partial candidate 都不能进入 staging。
- 7 个 ranking-record identity mapping 对应 6 个逻辑 institution identity；Georgia Tech 的 Scheller 与 Aerospace school 名称显式合并到同一 Georgia Institute of Technology identity。所有 `UNITID` 均为 `null` / `not_collected`，没有猜测或创建 canonical university。

完整来源 URL、publisher、source type 与可访问性位于 `data/ranking-seeds/2026-best-colleges/pilot/source-manifest.json`。

- National Universities：U.S. News 发布、PR Newswire 公开转载。
- Undergraduate Business Programs：Carnegie Mellon Tepper 与 Cornell SC Johnson 页面仅作 partial candidate；Ohio State Fisher、Georgia Tech Scheller 为 direct-edition verified records。
- Aerospace Engineering：Georgia Tech Daniel Guggenheim School of Aerospace Engineering 官方页面。

## Coverage gaps

三个 stream 都是 **incomplete**：

- National Universities 尚未覆盖 numeric rank 4–50，也未知未采集 rank 的 tie groups。
- Undergraduate Business Programs 尚未覆盖其余 `<= 20` ranks 与完整 tie groups；发现 4 条不等于 Top 20 覆盖。
- Aerospace Engineering 尚未覆盖 rank 1、3–20 或完整 tie groups。

因此当前不得生成 `national_top_50`、`program_top_20`、最终 university universe、selection memberships 或前端导出。

## 真实 validation

- Python executable：`/usr/bin/python3`（Python 3.9.6）。
- 实际命令：

```bash
PYTHONPATH=src python3 -m pathos_data validate-ranking-pilot \
  --seed-batch data/ranking-seeds/2026-best-colleges/pilot/national-universities.json \
  --seed-batch data/ranking-seeds/2026-best-colleges/pilot/undergraduate-business-programs.json \
  --seed-batch data/ranking-seeds/2026-best-colleges/pilot/engineering-aerospace.json \
  --identity-mappings data/ranking-seeds/2026-best-colleges/pilot/identity-mappings.json \
  --candidate-observations data/ranking-seeds/2026-best-colleges/pilot/candidate-observations.json \
  --coverage-matrix data/ranking-seeds/2026-best-colleges/pilot/coverage-matrix.json \
  --source-manifest data/ranking-seeds/2026-best-colleges/pilot/source-manifest.json \
  --result-output data/ranking-seeds/2026-best-colleges/pilot/validation-result.json
```

结果：通过。聚合 validator 实际验证 3 个 seed batch、source manifest、identity mappings、candidate observations 与 coverage matrix；接受 6 条 verified staging records，拒绝 2 条 partially verified candidate，未创建 canonical university、selection membership 或 frontend export。`validation-result.json` 是该成功命令覆盖生成的结果，不再是先前手写的 `passed` 草稿。

Gate 2B1 修复后，正式 CLI 强制 full artifact path；缺 source manifest、coverage matrix、candidate observations 或 result output 会失败。`verified` 还必须具有字段级 evidence anchors，anchor source 必须在 manifest 中。`edition_direct`、`edition_inferred_from_release_cycle` 与 `edition_ambiguous` 规则防止 release-cycle 推断被伪装为 direct edition evidence。

全量 Python suite 为 33 / 33 通过；Stage 2A discovery validation 与已有 fixture/migration/schema validation 均通过。`git diff --check` 通过。前端在原 worktree 没有安装依赖，且其预先存在的 lockfile 与 manifest 不同步，故 lockfile-pinned `npm ci` 无法运行；在不改动工作树的临时副本以 `--package-lock=false` 安装依赖后，`tsc --noEmit` 通过。这是源码类型检查通过，不是对该 lockfile 可复现安装的声明。

## 风险与下一步

- U.S. News 直接 ranking pages 仍有访问限制；不能绕过 robots、登录、付费墙或 CAPTCHA。
- 其余排名需要人工 seed，人工来源核验成本高。
- edition 不能直接证实时必须降级为 partial 或 unresolved，不能用于正式 staging。
- identity mapping 仍需后续以 IPEDS UNITID 做正式解析。
- 本 pilot 不证明其余 stream 有同样的来源形态或同样可验证性。

技术上可以在获得独立审计或用户指示后扩展收集流程；当前不建议直接扩展或生成 universe。
