# PathOS Stage 6 故障恢复 Runbook

## 总原则

1. 先运行 `./pathos-demo doctor`。
2. 不回退 fixture。
3. 不修改 Stage 4B/4C、Candidate v2、ranking、people 或 Preview 数据事实。
4. 不复制旧 cache、handoff 或 linked-worktree 文件。
5. 不写入旧 Git source 或 linked backend。
6. 恢复操作必须可定位到一个明确文件、PID 或端口。

## `.env.local` 不存在

无需创建才能启动。`start` 会显式注入 backend mode 和 standalone Bundle 路径。doctor 返回 warning 后仍可启动。

如需本地开发文件，只能从 `.env.example` 创建，且不得加入 secret：

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并/PathOS-main/frontend"
cp ".env.example" ".env.local"
```

## 端口 3000 被占用

无需停止未知进程。`start` 自动选择 3001–3099：

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并"
./pathos-demo start
./pathos-demo status
```

始终使用 status 输出的实际 URL。

## stale 状态文件

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并"
./pathos-demo stop
./pathos-demo status
```

stop 会删除已确认不存在的 stale PID 状态。若 PID 存在但 cwd 或监听端口不匹配，脚本拒绝终止它；不要手动 kill，先调查 PID 所属应用。

## node_modules 缺失

`start` 自动运行 `npm ci`。若安装失败：

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并/PathOS-main/frontend"
npm ci
```

网络不可用时记录为依赖安装环境问题，不得通过 fixture 或删除 lockfile 绕过。

## `.next` 缺失或陈旧

`start` 会比较 `BUILD_ID` 与 `src/`、`public/` 和关键配置时间，必要时自动构建。

强制重建：

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并"
./pathos-demo restart --rebuild
```

这只生成前端 build，不生成 production data export。

## Preview Bundle 缺失或 hash 不匹配

doctor 返回 FAIL，start 必须停止。不得回退 fixture。

只读确认：

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking-standalone"
git status --short
git rev-parse HEAD
git ls-tree -r --name-only "b73e61ec4fda11b7c72e74c14e414fbe2c74300f" \
  "data-pipeline/artifacts/stage5-warning-aware-preview"
```

若仅是 tracked Bundle 被误删或损坏，先在独立临时目录用 `git archive` 提取 checkpoint 并对比。未经明确审查，不得覆盖当前 backend。不得从旧仓库、linked backend、handoff 或 cache 恢复。

## Backend HEAD 或 worktree 不匹配

停止启动，不执行 reset、rebase、stash 或 clean：

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking-standalone"
git branch --show-current
git rev-parse HEAD
git status --short
git diff --check
```

保留现场并根据 diff 审查。Stage 6 Demo checkpoint 要求 HEAD 为 `b73e61e...`，分支为 `feature/stage6-demo-freeze-operational-readiness`。

## Backend 页面显示明确错误

1. 运行 `./pathos-demo status`。
2. 运行 `./pathos-demo doctor`。
3. 查看 `.pathos-demo-runtime/frontend.log`。
4. 修复 Bundle/服务状态后运行 `./pathos-demo restart`。
5. 运行 `./pathos-demo smoke`。

错误期间不得显示 fixture 学校，不得把 failure 转成空数据成功。

## 外部地图、字体或底图不可用

这是非核心外部网络依赖。确认：

- 页面 shell、真实学校 API 和详情页仍可用。
- Console 中错误仅来自外部 tile/font 域。
- 不修改数据事实或启用 choropleth 作为补偿。

演示时可以转到学校详情和来源面板，记录外部依赖限制后继续。

## Stage 5 PASS 前端恢复

先校验：

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并"
./scripts/pathos-freeze-check.sh
```

将归档提取到空目录：

```bash
mkdir -p "/private/tmp/pathos-stage5-pass-recovery"
tar -xzf "/Users/jiayihuang/Downloads/PathOS合并-integration-baseline/stage5-pass-freeze/stage5-pass-frontend-snapshot.tar.gz" \
  -C "/private/tmp/pathos-stage5-pass-recovery"
```

不得直接覆盖非 Git 前端。先逐文件对比 Closing Patch manifest 与 Stage 5 PASS manifest，再执行经过审查的最小恢复。

## 无法停止 managed 服务

状态文件提供 PID、端口和 frontend cwd。仅当以下三者同时匹配时处理：

- PID 仍存在；
- PID cwd 为冻结前端目录；
- PID 正在监听状态文件端口。

先重试：

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并"
./pathos-demo stop
```

脚本先发送 SIGTERM，15 秒后才对同一已验证 PID 使用 SIGKILL。不得对未知 PID 或目录执行 kill。
