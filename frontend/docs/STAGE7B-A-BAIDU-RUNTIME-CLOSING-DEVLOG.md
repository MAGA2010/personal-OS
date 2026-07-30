# Stage 7B-A — Baidu Runtime Closing DEVLOG（运行时补全 · 开发日志）

> 日期：2026-07-25
> 视角：每一项修改都包含「Why / What / Risk」三段。读者：独立 Re-Gate 工程师。

---

## 21:55 · 收到本轮指令

四个阻塞性证据缺口：
1. 上一轮报告 "AK BLOCKED" 但 `.env.local` 实际有 AK
2. 百度 Polygon 是 no-op hook
3. Browser Matrix 主要用 curl
4. 14 → 15 routes 差异未解释

## 22:00 · Section 二 · AK 安全确认

**Why**：纠正上一轮判断（"BLOCKED" 实际是错误）。

```bash
cd "/Users/jiayihuang/Downloads/PathOS合并/PathOS-main/frontend"
pwd && test -f .env.local && test -s .env.local
# .env.local exists · non-empty

grep -E '^[A-Z0-9_]+=' .env.local | cut -d= -f1
# 7 个变量：PATHOS_DATA_MODE / PATHOS_PREVIEW_BUNDLE_DIR / PATHOS_BACKEND_BASE_URL
# / PATHOS_BACKEND_TIMEOUT_MS / NEXT_PUBLIC_PATHOS_API_BASE_URL
# / NEXT_PUBLIC_BAIDU_MAP_AK / NEXT_PUBLIC_PATHOS_MAP_PROVIDER
```

安全脚本输出（值已脱敏）：
- `env_file_exists: True`
- `baidu_ak_configured: True` ← 关键纠正
- `baidu_ak_length_valid: True`
- `ak_length: 32`（合法）
- `map_provider: baidu`

**What**：确认上一轮 "BLOCKED" 报告错误。AK 已配置。

**Risk**：上一轮的 6 份文档（PLAN/DEVLOG/REPORT/DARK-CONTRAST-AUDIT/MAP-PROVIDER-COMPARISON/CHANGE-MANIFEST.json）均基于错误前提。本份 CLOSING 报告替代其结论，但保留它们作为历史记录。

## 22:15 · Section 三 · Next.js env 加载

**Why**：确认 Next.js dev/build 实际读取 `.env.local`。

```bash
# 清理本轮自身产生的旧 .next
test -d .next && rm -rf .next  # 移除 157M 缓存

# 启动 dev server
nohup npm run dev -- --port 3002 > /tmp/dev3002.log 2>&1 &
# → PID 30175
```

**What**：dev server 在 PID 30175 / 30194（next-server）启动；端口 3002 空闲后绑定；HTTP 200 在 1 秒内 ready。

**Build 输出**：
```
- Environments: .env.local
✓ Generating static pages (15/15)
```

**Risk**：低。端口 3002 之前 Stage 7R 已使用过；本轮确认其空闲。

## 22:25 · Section 四 · 百度 Loader 真实加载

**Why**：确认 AK 在主机网络上可授权百度 JSAPI。

```bash
curl -s -w "status=%{http_code} time=%{time_total}\n" --max-time 30 \
  "https://api.map.baidu.com/api?v=3.0&type=webgl&ak=ak%3D%5BREDACTED%5D" \
  -o /tmp/b.txt
# status=200 time=0.110s

curl -s -w "status=%{http_code} time=%{time_total} size=%{size_download}\n" \
  --max-time 60 \
  "https://api.map.baidu.com/getscript?type=webgl&v=1.0&ak=ak%3D%5BREDACTED%5D..." \
  -o /tmp/baidu_gl.js
# status=200 time=0.395s size=1,179,484 bytes
```

**BMapGL 授权字段**（从 getscript bundle 提取）：
```json
{
  "business": 0,
  "unauth": 0,            ← AK 已授权
  "popup_code": "",
  "popup_block_time": 60,
  "popup_timestamp": 1784989417,
  "watermark_ratio": 0
}
```

**BMapGL 类存在**（grep bundle）：
- `BMapGL.Map` ✅
- `BMapGL.Marker` ✅
- `BMapGL.Point` ✅
- `BMapGL.Polygon` ✅
- `BMapGL.CopyrightControl` ✅
- `BMapGL.NavigationControl` ✅

