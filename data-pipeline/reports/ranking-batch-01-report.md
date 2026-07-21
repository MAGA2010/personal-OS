# PathOS Stage 2B2｜Ranking Stream Batch 1

执行日期：2026-07-11（validation result 保存 UTC 时间戳）
范围：7 条未处理的本科 business specialty streams；不是 university universe，也不是任何类别的完整 cutoff 覆盖。

## 选择与来源策略

所有 Batch 1 category 均来自 2026 Best Colleges inventory，且没有重用 National Universities、Undergraduate Business Programs 或 Aerospace Engineering pilot stream。inventory 的共同 `undergraduate_program` family 不变；本批次以 business specialty 的不同类别验证多-stream full-artifact 流程。

| Stream / official category | 选择原因 | 预计来源策略 |
| --- | --- | --- |
| `business-accounting` / Accounting | ASU 官方页直接给出 Top-20 rank | ASU 2026 Best Colleges 官方新闻 |
| `business-analytics` / Analytics | 同一公开页面给出直接 rank | ASU 官方新闻 |
| `business-management-information-systems` / Management Information Systems | 覆盖 business technology specialty | ASU 官方新闻 |
| `business-production-operations-management` / Production/Operations Management | 覆盖 operations specialty | ASU 官方新闻 |
| `business-management` / Management | 覆盖一般 management specialty | ASU 官方新闻 |
| `business-supply-chain-management-logistics` / Supply Chain Management/Logistics | 覆盖 logistics specialty | ASU 官方新闻 |
| `business-real-estate` / Real Estate | 使用第二所大学的不同来源页面 | University of Florida Warrington 官方新闻 |

## 结果与覆盖

| Stream | discovered | verified | partial | unresolved | ties | identity resolved / unresolved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Accounting | 1 | 1 | 0 | 0 | 0 | 1 / 0 |
| Analytics | 1 | 1 | 0 | 0 | 0 | 1 / 0 |
| Management Information Systems | 1 | 1 | 0 | 0 | 0 | 1 / 0 |
| Production/Operations Management | 1 | 1 | 0 | 0 | 0 | 1 / 0 |
| Management | 1 | 1 | 0 | 0 | 0 | 1 / 0 |
| Supply Chain Management/Logistics | 1 | 1 | 0 | 0 | 0 | 1 / 0 |
| Real Estate | 1 | 1 | 0 | 0 | 0 | 1 / 0 |

- full artifact validation：**7 accepted verified / 0 rejected partial / 0 unresolved**。
- 每个 verified record 提供完整 direct evidence anchors，覆盖 source display name、ranking family、category、edition、numeric rank、displayed rank 与 tie；每个 anchor source_id 都在 source manifest 中。
- 7 个 record mapping 均 resolved，归并到 Arizona State University 或 University of Florida 两个逻辑 institution identity。UNITID 均为 `null` / `not_collected`，没有猜测或写入 canonical university。
- 每条 stream 仍为 **incomplete**：只收集到一个有来源的 Top-20 record；其余 `<=20` ranks 和 tie groups 未覆盖。发现记录数不等于完整 cutoff coverage。

## Full artifact validation

正式 CLI 使用 7 个 seed batch、identity mappings、source manifest、空 candidate observations、coverage matrix 和 result output。`validation-result.json` 由成功运行生成，未手工写入 `passed`。

## Transport 中断恢复

首次 Batch 1 聚合测试和后续只读状态检查都因执行服务 `transport decode error` 中断；这不是业务测试失败，结果视为未知。没有使用替代脚本绕过、没有跳过 full artifact validation。服务恢复后，使用同一项目 unittest 命令重新运行聚合测试并通过，再继续正式 validation。

## 风险与 Batch 2 建议

- 本批次仅说明公开大学新闻页可以提供带 edition anchors 的个别 Top-20 record，不证明完整 category coverage 或其余 stream 的来源形态。
- U.S. News 直接 ranking pages 仍可能受 robots/访问限制；不得绕过。
- 后续仍需 IPEDS UNITID 正式 identity resolution。

建议在检查本批次来源与 coverage matrix 后，继续受控 Batch 2；仍不得生成 university universe，直至所有 scope stream 的 cutoff coverage 达到可审计标准。
