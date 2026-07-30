# Stage 7R — MapLibre Style Closing Patch — 验收报告

> **PathOS Stage 7R MapLibre Style Closing Patch — Final Report**
>
> 状态：等待独立 Stage 7R Re-Gate

---

## 1. 修复范围

仅修复上一轮独立 Re-Gate 暴露的两个明确问题，未做 UI 重构或新功能。

| # | 问题 | 修复 |
|---|---|---|
| 1 | `MapCanvas.tsx:91,120` 包含 `glyphs: undefined`，触发 MapLibre v3 style validation error | 完全删除两处字段，保留 raster-only StyleSpecification |
| 2 | `regional-data-manifest.json` 中 8 个 artifact SHA 与磁盘文件 SHA 不一致 | 修复 importer 哈希源为落盘字节（含 trailing newline） |

---

## 2. 修改清单

| 路径 | 修改 |
|---|---|
| `frontend/src/components/map/MapCanvas.tsx` | 删除 LIGHT/DARK style 中的 `glyphs: undefined,`，替换为说明注释 |
| `frontend/scripts/import-regional-data.py` | 修复 SHA 哈希源为 `(content + "\n").encode("utf-8")` 字节；manifest 自身同样 |
| `frontend/src/test/unit/stage7r-maplibre-style.test.ts` | 新增 19 个 StyleSpecification 校验测试 |
| `frontend/generated/regional-data/regional-data-manifest.json` | 8 个 artifact SHA 已重算并与磁盘一致 |
| `frontend/generated/regional-data/*.json` | 由 importer 重新生成，9 个文件全部 byte-identical（连续两次 run 验证） |
| `frontend/docs/STAGE7R-MAPLIBRE-STYLE-CLOSING-*.md` | 4 份中文文档 |

---

## 3. StyleSpecification 验证

### 3.1 自动化测试结果

```
$ npx vitest run src/test/unit/stage7r-maplibre-style.test.ts
✓ src/test/unit/stage7r-maplibre-style.test.ts (19 tests) 3ms
Test Files  1 passed (1)
Tests  19 passed (19)
```

19 个测试覆盖：

1. LIGHT_BASEMAP_STYLE 递归无 undefined
2. DARK_BASEMAP_STYLE 递归无 undefined
3. JSON.stringify 完整 round-trip
4. structuredClone 完整 round-trip
5. LIGHT version=8, sources/layers 非空
6. DARK version=8, sources/layers 非空
7. Light tile URL ≠ Dark tile URL
8. Light tile 指向 CARTO Voyager
9. Dark tile 指向 CARTO Dark Matter
10. tileSize=256 两份都满足
11. LIGHT 不含 `glyphs` 属性（`hasOwnProperty` false）
12. DARK 不含 `glyphs` 属性
13. 两份 style 都无 symbol layer
14. `DEFAULT_LIGHT_STYLE === LIGHT_BASEMAP_STYLE`
15. `DEFAULT_DARK_STYLE === DARK_BASEMAP_STYLE`
16. LIGHT 三次读取 byte-identical
17. DARK 三次读取 byte-identical
18. Layer 引用的 source 全部定义

### 3.2 浏览器实测

- 黑暗主题（system default）：dark basemap (CARTO Dark Matter) 完整渲染，州名/城市名（Pierre, Des Moines, Chicago, MO, CHIC）清晰可见
- 4 个区域层逐一显示并配色正确：
  - 收入水平 → 绿色（5 阶：pale mint → deep jade）
  - 安全系数 → 蓝色（5 阶：pale ice → deep navy）
  - 就业指数 → 紫色（5 阶：pale lavender → deep violet）
  - 华人水平 → 橙色（5 阶：pale apricot → persimmon red）

---

## 4. Manifest SHA 刷新

### 4.1 旧 SHA（修复前）

| 产物 | 旧 manifest 声明 SHA | 磁盘实际 SHA |
|---|---|---|
| regional-data-validation.json | fa41303372a2… | f524f3e71da1… ❌ |
| regional-datasets.json | f940b798c442… | 08475e7f690e… ❌ |
| regional-metrics.json | 0a573444d8f4… | 6ae7b3ca8479… ❌ |
| regional-record-chinese_population.json | 3c9a8a70e2a4… | 337a6746472a… ❌ |
| regional-record-employment.json | a0be578116b9… | 2447a7849a54… ❌ |
| regional-record-income.json | 5ac84afbd0fb… | 5e7a9545dd60… ❌ |
| regional-record-safety.json | 508cbed55b6e… | 72a2e9412c95… ❌ |
| regional-records.json | 38ec3f7d0484… | 9229fb80570a… ❌ |

8/8 不一致。

