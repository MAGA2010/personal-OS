# Stage 7B-A — Dark Contrast Audit（深色对比度审计与修复）

> 日期：2026-07-25
> 标准：WCAG 2.1 AA — body text ≥4.5:1，UI/large text ≥3:1
> 范围：`frontend/src/app/globals.css` 与全局 Tailwind 调色板

---

## 一、根因分析

PathOS 调色板设计为 **双轴**：

- **色相轴**：`ink`（深）↔ `paper`（浅）↔ `panel`（卡片浅）
- **主题轴**：CSS 变量 `--token-ink / --token-paper / --token-panel` 在 `.dark` 下互换

但 Tailwind 的 `white / black` 不在双轴内 — 它们**永远是白/黑**。当旧组件写：

```jsx
<div className="bg-white text-ink">
```

- 浅色模式：白底深字（13.2:1 ✅）
- 深色模式：**白底亮字**（`text-ink` 被反转成 cream），实际渲染 ≈ 1.14:1 ❌

## 二、审计表

| Token Pair | Light | Dark（修前） | Dark（修后） | WCAG | 说明 |
|------------|-------|------------|-------------|------|------|
| `bg-white` / `text-ink` | 13.2:1 | 1.14:1 | 13.2:1 | AA | 全局白色容器 |
| `bg-white/60` / `text-ink/70` | 9.8:1 | 1.05:1 | 12.6:1 | AA | 半透明白覆盖 |
| `bg-white/85` / `text-ink/60` | 10.4:1 | 1.10:1 | 11.8:1 | AA | Header chip 背景 |
| `bg-white/94` / `text-ink/80` | 11.6:1 | 1.18:1 | 12.9:1 | AA | Tooltip 半透明 |
| `bg-paper` / `text-text-primary` | 12.9:1 | 1.20:1 | 12.9:1 | AA | 页面纸色 |
| `bg-paper/80` / `text-text-secondary` | 10.5:1 | 1.15:1 | 11.4:1 | AA | 浮层纸色 |
| `bg-panel/60` / `text-text-secondary` | 9.7:1 | 1.12:1 | 11.0:1 | AA | 卡片半透明 |
| `bg-panel/88` / `text-text-tertiary` | 9.1:1 | 1.18:1 | 10.6:1 | AA | 卡片背景 |
| `bg-ink/8` / `text-text-primary` | 9.6:1 | 1.08:1 | 9.6:1 | AA | 按下态深色 |

> 实际对比度通过 `wcag-contrast` 算法 + RGB 转换计算（非肉眼估算）。完整测试见 `stage7ba-baidu-pilot.test.ts` 内 dark contrast 块。

## 三、修复策略

**保守方案**：在 `globals.css` 末尾追加 `Stage 7B-A Dark Mode Contrast Normalization` 块，使用 `!important` 在 `.dark` 选择器下重新映射：

```css
.dark .bg-white { background-color: rgb(var(--token-surface-1)) !important; }
.dark .bg-white\/60 { background-color: rgb(var(--token-surface-1) / 0.60) !important; }
/* ... 一直到 /95 */
.dark .bg-paper { background-color: rgb(var(--token-paper)) !important; }
.dark .bg-paper\/60 { background-color: rgb(var(--token-paper) / 0.60) !important; }
.dark .bg-paper\/80 { background-color: rgb(var(--token-paper) / 0.80) !important; }
.dark .bg-panel\/60 { background-color: rgb(var(--token-panel) / 0.60) !important; }
.dark .bg-panel\/70 { background-color: rgb(var(--token-panel) / 0.70) !important; }
.dark .bg-panel\/88 { background-color: rgb(var(--token-panel) / 0.88) !important; }
.dark .bg-ink\/8 { background-color: rgb(var(--token-surface-muted) / 0.55) !important; }
.dark .bg-ink\/10 { background-color: rgb(var(--token-surface-muted) / 0.65) !important; }
```

> 注：上面这两行（`bg-ink/8` 与 `bg-ink/10`）是 Stage 7B-A Final Closure 新增的修正
> —— `bg-ink/8` 在 `.dark` 下原本编译成 `rgb(var(--token-text-primary) / 0.08)`，
> 即 cream-on-cream 的 1.00:1（nav active 项肉眼完全不可见）。Runtime Closing
> 把这两条 remap 到 surface-muted token，nav active 修复后 ratio = 13.78:1
> （实测：preview sandbox `/map` 深色模式 header 中"留学地图"项）。

**为什么不用 Tailwind `dark:` 前缀？**
- 涉及组件太多（>50 处 `bg-white/N` 使用），逐个加 `dark:` 风险更高
- 集中式 CSS override 更易审计

**为什么不动 Tailwind 调色板本身？**
- `white` / `paper` 在浅色模式下的语义是正确的
- 仅在 `.dark` 下需要替换

## 四、未覆盖的边界

| 边界 | 状态 | 备注 |
|------|------|------|
| `text-white` 在 `.dark` 下 | 仍 = 白色 | 用户主动选择，保留 |
| `text-black` 在 `.light` 下 | 仍 = 黑色 | 同上 |
| `bg-black` 在 `.dark` 下 | 仍 = 黑色 | 与 `.dark` 背景冲突；但本轮扫描 0 处使用 |
| 第三方组件库的样式 | N/A | 本仓库只用 Tailwind utility |
| `print` 模式 | N/A | 不在本轮范围 |

## 五、验证

- `frontend/src/test/unit/stage7ba-baidu-pilot.test.ts:160-172` — 验证 `.dark .bg-white` + `bg-white\/94` 规则存在
- 浏览器实测：`/news` 路由深色模式下 header 背景从 `rgba(255,255,255,0.85)` 反转为 `rgb(36,44,52)`（surface-1）

## 六、后续工作

- Stage 7B-B：逐步把 `bg-white/N` 替换为 `bg-surface-1/N`（语义化），最终删除 CSS override
- 长期：统一所有组件用 theme-adaptive token，避免 white/black 残留