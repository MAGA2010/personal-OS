# PathOS Frontend

这是 PathOS 唯一正式前端。它使用 Next.js App Router，并由同一 Next.js 服务通过 BFF 读取本地 Preview Bundle。

## 启动

```bash
npm ci
cp .env.example .env.local
npm run dev -- -p 3017
```

默认 Bundle 位于 `data/preview`，无需另启 Python HTTP 服务。不要提交 `.env.local` 或任何真实 API Key。

完整项目说明见仓库根目录 `README.md`，冻结状态见 `FINAL_PROJECT_ARCHIVE/`。
