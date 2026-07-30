# PathOS 当前功能状态

| Feature | 状态 | 说明 |
|---|---|---|
| Home / Brand Story | 已完成 Demo | 象牙白编辑式首页、品牌叙事、CTA 与 Feature Showcase。 |
| Feature Entry Animation | 已完成 Demo | Map、Assessment、Match、Portfolio 的入场页与环境效果。 |
| Interactive Map | 已完成 Demo，需公网复核 | MapLibre 大学探索、Marker、Tooltip、学校卡片与详情入口。 |
| Regional Heatmap | 已完成 Demo | 4 项州级指标、204 条记录、51 个辖区；只用于 Map。 |
| State Selection | 已完成 Demo | 单州高亮、URL state、州内大学列表与 Back / Forward。 |
| University Detail | 已完成 Demo | 62 所学校动态详情路由，缺失值不会伪装成 0。 |
| Search / Filter | 基础完成 | 学校搜索与地图筛选已接入真实 DataSource。 |
| Compare | 基础完成 | 比较能力位于地图 `ComparePanel`；没有独立 `/compare` 路由。 |
| News | 已完成 Demo | 编辑式入口、9 张本地校园 WebP、Credits 与 reduced-motion。 |
| Assessment | 基础完成 | 输入流程、权重交互和评估展示骨架。 |
| Calculator | 基础完成 | 搜索、选择、删除和最多 3 校费用比较。 |
| Match | 基础完成 | 当前综合分基于真实可用维度；区域指标不进入算法。 |
| Portfolio | 基础完成 | 选校清单与组合分析入口。 |
| AI Advisor | 框架存在 | 可生成确定性本地分析；外部模型不是冻结版本的生产依赖。 |
| Theme | 已完成 Demo | Light / Dark / System 与响应式主题。 |
| Error Handling | 已完成基础链路 | Backend 失败 fail closed，不回退 fixture。 |
| Data Provenance | 已完成基础链路 | Source / status / warning / feature readiness 可追踪。 |
| Rankings | 未产品化 | 候选概念被归档，没有正式数据契约或路由。 |
| Explore | 未产品化 | 候选概念被归档，没有正式产品状态。 |
| User Accounts | 未实现 | 无注册、登录、持久化档案或权限体系。 |
| Payment / Subscription | 未实现 | 无支付或商业化系统。 |

## 正式路由快照

当前部署快照包含：

- `/`
- `/map`
- `/news`
- `/news/credits`
- `/assessment`
- `/calculator`
- `/match`
- `/portfolio`
- `/university/[id]`
- `/xuanxiao`
- `/entry/map`
- `/entry/assessment`
- `/entry/match`
- `/entry/portfolio`

另有 Next.js BFF：`/api/pathos/preview`、`/api/ai/analyze`、`/api/ai/context` 和 `/api/xuanxiao/universities`。

## 功能声明边界

- 所有功能均按 Preview / Demo 口径描述。
- AI 输出不构成录取建议或录取保证。
- Rankings、Explore、用户系统和商业化功能不应被描述为已完成。
- Production Data Export 保持禁止。
