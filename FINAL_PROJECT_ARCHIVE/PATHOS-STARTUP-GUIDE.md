# PathOS 启动指南

## 1. 当前真实运行架构

PathOS 当前由一个 Next.js 服务同时提供页面和 BFF。BFF 直接以只读方式加载 Preview Bundle，因此无需额外启动 Python、FastAPI 或 Flask HTTP 服务。

```text
Next.js frontend + BFF → local Preview Bundle
```

Standalone Backend 是数据管道与冻结 artifacts 的仓库，不是必须单独启动的 Web server。

## 2. 推荐：启动最终前端

唯一正式前端位于 `frontend/`，并自带只读 `data/preview`：

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并/frontend"
```

若 `node_modules` 不存在，按 lockfile 安装：

```bash
npm ci
```

启动开发服务器：

```bash
PATHOS_DATA_MODE=backend \
PATHOS_PREVIEW_BUNDLE_DIR="./data/preview" \
PATHOS_BACKEND_TIMEOUT_MS=10000 \
npm run dev -- -p 3017
```

打开：

```text
http://127.0.0.1:3017/
http://127.0.0.1:3017/map
http://127.0.0.1:3017/news
```

停止时在启动终端按 `Control-C`。不要使用 `pkill`、`killall` 或终止未知 PID。

## 3. 使用 Canonical Bundle 启动选定前端

如果未来从新的隔离工作副本启动，应把 `PATHOS_PREVIEW_BUNDLE_DIR` 指向：

```text
/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking-standalone/data-pipeline/artifacts/stage5-warning-aware-preview
```

必须保持 `PATHOS_DATA_MODE=backend`。不要通过 `.env.local` 静默切换 fixture，也不要把密钥写入命令日志或文档。

## 4. 构建与生产式本地预览

只有在恢复开发并准备重新验证时执行：

```bash
npm run build
PATHOS_DATA_MODE=backend \
PATHOS_PREVIEW_BUNDLE_DIR="/absolute/path/to/stage5-warning-aware-preview" \
npm run start -- -p 3017
```

构建成功不等于 Production Data Export，也不代表生产发布。

## 5. Stage 6 运行工具的归档状态

Stage 6 的 `pathos-demo` 曾绑定历史前端路径和 Stage 6 分支。公开发布清理时已移除该过时运行器，其审计报告仍在 `docs/` 中保留。当前唯一支持的启动方式是上述 `frontend/` 中的 npm 命令。

## 6. 端口历史

| 端口 | 历史用途 |
|---:|---|
| 3002 | Stage 7 开发与地图 / 热力图复核的常用安全端口。 |
| 3003 | 3002 被占用时的开发备用端口。 |
| 3017 | Integration Bugfix、当前人工 review 与部署快照的推荐端口。 |
| 3018 | 曾为“如需独立 Backend”的预留端口；当前架构没有必须启动的独立 HTTP Backend。 |

启动前使用 `lsof -nP -iTCP:<port> -sTCP:LISTEN` 检查端口。若被未知服务占用，选择其他端口，不要接管或终止外部服务。

## 7. 公网 Preview

```text
https://pathos-preview-20260726.vercel.app
```

这是 Demo / Preview 地址。可用性取决于 Vercel 项目状态；它不是生产级服务承诺。

## 8. 最小健康检查

```bash
curl -fsS "http://127.0.0.1:3017/api/pathos/preview?endpoint=manifest"
curl -I "http://127.0.0.1:3017/map"
curl -I "http://127.0.0.1:3017/news"
```

Manifest 应显示 `contractVersion=pathos-preview-v1`、`view=preview` 和 62/62/62/904。仍需浏览器人工检查地图 Marker、区域图层、Console 与 Network。
