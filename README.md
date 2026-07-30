# PathOS

PathOS 是一个面向美国本科留学探索的数据驱动平台，通过交互式地图、大学资料、区域指标、选校工具和留学资讯帮助用户理解选校空间。

## 当前状态

这是 Preview / Demo 版本，不是录取预测系统，也不替代专业升学顾问。项目保留来源、状态、warning 和缺失值边界；Production Data Export 未启用。

## 核心功能

- MapLibre 交互地图、大学 Marker、学校卡片和动态详情页。
- income、safety、employment、chinese_population 四项州级区域图层。
- 单州高亮、州内学校列表、URL `region/state` 与 Back / Forward。
- Assessment、Calculator、Match、Portfolio 的基础流程。
- 编辑式首页、Feature Showcase、功能入场动画和统一主题。
- News 入口、9 张本地授权校园摄影和 Credits 页面。
- Next.js BFF + Preview Bundle；backend mode 失败时不回退 fixture。
- AI 辅助框架与确定性本地分析；真实模型尚未达到生产级。

## 数据边界

| 数据集 | 当前范围 |
|---|---:|
| Schools | 62 |
| Summaries | 62 |
| Details | 62 |
| Verified records | 904 |
| Regional metrics | 4 |
| Regional records | 204 |
| State-level jurisdictions | 51 |

大学数据 contract 为 `pathos-preview-v1`。区域指标只用于地图环境参考，`usedForMatch=false`。

## 技术架构

```text
Browser
  → Next.js App Router
  → Next.js BFF (/api/pathos/preview)
  → local Stage 5 Preview Bundle
```

前端使用 Next.js 14、React 18、TypeScript、MapLibre、Tailwind CSS 和 Vitest。Standalone Backend 保存数据管道、schema、validator、provenance 和冻结 artifacts。无需另启 Python HTTP 服务。

## 仓库结构

```text
PathOS/
├── frontend/                         # 唯一正式前端与本地 Preview 副本
├── PathOS-db-ranking-standalone/     # standalone Backend 与数据管道
├── FINAL_PROJECT_ARCHIVE/            # 最终冻结和发布记录
├── docs/                             # 阶段报告与审计证据
├── resource/                         # 区域来源工作簿
├── scripts/                          # Demo 生命周期工具
├── .env.example
├── SECURITY.md
└── README-FINAL.md
```

## 快速启动

环境要求：Node.js 20+、npm。

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev -- -p 3017
```

默认地址：`http://127.0.0.1:3017`。

`.env.example` 默认使用 `PATHOS_DATA_MODE=backend` 和本地 `./data/preview`。不要提交 `.env.local`。

## 环境变量

| 变量 | 用途 |
|---|---|
| `PATHOS_DATA_MODE` | 必须为 `backend` 才能使用正式 Preview 链路。 |
| `PATHOS_PREVIEW_BUNDLE_DIR` | Preview Bundle 目录；仓库默认 `./data/preview`。 |
| `PATHOS_BACKEND_TIMEOUT_MS` | BFF 超时。 |
| `NEXT_PUBLIC_PATHOS_MAP_PROVIDER` | `maplibre`（默认）或可选 `baidu`。 |
| `NEXT_PUBLIC_BAIDU_MAP_AK` | Baidu Runtime 可选配置；使用者自行申请。 |
| `DEEPSEEK_API_KEY` | 可选外部 AI provider；不要提交真实值。 |

## 数据可信度原则

- 来源可追溯；缺失值优于伪造值。
- `null` 不显示为 0、rank 0、¥0、0/100、0:1 或 `[0,0]`。
- pending / deferred 不转换成 verified fact。
- Fixture 只用于显式测试，不是 backend mode 的事实来源。
- Preview 数据为 `sourceLimited=true`、`incomplete=true`、`notFinal=true`。

## 图片与许可证

News 的 9 张校园 WebP 来自独立核验的 Wikimedia Commons File 页面。署名和许可证见：

- `frontend/public/news/campus/ATTRIBUTIONS.md`
- `frontend/docs/STAGE7B-A3-3-NEWS-PHOTOGRAPHY-LICENSES.json`

首页 Entry 使用的地球摄影来源见 `frontend/public/entry/ATTRIBUTIONS.md`。

## 已知限制

- AI 不是生产级 LLM 顾问服务。
- Rankings 与 Explore 尚未正式产品化。
- 没有用户账户、支付或商业化系统。
- Baidu Runtime 需要使用者自行配置 AK；默认使用 MapLibre。
- 公网 Preview 仍需复核 Marker、Choropleth 和 metric retention 的组合场景。
- 当前部署与数据均为 Demo / Preview，不是生产发布。

## Final Archive

完整冻结记录见 [FINAL_PROJECT_ARCHIVE](./FINAL_PROJECT_ARCHIVE/PATHOS-FINAL-SUMMARY.md)，启动细节见 [PATHOS-STARTUP-GUIDE.md](./FINAL_PROJECT_ARCHIVE/PATHOS-STARTUP-GUIDE.md)。

## 免责声明

PathOS 是 Demo / Research project。内容用于信息探索，不构成录取预测、申请保证、法律意见、财务意见或专业顾问服务。使用者应回到原始来源核验信息。
