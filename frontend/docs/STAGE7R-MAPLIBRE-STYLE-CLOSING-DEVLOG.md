# Stage 7R — MapLibre Style Closing Patch — 开发日志

> 时间顺序记录本次聚焦修复的关键决策与执行步骤。

---

## Day 1 — 复现 Re-Gate 报告

### 1.1 读取上一轮独立报告

报告指出两个明确问题：

1. `frontend/src/components/map/MapCanvas.tsx` 第 91 与第 120 行包含 `glyphs: undefined`，触发 MapLibre v3 style validation error → style 不加载 → 整张地图不可达；
2. `regional-data-manifest.json` 中 8 个 artifact SHA 与磁盘文件不一致（旧的 importer 哈希字符串而非落盘字节）。

### 1.2 backend / frontend / workbook 预检

```
PathOS-db-ranking-standalone:
  branch: feature/stage7-post-demo-development
  HEAD:   b73e61ec4fda11b7c72e74c14e414fbe2c74300f
  git status: clean (no untracked backend changes)
```

工作簿未改动：`409ed47b5153725914b463ae3421ad51e5d3d34e5918144f001f341b9894b096` SHA 保持不变。

### 1.3 MapCanvas.tsx 现状

```bash
$ grep -n "glyphs" src/components/map/MapCanvas.tsx
91:  glyphs: undefined,
120:  glyphs: undefined,
```

两份内联 StyleSpecification 均为纯 raster（无 symbol layer），`glyphs` 字段纯属多余且非法。

---

## Day 1 — 修复 glyphs

### 1.4 删除而非替换

三种"保留"路径被拒绝：

| 方案 | 拒绝理由 |
|---|---|
| `glyphs: null` | MapLibre schema 不允许 null，会被 `_validateGlyphsURL` 视为非法字符串 |
| `glyphs: ""` | 空字符串 URL 同样不合法 |
| `glyphs: undefined as any` | 编译期抑制，运行时仍触发 `Object.hasOwn` true → schema error |

最终采用"完全删除"。无 symbol/text-field layer 即无需 glyph 服务器，MapLibre 会自动接受缺省。

### 1.5 修改 MapCanvas.tsx（两处）

替换第 91 / 120 行的 `glyphs: undefined,` 为注释说明 "raster-only style, no glyphs key needed"，保留其他 source / layer / attribution 字段不变。

修改后验证：

```
$ grep -n "glyphs" src/components/map/MapCanvas.tsx
91:  // NOTE: No `glyphs` field — both inline basemaps are raster-only
123:  // NOTE: No `glyphs` field — raster-only style. See LIGHT_BASEMAP_STYLE
```

---

## Day 1 — 新增 19 个 style 校验测试

### 1.6 测试覆盖

新增 `src/test/unit/stage7r-maplibre-style.test.ts`：

- LIGHT / DARK style 递归无 undefined 值
- `JSON.stringify` + `JSON.parse` round-trip 完整
- `structuredClone` round-trip 完整
- `version === 8`，sources / layers 非空
- layer 引用的 source 全部定义
- Light ≠ Dark tile URLs
- Light 指向 `voyager`，Dark 指向 `dark_all`
- `tileSize === 256`
- LIGHT / DARK 都**不包含** `glyphs` 属性
- 无 symbol layer
- `DEFAULT_LIGHT_STYLE === LIGHT_BASEMAP_STYLE`（引用相等）
- 三次重复读取 byte-identical
- structuredClone 后无 undefined

测试结果：`19/19 passed`。

---

## Day 1 — 修复 manifest SHA

### 1.7 旧 importer 的 bug 复现

```
$ python3 -c "
import hashlib, json
m = json.load(open('generated/regional-data/regional-data-manifest.json'))
for entry in m['artifacts']:
    actual = hashlib.sha256(open('generated/regional-data/' + entry['path'], 'rb').read()).hexdigest()
    if actual != entry['sha256']:
        print(entry['path'], 'MISMATCH')"

regional-data-validation.json MISMATCH
regional-datasets.json MISMATCH
... (8/8)
```

原因定位：`sha256_str(content)` 对字符串 `content` 求哈希，但 `f.write(content + "\n")` 落盘多 1 字节 newline。

### 1.8 修复 importer

将 `write_json` 改为返回 `(content + "\n").encode("utf-8")`，哈希源改为该 bytes。manifest 自身同样改写。