**What**：百度 JSAPI 在主机上完全可加载。

**Risk**：仅主机层可达；浏览器层（preview sandbox）网络隔离，无法真实浏览器渲染验证。

## 22:35 · Section 九 · 真实 Dark contrast 复核（新发现 + 修复）

**Why**：上一轮报告基于"token 表 + normalized values"声称 dark contrast 完成。本轮用真实 `getComputedStyle` 复核发现 **nav active state 仍不可见**。

**真实测量**（preview sandbox `/map`）：
```js
nav a[href="/map"] (active state):
  bg: rgba(244, 240, 232, 0.08)  ← 8% 奶白在炭黑上 = 看不见
  fg: rgb(244, 240, 232)          ← 奶白文字
  ratio: 1.00:1 ❌
```

**根因**：Tailwind 调色板在 `.dark` 下 `--token-ink: 244 240 232`（cream）。`bg-ink/8` 编译成 `rgba(244,240,232,0.08)` —— 奶白底配奶白字，1:1 不可见。

**修复**（`src/app/globals.css` 第 259-261 行替换）：
```css
.dark .bg-ink\/8 {
  background-color: rgb(var(--token-surface-muted) / 0.55) !important;
}
.dark .bg-ink\/10 {
  background-color: rgb(var(--token-surface-muted) / 0.65) !important;
}
```

**修复后**（同一 nav item）：
```js
bg: rgba(30, 36, 42, 0.55)   ← 暗灰（surface-muted）在炭黑上 = 可见凹陷
fg: rgb(244, 240, 232)
ratio: 13.78:1 ✅
```

**截图确认**：preview sandbox `/map` dark mode 下，header 中"留学地图"项现在清晰可见。

**Risk**：仅影响 `bg-ink/8` 和 `bg-ink/10`；其他 token（bg-paper/bg-panel/bg-white/N）已有覆盖。

## 22:45 · Section 八/十 · 图例去重 + routes 差异

**Why**：验证上一轮的两项声明。

**图例去重**：
```bash
grep -c 'from "./MapLegend"' src/components/map/MapShell.tsx
# 0  ← import 已删除
grep -c '<MapLegend' src/components/map/MapShell.tsx
# 0  ← JSX 已删除
grep -c 'from "./regional/RegionalLegend"' src/components/map/MapShell.tsx
# 1  ← RegionalLegend 是唯一权威
```

**Routes 差异**：
```bash
find src/app -type f \( -name 'page.tsx' -o -name 'route.ts' \) | wc -l
# 15  ← 实际 15 routes

npm run build  # 输出确认 15 routes
```

**What**：图例去重真实生效；routes 实际从一开始就 15 个（不是 14）。上一轮 14 报告是统计错误。

**Risk**：无。

## 22:55 · Section 五/六/七 · 百度真实渲染 / Polygon / 交互

**Why**：尝试按 directive 完成百度真实 runtime。

**结论**：**BLOCKED**。

**根因 1**：`MapShell.tsx:635` 直接渲染 `<MapCanvas>`（MapLibre-backed），从未经过 `<MapProviderHost>`。`NEXT_PUBLIC_PATHOS_MAP_PROVIDER=baidu` env 在 shell 层被读取但**未被 MapShell 使用**。

**根因 2**：BMapGL 适配器是 contract stub（`addUniversityMarkers` / `setRegionalFill` / `setSelectedRegion` / `setHoveredRegion` 全是 no-op）。

**根因 3**：完整实现需要：
- 替换 MapCanvas 为 BMapGL.Map 实例化
- 51 个州 polygon 用 BMapGL.Polygon 渲染（接收 BD09 坐标）
- WGS84 → BD09 转换（百度海外 convertor 服务依赖）
- Marker / Hover / Click / Theme 全部切换
- 监听器清理

相当于 Stage 7B-B 整个 round 的工作量。

**What**：诚实记录 BLOCKED，附精确证据（CDN 可达 + AK 授权 + BMapGL 类存在，但 MapShell 未接入）。

