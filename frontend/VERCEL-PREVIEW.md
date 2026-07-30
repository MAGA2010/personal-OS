# PathOS Vercel Preview

该目录是从整合候选前端生成的隔离部署包。它内置 Stage 5 只读 Preview Bundle，供 Next.js BFF 在 Vercel Node.js 运行时读取。

- 数据模式：`backend`
- Bundle 路径：`data/preview`
- Production Data Export：禁止
- 本目录不包含 `.env.local`、Git metadata、构建缓存或 `node_modules`
- 原 Backend 与原 Preview Bundle 不被修改

部署环境变量：

- `PATHOS_DATA_MODE=backend`
- `PATHOS_PREVIEW_BUNDLE_DIR=data/preview`
- `PATHOS_BACKEND_TIMEOUT_MS=10000`
- `NEXT_PUBLIC_PATHOS_MAP_PROVIDER=maplibre`
