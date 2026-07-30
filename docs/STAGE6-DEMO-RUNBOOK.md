# PathOS Stage 6 Demo Runbook

## Demo checkpoint

- Workspace: `/Users/jiayihuang/Downloads/PathOS合并`
- Frontend: `/Users/jiayihuang/Downloads/PathOS合并/PathOS-main/frontend`
- Standalone backend: `/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking-standalone`
- Backend branch: `feature/stage6-demo-freeze-operational-readiness`
- Backend HEAD: `b73e61ec4fda11b7c72e74c14e414fbe2c74300f`
- Data mode: `backend`
- Preview contract: `pathos-preview-v1`
- Dataset: `stage5-preview-ec8c66e`
- Production data export: prohibited

## 快速操作

所有命令都可以从任意终端目录运行，但以下示例从统一工作区开始：

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并"

./pathos-demo doctor
./pathos-demo start
./pathos-demo status
./pathos-demo smoke
./pathos-demo open
./pathos-demo stop
```

完整的一键演示准备：

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并"
./pathos-demo demo
```

`demo` 按顺序执行 doctor、start、Smoke 和 status。它不会回退 fixture。

## 命令语义

| 命令 | 行为 |
|---|---|
| `doctor` | 只读检查 41 项环境、Git、进程身份工具、Bundle、数据边界和冻结点 |
| `doctor --json` | 输出机器可读 JSON |
| `start` | 必要时执行 `npm ci` 和 backend-mode build，然后启动真实 Preview |
| `start --rebuild` | 强制重新构建后启动 |
| `stop` | 只停止状态文件中记录、且 controller/listener/PGID 身份全部重新验证的进程组 |
| `restart` | 安全 stop 后重新 start |
| `status` | 检查 controller、listener、真实 PGID、监听端口和 Preview manifest 健康状态 |
| `status --json` | 输出机器可读状态 |
| `smoke` | 验证 contract、62 校、904 records、有效详情、404、页面和安全哨兵 |
| `open` | 在系统浏览器打开当前 managed URL |
| `demo` | 完成演示前的诊断、启动、Smoke 和状态检查 |

doctor 退出码：

- `0`：可启动，无 warning。
- `1`：存在阻塞性 failure。
- `2`：可启动，但存在 warning。

status 在停止状态返回 `1`，在 starting、stale、identity mismatch 或外部端口占用状态返回 `2`。

`status --json` 至少包含：

```text
status, controllerPid, listenerPid, pgid, port, url, dataMode,
bundlePath, uptime, logPath, identityVerified
```

可能状态：

- `RUNNING`
- `STARTING`
- `STOPPED`
- `STALE_STATE`
- `IDENTITY_MISMATCH`
- `PORT_OWNED_BY_FOREIGN_PROCESS`

## 启动行为

运行环境由控制器显式注入：

```text
PATHOS_DATA_MODE=backend
PATHOS_PREVIEW_BUNDLE_DIR=/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking-standalone/data-pipeline/artifacts/stage5-warning-aware-preview
```

脚本不读取 fixture 作为 fallback。端口 3000 被占用时，会依次寻找 3001–3099，并在 start/status 输出实际 URL。

运行状态和日志位于：

```text
/Users/jiayihuang/Downloads/PathOS合并/.pathos-demo-runtime/state.json
/Users/jiayihuang/Downloads/PathOS合并/.pathos-demo-runtime/frontend.log
```

状态文件权限为 `0600`，不包含 secret。

controller 由 Node 直接执行 npm，使用 `detached=true`、`shell=false`。
状态记录操作系统实际返回的 PGID，不假设 PGID 必须等于 npm PID。
listener 必须属于相同 PGID，并保持可信 Next.js command、前端 cwd、端口与启动时间身份。