**Risk**：与 directive 的 Section 十五 escape hatch 一致 —— "MAPLIBRE PATH READY · BAIDU PROVIDER BLOCKED"。

## 23:05 · Section 十三 · 数据不变量验证

**Why**：保持 62/62/62/904 + 204/51/4/0。

```bash
curl "http://localhost:3002/api/pathos/preview?endpoint=universities" | jq 'length'
# 62 ✅

python3 -c "
import json
with open('frontend/generated/regional-data/regional-records.json') as f:
    d = json.load(f)
recs = d['records']
print('total:', len(recs))                                    # 204
print('metrics:', len(set(r['metricId'] for r in recs)))      # 4
print('jurisdictions:', len(set(r['geoId'] for r in recs)))   # 51
print('duplicates:', len(recs) - len(set((r['metricId'], r['geoId']) for r in recs)))  # 0
"

python3 -c "
import json
with open('frontend/generated/regional-data/regional-metrics.json') as f:
    d = json.load(f)
for m in d['metrics']:
    print(m['metricId'], 'usedForMap:', m['usedForMap'], 'usedForMatch:', m['usedForMatch'])
"
# income usedForMap: True usedForMatch: False
# safety usedForMap: True usedForMatch: False
# employment usedForMap: True usedForMatch: False
# chinese_population usedForMap: True usedForMatch: False
```

**What**：全部不变量保持。

**Risk**：无。bundle / backend / 原始工作簿未触动。

## 23:15 · Section 十四 · 全量回归

```bash
npx tsc --noEmit    # 0 errors
npm run lint        # 0 warnings
npm test            # 220/220 passed (7 files, 336ms)
npm run build       # success (15 routes)
```

**What**：所有自动化回归通过。

**Risk**：无。

## 23:25 · Section 十一/十二 · 真实 Browser Matrix + Console

**Preview sandbox**（`preview_start pathos-frontend`）：

| Route | Hydrated | Title |
|-------|----------|-------|
| `/` | ✅ | PathOS — 面向中国家庭的留学选校数据平台 |
| `/map` | ✅ | 留学地图 \| PathOS |
| `/calculator` | ✅ | PathOS |
| `/assessment` | ✅ | PathOS |
| `/match` | ✅ | PathOS |
| `/portfolio` | ✅ | PathOS |
| `/news` | ✅ | PathOS |

**Console errors**：
```
[RegionalStateLayer] failed to load boundaries:
  Error: Style is not done loading.
  at RegionalStateLayer.tsx:105
```

- Medium 级
- pre-existing（Stage 7R 时期已有 — 未在 changelog 中作为修复）
- 不阻塞 Re-Gate（第二次 retry 成功，用户无感知）

**Network 异常**：无关键 404 / 循环失败 / AK 泄漏。

## 23:35 · Section 十六 · 3 份结案文档

- `docs/STAGE7B-A-BAIDU-RUNTIME-CLOSING-REPORT.md`
- `docs/STAGE7B-A-BAIDU-RUNTIME-CLOSING-DEVLOG.md`（本份）
- `docs/STAGE7B-A-BAIDU-RUNTIME-CLOSING-CHANGE-MANIFEST.json`

## 23:45 · 停止本轮服务

```bash
kill 30175 30194   # dev server + next-server
lsof -nP -iTCP:3002 -sTCP:LISTEN  # 端口 3002 释放
```

**What**：停止本轮启动的服务。端口 3002 释放。

**Risk**：无。

## 23:55 · 等待独立 Re-Gate

- 不自我宣告 PASS
- 不创建 tag
- 不 push
- 等独立 Re-Gate 工程师给出最终判定

---

## 关键决策回顾

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 默认 Provider | 维持 maplibre | Baidu MapShell 未接入 |
| Baidu 真实渲染 | BLOCKED · 文档化 | MapProviderHost contract stub |
| Dark contrast | 真实修复 nav active | 上一轮遗漏 1.00:1 关键问题 |
| Routes 差异 | 实际为 15（无误） | find + build 双重确认 |
| 数据不变量 | 全部保持 | bundle / backend / 原始工作簿未触动 |
| 状态判定 | MAPLIBRE PATH READY · BAIDU PROVIDER BLOCKED | 符合 directive Section 十五 escape hatch |
