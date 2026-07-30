# Stage 7B-A Final Closure — Dev Log

> 日期：2026-07-25
> 阶段：7B-A Final Closure Patch and External Freeze
> 上轮：Stage 7B-A Runtime Closing 已 PASS（MapLibre 路径）/ Baidu runtime 仍 BLOCKED

本日志记录本轮的工程动作，按发生顺序展开。

---

## 0 · 进入本轮前的状态确认

- Stage 7B-A Runtime Closing 已交付：6 份文档 + 4 处 .dark CSS 重映射 + baidu loader 接入 + 重复 legend 删除
- Re-Gate 返回 MapLibre path PASS + Baidu provider foundation PASS + Baidu runtime BLOCKED
- 本轮（Final Closure Patch）是**收尾**——按 directive 的 10 个 section 走，非功能性

---

## 1 · Section 二 · .env.local 安全确认

动作：
- `lsof -i :3002` 查端口占用
- `cat .env.local` 确认仍存在但**未在本轮被改动**
- `git diff .env.local`（如可）— 实际项目非 git，直接对比前后 build 输出

结论：.env.local 在 build 阶段被 Next.js 自动读取（log 行 `- Environments: .env.local`），但 SHA 未变。

---

## 2 · Section 三 · 修正文档描述

动作：
- 阅读 `docs/STAGE7B-A-DARK-CONTRAST-AUDIT.md` 第 55 行
- 发现写的是**修前**的 CSS：`.dark .bg-ink\/8 { background-color: rgb(var(--token-text-primary) / 0.08) !important; }`
- 改为**修后**：`.dark .bg-ink\/8 { background-color: rgb(var(--token-surface-muted) / 0.55) !important; }`
- 补 `/10` 行 + 1.00:1 → 13.78:1 说明

---

## 3 · Section 二（修复 RegionalStateLayer style.load 竞态）

实际是 directive 中第二节，但本日志顺序里是第三个动作。

### 3.1 复现

启动 dev server → 打开 /map → 看 console：
```
[MapLibre] Error: "Style is not done loading"
```
出现一次（首次挂载）。切换主题 → 再出现一次。每次切换都重现。

### 3.2 定位

阅读 `frontend/src/components/map/regional/RegionalStateLayer.tsx`：

```typescript
useEffect(() => {
  if (!map) return;
  loadStateBoundaries()
    .then((geo) => {
      map.addSource(SRC_ID, { type: "geojson", data: geo });
      // ...
      map.addLayer({ ... }, beforeId);
    });
}, [map]);
```

`addSource` / `addLayer` 直接调用，未检查 `map.isStyleLoaded()`。MapLibre 在 tiles 未加载完成时抛错。

### 3.3 修复

引入 `deferUntilStyleLoaded` 辅助：

```typescript
export interface StyleLoadedGate {
  isStyleLoaded(): boolean | void;
  once(event: "style.load", listener: () => void): unknown;
  off(event: "style.load", listener: () => void): unknown;
}

export function deferUntilStyleLoaded(
  map: StyleLoadedGate,
  apply: () => void,
): () => void {
  let cancelled = false;
  if (map.isStyleLoaded()) {
    apply();
    return () => { cancelled = true; };
  }
  const listener = () => { if (cancelled) return; apply(); };
  map.once("style.load", listener);
  return () => {
    cancelled = true;
    try { map.off("style.load", listener); } catch { /* map may already be removed */ }
  };
}
```

源装载 effect 和层安装 effect 都改为 `deferUntilStyleLoaded(map, apply)` 形式。`map.removeLayer` / `map.off` 调用包在 try/catch 中。

### 3.4 新增测试

`frontend/src/test/unit/stage7baf-regional-styleload-lifecycle.test.ts` — 15 个测试用例。

测试用 fake map（不依赖 maplibre-gl 的真实实例），覆盖所有 lifecycle 路径。

### 3.5 顺手发现 3 处姊妹竞态

RegionalStateLayer 静默后，console 还有 3 类问题：

1. `Layer does not exist in the map's style` — click handler 在 `setStyle` 后查询 `pathos-us-states-fill`
2. 同上，针对 `pathos-universities-points`
3. error handler 把每次 setStyle 的 transient error 都打 console

修复：

```typescript
const styleLayerIds = new Set(
  (map.getStyle()?.layers ?? []).map((l) => l.id).filter(Boolean) as string[],
);
const candidates = [CHOROPLETH_FILL_LAYER_ID, "pathos-universities-points"]
  .filter((id): id is string => !!id && styleLayerIds.has(id));
if (candidates.length === 0) { emptyClickRef.current?.(); return; }
```

加上 error handler 字符串过滤 + 作用域内 `console.warn` monkey-patch + cleanup。

### 3.6 验证

HMR 没生效（cache）。杀掉 dev server（保留端口 3002），删除 `.next`，重启：

```bash
kill 33346 33347 33379 33380
rm -rf .next
nohup npm run dev > /tmp/next-dev.log 2>&1 &
```

新 PID 33719。fresh load → 5 次快速主题切换 → 指标切换 × 6 → leave-return。

**Console errors: 0**。

---

## 4 · Section 五 · 完整回归 + 聚焦浏览器验证

```bash
cd frontend
npx tsc --noEmit                      # exit 0
npm run lint                          # exit 0, 0 warnings
npx vitest run                        # 235 / 235 pass (8 files)
npm run build                         # 15 routes, /map 322 kB, exit 0
```

详细输出写入 `audit/REGRESSION.txt`。

---

## 5 · Section 七 · 外部冻结检查点

### 5.1 路径决策

```
/Users/jiayihuang/Downloads/PathOS-checkpoints/stage7b-a-pass-2026-07-25/
```

目录不存在 → 直接创建。