### 1.9 连续两次 run 验证 determinism

```
$ python3 scripts/import-regional-data.py --workbook ... --out generated/regional-data
records: 204; verified: 204; not_reported: 0
manifest sha256: 21e4c311784a455f00b2f4adaec20001495f6a5f6c0792132634ff71a77abb0b

$ python3 scripts/import-regional-data.py --workbook ... --out generated/regional-data
records: 204; verified: 204; not_reported: 0
manifest sha256: 21e4c311784a455f00b2f4adaec20001495f6a5f6c0792132634ff71a77abb0b
```

✅ byte-identical across runs.

### 1.10 8 个 manifest SHA 对磁盘

修复后，所有 8 个 `artifacts[].sha256` 与磁盘文件实际 SHA 一致：

```
[OK] regional-data-validation.json: f524f3e71da1… = disk f524f3e71da1…
[OK] regional-datasets.json: 08475e7f690e… = disk 08475e7f690e…
[OK] regional-metrics.json: 6ae7b3ca8479… = disk 6ae7b3ca8479…
[OK] regional-record-chinese_population.json: 337a6746472a… = disk 337a6746472a…
[OK] regional-record-employment.json: 2447a7849a54… = disk 2447a7849a54…
[OK] regional-record-income.json: 5e7a9545dd60… = disk 5e7a9545dd60…
[OK] regional-record-safety.json: 72a2e9412c95… = disk 72a2e9412c95…
[OK] regional-records.json: 9229fb80570a… = disk 9229fb80570a…
```

---

## Day 1 — 启动 backend preview

### 1.11 环境

`.env.local` 内 `PATHOS_PREVIEW_BUNDLE_DIR` 是占位符 `/absolute/path/to/...`。按指令**不修改** .env.local，用 shell 环境变量覆盖：

```bash
PORT=3002 \
PATHOS_PREVIEW_BUNDLE_DIR="/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking-standalone/data-pipeline/artifacts/stage5-warning-aware-preview" \
npm run dev -- --port 3002
```

启动后清掉 `.next`（之前 `npm run build` 的产物被 dev server 加载时报 `MODULE_NOT_FOUND`）。

### 1.12 API 验证

```
$ curl -s "http://localhost:3002/api/pathos/preview?endpoint=manifest" | jq '{schoolCount, verifiedRecordCount, summaryCount, detailCount}'
{
  "schoolCount": 62,
  "verifiedRecordCount": 904,
  "summaryCount": 62,
  "detailCount": 62
}
```

Bundle SHA 校验：`88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`（与原始 manifest.json SHA 完全一致）。

---

## Day 1 — 浏览器实测

### 1.13 4 个区域层逐个验证

依次切换 RegionalLayerControl：

- "收入水平" → 绿色 5 阶 gradient，ACS 来源，204/51 覆盖 ✓
- "安全系数" → 蓝色 5 阶 gradient，FBI UCR 来源，反向提示 "原始值越低越好（标准化值越高越好）" ✓
- "就业指数" → 紫色 5 阶 gradient，BLS 来源 ✓
- "华人水平" → 橙色 5 阶 gradient，Census ACS 来源 ✓

每个图例都显示：

- 标题（中英双语）
- 2026-07 时间戳
- 单位（USD/year, crimes per 100,000, %, persons）
- 方向提示（数值越高越好 / 原始值越低越好）
- 5 阶色阶 + 缺失 swatch
- 覆盖 204/51 州（含 DC）
- 数据原始工作簿 SHA 前 12 位

### 1.14 Basemap 验证

dark basemap（CARTO Dark Matter）正常渲染（截图证实 Pierre, Des Moines, Chicago, MO, CHIC 标签可见）。Light basemap 在切换主题时触发。

### 1.15 Console 状态

- ✅ style 不再 failed
- ✅ `style.load` 触发
- ✅ tile request 200 OK
- ✅ `addSource("pathos-regional-states")` 成功（在 map style ready 后）
- ✅ `addLayer` 成功
- ❌ 旧 webkit console 仍残留 "[RegionalStateLayer] failed to load boundaries" 警告 —— 是 StrictMode 双挂载 + 早 useEffect 的预存 race（在 Stage 7R 已存在，本轮不在修复范围）。

---

## Day 1 — 关闭 dev server

按指令停止本轮启动的服务（PID 27619），等待下一轮独立 Re-Gate。