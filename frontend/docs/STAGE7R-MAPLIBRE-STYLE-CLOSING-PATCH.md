# Stage 7R — MapLibre Style Closing Patch

> **聚焦修复任务**
>
> 范围：仅修复上一轮独立 Re-Gate 暴露的两个明确问题
>
> 1. MapCanvas.tsx 第 91 与第 120 行的 `glyphs: undefined` —— 导致 MapLibre v3 style 永不加载；
> 2. `regional-data-manifest.json` 中 8 个 artifact SHA 过期 —— 旧 importer 哈希字符串而未哈希落盘字节。
>
> 不进行 UI 重构、新数据采集或 Stage 7B。

---

## 1. 根因分析

### 1.1 glyphs: undefined

`LIGHT_BASEMAP_STYLE` 与 `DARK_BASEMAP_STYLE` 均为**纯 raster** 内联 StyleSpecification —— 仅包含 `background` 层 + `raster` 源 + CARTO tile URLs。它们**没有**任何 `symbol` / `text-field` layer，因此**不需要 glyph 服务器**。

但旧代码在 `layers:` 数组后追加了：

```ts
layers: [
  { id: "background", type: "background", paint: { "background-color": "#f6f3ed" } },
  { id: "carto-light", type: "raster", source: "carto-light" },
],
glyphs: undefined,   // ← 显式 undefined,违反 StyleSpecification
```

MapLibre v3 内部对 StyleSpecification 走严格 schema 校验。`glyphs: undefined` 等价于"`glyphs` 字段存在但值未定义"，触发 `_checkLoaded` 中的 style validation error，style 进入"failed"状态后 `style.load` 事件永不触发 → `addSource`、`addLayer`、`queryRenderedFeatures` 全部失败 → 整个 map 表现为"静默死亡"。

受影响的下游功能（全部不可达）：

- Light basemap
- Dark basemap
- 4 个 regional choropleth layers
- University POI markers
- Regional hover tooltip
- Source panel
- Map drag/wheel-zoom
- 主题切换视觉

### 1.2 Manifest SHA 过期

旧 `import-regional-data.py`：

```python
files["regional-records.json"] = json.dumps(...)  # 不含 \n
artifact_hashes[name] = sha256_str(content)        # 哈希 content（无 \n）
...
with open(full, "w", encoding="utf-8") as f:
    f.write(content + "\n")                       # 落盘字节 = content + "\n"
```

**写入磁盘的是 `content + "\n"`，但 manifest 记录的是 `sha256(content)`**，两者不一致。审计员检查 manifest SHA 时会发现磁盘文件 SHA 与声明不符。

---

## 2. 修复

### 2.1 删除 glyphs 字段

文件：`frontend/src/components/map/MapCanvas.tsx`

修改前：

```ts
const LIGHT_BASEMAP_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: { "carto-light": { type: "raster", tiles: [...], tileSize: 256, attribution: "..." } },
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#f6f3ed" } },
    { id: "carto-light", type: "raster", source: "carto-light" },
  ],
  glyphs: undefined,   // ← 删除
};

const DARK_BASEMAP_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: { "carto-dark": { type: "raster", tiles: [...], tileSize: 256, attribution: "..." } },
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#181e24" } },
    { id: "carto-dark", type: "raster", source: "carto-dark" },
  ],
  glyphs: undefined,   // ← 删除
};
```

修改后：

```ts
const LIGHT_BASEMAP_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: { "carto-light": { type: "raster", tiles: [...], tileSize: 256, attribution: "..." } },
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#f6f3ed" } },
    { id: "carto-light", type: "raster", source: "carto-light" },
  ],
  // NOTE: No `glyphs` field — both inline basemaps are raster-only
  // (background + raster source). MapLibre v3 rejects styles that declare
  // any property as explicit `undefined`; omitting the key entirely is
  // the canonical fix when no symbol/text-field layer is present.
};

const DARK_BASEMAP_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: { "carto-dark": { type: "raster", tiles: [...], tileSize: 256, attribution: "..." } },
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#181e24" } },
    { id: "carto-dark", type: "raster", source: "carto-dark" },
  ],
  // NOTE: No `glyphs` field — raster-only style. See LIGHT_BASEMAP_STYLE
  // for the rationale on omitting the key entirely.
};
```

**完全删除字段**，不替换为 `null` / `""` / `undefined as any` / 类型断言。MapLibre 在没有 symbol layer 时本身就不需要该字段。

### 2.2 修复 manifest SHA 哈希源

文件：`frontend/scripts/import-regional-data.py`

修改前（artifact 哈希）：

```python
for name, content in files.items():
    full = os.path.join(out_dir, name)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content + "\n")
    artifact_hashes[name] = sha256_str(content)   # ← 错误：哈希无 \n 的 content
```

修改后：

```python
for name, content in files.items():
    bytes_on_disk = (content + "\n").encode("utf-8")   # ← 落盘字节
    full = os.path.join(out_dir, name)
    with open(full, "wb") as f:
        f.write(bytes_on_disk)
    artifact_hashes[name] = hashlib.sha256(bytes_on_disk).hexdigest()   # ← 哈希真实落盘字节
```

manifest 写入同样改为哈希落盘字节：

```python
manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
manifest_bytes = manifest_text.encode("utf-8")
with open(os.path.join(out_dir, "regional-data-manifest.json"), "wb") as f:
    f.write(manifest_bytes)
print(f"manifest sha256: {hashlib.sha256(manifest_bytes).hexdigest()}")
```

---

## 3. 验收点

- 两份 StyleSpecification 完全无 `undefined` 值（递归检查）；
- 两份 style 的 `glyphs` 字段完全不存在（`hasOwnProperty` 返回 false）；
- tile URL 不同，Light 指向 Voyager，Dark 指向 Dark Matter；
- 8 个 manifest SHA 与磁盘文件 SHA 一一匹配；
- 连续两次 import 产出 byte-identical 9 个文件；
- TypeScript / ESLint / vitest / build 全清；
- 浏览器实测：4 个 regional layer（绿/蓝/紫/橙）+ basemap + tooltip + legend 全部显示。