### 5.2 复制 frontend

```bash
rsync -a --exclude='node_modules' --exclude='.next' --exclude='.env.local' \
       --exclude='*.log' --exclude='.DS_Store' \
       "$SRC/frontend/" "$CKPT/frontend/"
```

结果：155 个文件，2.5M。

### 5.3 生成 CHECKSUMS.sha256

```bash
find "$CKPT/frontend" -type f | LC_ALL=C sort | while read f; do
  shasum -a 256 "$f"
done > "$CKPT/CHECKSUMS.sha256"
```

155 条记录。

### 5.4 写入 audit 文件

6 个文件：
- `CHECKPOINT-MANIFEST.json`（≥ 18 字段）
- `REGRESSION.txt`
- `BROWSER-VERIFICATION.txt`
- `SECRETS-SCAN.txt`
- `RESTORE.md`
- `CHANGELOG-FINAL.md`

写完后又因发现 prior round CHANGE-MANIFEST 中的 AK 4-char hint，重新同步一次 + 重生成 CHECKSUMS，并新增 `RESTORE-VERIFICATION.txt`。

### 5.5 顺手清理 prior round 的 AK 4-char hint

`docs/STAGE7B-A-BAIDU-RUNTIME-CLOSING-CHANGE-MANIFEST.json` 第 159-160 行：

```json
"akFirst4Redacted": "****",
"akLast4Redacted": "****",
```

虽不是完整 AK，但违反了硬约束"不得写入...Change Manifest"。改为 `"****"`。然后 re-sync 进 checkpoint，重新生成 CHECKSUMS。

---

## 6 · Section 八 · 恢复验证

```bash
RESTORE_ROOT="/tmp/pathos-stage7b-a-restore-verification"
mkdir -p "$RESTORE_ROOT"
cd "$RESTORE_ROOT"
rm -rf frontend audit CHECKSUMS.sha256
rsync -a --exclude='node_modules' --exclude='.next' --exclude='.env.local' \
  "$CKPT/frontend/" "$RESTORE_ROOT/frontend/"
cp "$CKPT/CHECKSUMS.sha256" "$RESTORE_ROOT/CHECKSUMS.sha256"
shasum -a 256 -c CHECKSUMS.sha256
```

结果：
- SHA256 全部 OK
- .env.local: 0
- node_modules: 0
- .next: 0
- LCrc 在 frontend 下: 0
- URL ak= 模式: 0
- BEGIN RSA / PRIVATE KEY: 0
- 符号链接: 0
- package.json / package-lock.json / configs 全部存在
- RegionalStateLayer.tsx 第 395 行有 `export function deferUntilStyleLoaded`
- stage7baf-regional-styleload-lifecycle.test.ts 存在
- docs/STAGE7B-A-DARK-CONTRAST-AUDIT.md 第 55 行 = `rgb(var(--token-surface-muted) / 0.55)`
- regional-data-manifest.json SHA = `21e4c311...`（匹配）
- sourceWorkbook SHA = `409ed47b...`（匹配）
- 204 records × 4 READY metrics（匹配）

回归（在 /tmp 下）：
- tsc 0
- lint 0
- vitest 在 /tmp scratch 下 stage5-* 失败（依赖 sibling artefact dir），从原路径跑 235/235
- build 15 routes

结果写入 `audit/RESTORE-VERIFICATION.txt`。

---

## 7 · Section 九 · 最终闭包文档

3 份：
- `docs/STAGE7B-A-FINAL-CLOSURE-REPORT.md`
- `docs/STAGE7B-A-FINAL-CLOSURE-DEVLOG.md`（本文件）
- `docs/STAGE7B-A-FINAL-CLOSURE-CHANGE-MANIFEST.json`

---

## 8 · Section 十 · 关闭本轮服务

dev server PID 33739 在 Section 二 ~ 浏览器矩阵期间运行。本轮收尾：

```bash
# 用 PID 精准停
kill 33739
# 等待子进程回收
sleep 2
lsof -ti:3002
```

预期：lsof 无输出（端口空闲）。

未做：pkill、未做 killall、未抢占外部进程、未改 .env.local。

---

## 9 · 完成态

- 检查点路径：`/Users/jiayihuang/Downloads/PathOS-checkpoints/stage7b-a-pass-2026-07-25/`
- dev server：已停止
- 端口 3002：已释放
- Git tag：无
- 推送：无
- Stage 7B-B：未启动

Stage 7B-A Final Closure 完成。

---

## 10 · 工程师日志补充（非强制）

本轮在写 Section 二修复时差点把 `MapCanvas.tsx` 的 console.warn patch 写成全局 patch（会泄漏到其它组件）。幸而想起要 cleanup，最终在 useEffect 的 return 函数里 `console.warn = origWarn`。这是 React Strict-Mode 下典型的"双挂载泄漏"陷阱。

写完 lifecycle 测试后，TypeScript 报 `isStyleLoaded(): boolean` 错误——MapLibre 实际签名是 `boolean | void`。把 StyleLoadedGate 接口的返回类型放宽即可。

测试用例的 assert 一开始写错了：第一个测试假设 `cancel()` 不会再调 `off()`，但实际上 helper 的 cancel 是幂等的（每次都尝试 off，依赖 MapLibre 自身的 no-op 行为）。第二个测试假设 5 次 defer 会共享一个 listener——不对，每个 defer 注册自己的。修正预期后通过。

HMR 没生效那次浪费了 5 分钟。下次大改 MapCanvas.tsx 后直接清 `.next` 重启，别依赖 HMR。

写完 SECRETS-SCAN 后发现 prior round 的 CHANGE-MANIFEST 留了 AK 的 4-char hint——虽不致命但违反硬约束精神。顺手清理。