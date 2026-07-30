# PathOS 开发历史时间线

## 1. Hackathon 初始想法

项目从「地图 + AI 升学指导」出发，希望把选校从列表浏览变成空间探索：用户既能看到学校，也能理解州、城市、费用和申请偏好的关系。

## 2. 数据库与学校集合阶段

- 建立 US News national / program ranking seeds 与 Candidate v2 学校集合。
- 汇集学校基本信息、排名、专业、招生、费用、位置和来源记录。
- 形成 62 所 Preview 学校、62 条 Summary、62 条 Detail。
- Stage 4B 与 Stage 4C 累计冻结 904 条 verified records。
- 人物与专业资料分批补充，保留 130 个 program-person gaps。

## 3. 数据 Pipeline 阶段

管道逐步形成以下层次：

```text
raw → staging → canonical → validation → preview artifacts → frontend
```

- 引入 source manifest、field provenance、status dictionary 与 warning code。
- 候选、pending、deferred、quarantined 与 verified 边界被显式区分。
- Stage 5 建立 warning-aware Preview Adapter 与 deterministic Preview Bundle。

## 4. Map 阶段

- 采用 MapLibre 呈现大学 Marker、卡片和详情入口。
- 完成州级 TopoJSON / FIPS join、单州选择和 URL state。
- 引入 income、safety、employment、chinese_population 四项 Choropleth。
- 形成 204 条区域记录和 51 个州级辖区覆盖。
- 完成州内学校侧栏、Tooltip、Legend、Toolbar 和 Mobile Bottom Sheet。

## 5. Frontend 数据链重构

- 建立 `PathOSDataSource`、Runtime Schema、Normalizer 与领域模型。
- 从正式路径移除旧 mock / fixture 事实依赖。
- 通过 Next.js BFF 读取 standalone Preview Bundle。
- Backend failure 采用 fail closed，不静默回退 fixture。
- University Detail 改为动态服务端路由。

## 6. Stage 5 与 Stage 6 稳定化

- Stage 5 完成前后端 Integration Gate、Parent Mode readiness gating 和错误呈现。
- Stage 6 建立 `pathos-demo` doctor / start / stop / status / smoke 生命周期工具。
- 修复 macOS 中文路径、PID / PGID 身份绑定和安全停止问题。
- 建立 Stage 6 checkpoint、manifest、恢复说明和本地 annotated tag。

## 7. Stage 7 前端与区域体验

- 完成主题、响应式地图布局、热力图控制和碰撞修复。
- Assessment、Calculator、Match、Portfolio 得到交互与缺失值语义修正。
- 首页加入功能入场动画、Feature Showcase 与翻转卡片交互。
- News 建立墨绿编辑式 Hero、9 张本地校园摄影和 Credits。

## 8. 并行开发耦合

- 对第二位前端贡献进行项目、路由、模块、依赖和媒体盘点。
- 采用 Hybrid 策略：保留 Canonical 数据链和功能逻辑，吸收更成熟的首页叙事与视觉结构。
- 拒绝候选 mock、未知媒体、旧 Backend ZIP、重复 Header / Footer 和第二套 UI framework。
- 在隔离 integration workspace 中完成耦合，没有覆盖稳定 checkpoint。

## 9. 公网 Preview 与最后调试

- 建立 Vercel Preview 项目 `pathos-preview-20260726`。
- 部署快照放在 `vercel-deploy/pathos-preview-20260726`。
- 对公网 Map 的 Marker、主题切换、区域图层和 URL metric retention 进行过多轮调试。
- 冻结前仍保留需人工复核的地图叠层 / Marker 共存问题，因此不将公网 Preview 视为生产发布。

## 10. 最终归档

2026-07-29 停止继续开发。本阶段只核验、总结并创建 `FINAL_PROJECT_ARCHIVE/`，不修改业务代码、数据、Backend、Bundle 或 UI。