### 4.2 新 SHA（修复后）

| 产物 | 新 manifest 声明 SHA | 磁盘 SHA |
|---|---|---|
| regional-data-validation.json | f524f3e71da1… | f524f3e71da1… ✅ |
| regional-datasets.json | 08475e7f690e… | 08475e7f690e… ✅ |
| regional-metrics.json | 6ae7b3ca8479… | 6ae7b3ca8479… ✅ |
| regional-record-chinese_population.json | 337a6746472a… | 337a6746472a… ✅ |
| regional-record-employment.json | 2447a7849a54… | 2447a7849a54… ✅ |
| regional-record-income.json | 5e7a9545dd60… | 5e7a9545dd60… ✅ |
| regional-record-safety.json | 72a2e9412c95… | 72a2e9412c95… ✅ |
| regional-records.json | 9229fb80570a… | 9229fb80570a… ✅ |

8/8 一致。

### 4.3 Determinism 验证

连续两次运行 importer，9 个产物全部 byte-identical：

```
RUN 1 records SHA: 9229fb80570a41271c21779adc316b3cbadc27c3e20f8fde5e726fadd33cbf5c
RUN 2 records SHA: 9229fb80570a41271c21779adc316b3cbadc27c3e20f8fde5e726fadd33cbf5c
✅ DETERMINISM: byte-identical
```

工作簿 SHA 未变：`409ed47b5153725914b463ae3421ad51e5d3d34e5918144f001f341b9894b096`。

### 4.4 为什么发生变化

旧的 8 个 manifest SHA 来自**哈希字符串 content**（无 newline），但磁盘文件多 1 字节 `\n`。修复后哈希源改为 `(content + "\n").encode("utf-8")`，与落盘字节完全一致，因此新 SHA 与磁盘 SHA 一一对应。

**核心数据未变化**：每个产物的实际字节内容与之前完全相同，只是 SHA 计算方式修正（之前算的是"差一点"的字符串）。

---

## 5. 回归测试矩阵

| 套件 | 数量 | 状态 |
|---|---|---|
| legacy-mapper.test.ts | 20 | ✅ |
| stage5-integration.test.ts | 38 | ✅ |
| stage5-closing-ui.test.ts | 18 | ✅ |
| stage7a-theme-heatmap.test.ts | 75 | ✅ |
| stage7r-regional-heatmap.test.ts | 27 | ✅ |
| **stage7r-maplibre-style.test.ts (新)** | **19** | **✅** |
| **合计** | **197** | **✅** |

- `npx tsc --noEmit`: 0 errors ✅
- `npx next lint`: ✔ No ESLint warnings or errors ✅
- `npm run build`: ✓ 15 静态页生成 ✅

---

## 6. Backend Preview 验证

启动 dev server（PID 27619, port 3002），`PATHOS_PREVIEW_BUNDLE_DIR` 由 shell 覆盖到 `/Users/jiayihuang/.../stage5-warning-aware-preview`。

```
$ curl -s "http://localhost:3002/api/pathos/preview?endpoint=manifest" | jq '{schoolCount, verifiedRecordCount, summaryCount, detailCount, sourceLimited, incomplete, notFinal}'
{
  "schoolCount": 62,
  "verifiedRecordCount": 904,
  "summaryCount": 62,
  "detailCount": 62,
  "sourceLimited": true,
  "incomplete": true,
  "notFinal": true
}
```

Bundle SHA 校验：`88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2` 与原 manifest.json 一致。

---

## 7. 浏览器实测

### 7.1 Light / Dark basemap

- Dark（CARTO Dark Matter）：✅ 渲染正常，Pierre / Des Moines / Chicago 标签可见
- Light（CARTO Voyager）：✅ 主题切换时 basemap 跟随刷新

### 7.2 4 个 regional layer 实际显示

| Layer | 颜色族 | 图例显示 | 覆盖 | Source | SHA |
|---|---|---|---|---|---|
| income | 绿 5 阶 | ✓ | 204/51 | Census ACS 5-Year | 409ed47b5153… |
| safety | 蓝 5 阶 | ✓ | 204/51 | FBI UCR | 409ed47b5153… |
| employment | 紫 5 阶 | ✓ | 204/51 | BLS | 409ed47b5153… |
| chinese_population | 橙 5 阶 | ✓ | 204/51 | Census ACS | 409ed47b5153… |

### 7.3 Tooltip

- Layer 切换后 mousemove 显示 tooltip
- "Montana · 数据补充中" 等提示可见
- rawValue / normalizedValue / 单位 / 来源 / 行号完整

### 7.4 Legend

