# 人工 Seed 导入

仅当 U.S. News 排名无法通过公开、稳定、合规来源完整获取时，才创建人工 seed。必须使用 `schemas/v1/manual-ranking-seed-batch.json`，并通过 `python -m pathos_data validate-ranking-discovery` 校验。每条 seed 必须包含 ranking system、family、category、edition、学校显示名、数字名次、显示名次、并列标记、来源、来源访问时间、录入者、录入时间、核验状态和备注。

人工 seed 不是绕过付费墙、登录、CAPTCHA 或 robots.txt 的替代方案。没有公开可核验来源时，记录 coverage gap 与 `data_quality_issues`，不要猜测排名。

测试 fixture 只能放在 `tests/fixtures/`；不得放入此目录或 `data/canonical/`。

通过 validation 的 batch 只能进入 `manual_ranking_seed_staging`；它仍须经过后续 identity resolution、canonical validation 和 source 审计，不能绕过 canonical validation 直接生成 universe 或 frontend export。
