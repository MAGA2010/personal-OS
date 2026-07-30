# PathOS Stage 2C｜Full Ranking Corpus Validation

纳入：`pilot`、`batch-01`、`batch-02`、`batch-03`，没有遗漏或未来 batch。

| 指标 | 结果 |
| --- | ---: |
| 总 streams / 已处理 streams | 29 / 29 |
| verified records | 24 |
| partial rejected / unresolved | 2 / 0 |
| no-verified streams | 8 |
| duplicate records / identity conflicts | 0 / 0 |
| identity unresolved | 0 |
| incomplete streams | 29 |

Corpus validator 逐 batch 重跑 full artifact contract，并做跨 batch duplicate、stream-record edition/category/family、anchor manifest、identity alias 与 scope 检查。Global、Graduate、非本科 family 均未混入；排除 category 未出现；没有 universe、selection membership 或 frontend export。

8 个 no-verified streams 只作为带 `no_verified_reason` 的 coverage gaps，未生成 fake seed/identity。National Universities 仍只具有 Top 3 pilot coverage；其余每个 category 均 source-limited，未达完整 cutoff coverage。

`universe_candidate_ready: true`：所有 scope streams 已处理，verified/partial/no-verified 状态可审计，且没有 critical duplicate/identity/edition/category/scope issue。它只允许下一阶段生成 source-limited、incomplete 的 **university-universe-candidate**，不允许生成 final universe。进入前应审计 candidate policy、跨 batch school identity 与 cutoff-gap disclosure。