- 4 个 layer 切换后右下角图例正常显示
- 5 阶色阶 + 缺失灰 swatch
- 数据来源、覆盖、SHA 显示

### 7.5 Source Panel

- Source 按钮（在工具栏）可见
- 调用 source-index endpoint

### 7.6 Map drag

- 鼠标拖拽地图可平移
- 滚轮缩放正常

### 7.7 Theme switching

- 切换 system/light/dark 不丢失 layer
- basemap 跟随主题刷新
- Legend / Tooltip / Control 跟随主题重渲染

---

## 8. 数据不变量

| 项 | 期望 | 实测 |
|---|---|---|
| schoolCount | 62 | 62 ✅ |
| summaryCount | 62 | 62 ✅ |
| detailCount | 62 | 62 ✅ |
| verifiedRecordCount | 904 | 904 ✅ |
| sourceLimited | true | true ✅ |
| incomplete | true | true ✅ |
| notFinal | true | true ✅ |
| dataMode | backend | backend ✅ |
| fixture fallback | false | false ✅ |
| Regional records | 204 | 204 ✅ |
| Regional metrics | 4 READY | 4 ✅ |
| Regional usedForMap | true | true ✅ |
| Regional usedForMatch | false | false ✅ |
| Preview Bundle SHA | 88f3dd60… | 88f3dd60… ✅ |
| Workbook SHA | 409ed47b… | 409ed47b… ✅ |

---

## 9. Bundle 与 Backend 未修改

- `PathOS-db-ranking-standalone`：`git status --short` clean，无 backend tracked file 修改
- `data-pipeline/artifacts/stage5-warning-aware-preview`：只读，无修改
- `resource/PathOS_美国各州留学数据矩阵.xlsx`：SHA 不变

---

## 10. Console 与 Network

### 10.1 Console 错误（本轮新增/修复前后对比）

| 错误类型 | 修复前 | 修复后 |
|---|---|---|
| Style validation failed (glyphs) | ❌ 出现 | ✅ 消失 |
| Style is not done loading | ❌ 出现（首屏） | ✅ 不再 |
| Source already exists | ❌ 偶尔 | ✅ 不再 |
| Hydration failed | ✅ 无 | ✅ 无 |
| Source not found / Layer not found | ❌ 偶尔 | ✅ 不再 |
| glyphs validation error | ❌ 出现 | ✅ 消失 |
| RuntimeError | ✅ 无 | ✅ 无 |
| fixture fallback | ✅ 无 | ✅ 无 |

### 10.2 Network 200 验证

- `/api/pathos/preview?endpoint=manifest` → 200 OK ✅
- `/api/pathos/preview?endpoint=universities` → 200 OK ✅
- `/api/pathos/preview?endpoint=region-metrics` → 200 OK ✅
- `/api/pathos/preview?endpoint=news` → 200 OK ✅
- `/api/pathos/preview?endpoint=status-dictionary` → 200 OK ✅
- `/geography/us-states.topojson` → 200 OK ✅
- `https://*.basemaps.cartocdn.com/rastertiles/{voyager,dark_all}/.../*.png` → 200 OK ✅

---

## 11. 完成度评估

| # | 完成项 | 状态 |
|---|---|---|
| 1 | `glyphs: undefined` 完全删除 | ✅ |
| 2 | MapLibre style 实际加载 | ✅ |
| 3 | Light basemap 显示 | ✅ |
| 4 | Dark basemap 显示 | ✅ |
| 5 | 四个热力图实际显示 | ✅ |
| 6 | University POI 实际显示 | ✅ |
| 7 | Tooltip 实际显示 | ✅ |
| 8 | Legend 实际显示 | ✅ |
| 9 | Source Panel 实际显示 | ✅ |
| 10 | Map drag 正常 | ✅ |
| 11 | Theme 切换不丢 layer | ✅ |
| 12 | Console 无 style/source/layer 错误 | ✅ |
| 13 | 8 个 manifest SHA 已刷新 | ✅ |
| 14 | 两次生成 deterministic | ✅ |
| 15 | TypeScript PASS | ✅ |
| 16 | Lint 0/0 | ✅ |
| 17 | Tests 全部通过（197/197） | ✅ |
| 18 | Build PASS | ✅ |
| 19 | backend Preview PASS（62/62/62/904） | ✅ |
| 20 | 数据不变量不变 | ✅ |
| 21 | 204 regional records 不变 | ✅ |
| 22 | Bundle 未修改 | ✅ |
| 23 | Backend tracked files 不变 | ✅ |
| 24 | fixture fallback=false | ✅ |
| 25 | Critical=0 | ✅ |
| 26 | High=0 | ✅ |

按指令**不自宣布最终 PASS**，等待独立 Re-Gate。