启动前 doctor 会验证进程身份探测能力。spawn 成功但 controller identity
尚未建立时，控制器会把本次 `detached` spawn 创建的临时进程组作为仅限失败回收的
launch guard；它不会用于接受 listener，也不会替代运行状态中的 OS 实际 PGID。
若身份探测随后失败，只清理该 launch guard 对应的 controller 与同组 child。

stop 只向重新验证且不属于当前控制脚本的 PGID 发送信号。SIGTERM 后仍存活时，
只有组内剩余进程的 PGID、cwd 和 npm/Next.js command 全部仍可信，才允许 SIGKILL。

在 macOS 上，`lsof -Fn` 可能把中文 cwd 输出为连续的 UTF-8 byte escapes，
例如 `PathOS\xe5\x90\x88\xe5\xb9\xb6`。控制器先以严格 UTF-8 decoder
恢复这些 bytes，再对 lsof cwd 和配置路径双方执行 NFC、`path.resolve` 与
`realpath.native`；任何非法 escape、非法 UTF-8、不存在路径或 symlink 逃逸
都会 fail closed。该兼容处理不放宽 cwd、PGID、listener、start time、command
或 port identity 检查。

## 演示前 5 分钟检查

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并"
./pathos-demo doctor
./pathos-demo smoke
./pathos-demo start
./pathos-demo status
```

预期：

- doctor：无 FAIL；默认端口被外部服务占用时允许一个明确的 WARN
- Smoke：`12/12`
- mode：`backend`
- school/summary/detail：`62/62/62`
- verified records：`904`
- unknown university：HTTP 404

## 建议演示路线

1. `/map?mode=parent`
   - URL 自动降级为 `mode=student`。
   - Parent Mode 不可进入。
   - 真实 62 校 POI 可用。
2. `/university/candidate-v2%3Aharvard-university`
   - 展示 Preview 标识、来源和 `数据补充中`。
3. `/university/candidate-v2%3Aarizona-state-university`
   - SAT/ACT `not_reported`，不得显示 0。
   - national rank 为 `not_in_current_national_scope`，不得显示 rank 0。
4. `/university/candidate-v2%3Aharvey-mudd-college`
   - partial enrollment 保持 warning。
5. `/university/candidate-v2%3Aboston-college`
   - county-only geography 不冒充 city/place。
6. `/university/candidate-v2%3Adoes-not-exist`
   - 显示「未找到该学校」，不显示其他学校 fixture。

## Stage 5 PASS 恢复点

冻结目录：

```text
/Users/jiayihuang/Downloads/PathOS合并-integration-baseline/stage5-pass-freeze
```

只读校验：

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并"
./scripts/pathos-freeze-check.sh
```

归档解压只能使用新的空目录，不得直接覆盖当前前端：

```bash
mkdir -p "/private/tmp/pathos-stage5-pass-recovery"
tar -xzf "/Users/jiayihuang/Downloads/PathOS合并-integration-baseline/stage5-pass-freeze/stage5-pass-frontend-snapshot.tar.gz" \
  -C "/private/tmp/pathos-stage5-pass-recovery"
```

先对比恢复目录与当前前端，再由操作者决定是否进行逐文件恢复。

Stage 6 根冻结清单：

```text
/Users/jiayihuang/Downloads/PathOS合并/STAGE6-DEMO-FREEZE-MANIFEST.json
```

它绑定 backend checkpoint、Preview contract、Bundle hashes、Stage 5 PASS 前端归档、
控制器和所有 Stage 6 scripts，不包含 secret、`.env.local` 内容或 cache body。
Root manifest 引用 post-Unicode-closing cumulative、Closing Runtime 和 Unicode
Closing manifests 的最终 SHA-256。Cumulative inventory 中 Root、自身和 Unicode
Closing manifest 条目明确排除递归 hash，不以不可实现的自引用声称完整性。

## 演示结束

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并"
./pathos-demo stop
./pathos-demo status
```

最终 status 应为 `STOPPED`。Stage 6 Gate 前不得创建 tag、push 或生成 production data export。
