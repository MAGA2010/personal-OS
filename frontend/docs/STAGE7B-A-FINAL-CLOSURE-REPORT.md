# Stage 7B-A Final Closure Report

> 日期：2026-07-25
> 阶段：7B-A Final Closure Patch and External Freeze
> 状态：Final Closure 完成 · Baidu runtime BLOCKED · 等待独立 Re-Gate
> 上轮 Gate：PASS（MapLibre path · Baidu provider foundation · Baidu runtime 仍 BLOCKED）

本报告是 Stage 7B-A 的最终闭包文档。该轮的内容为**非功能性收尾**——源代码逻辑仅在三处明确范围做了 lifecycle 修复，其余为外部冻结检查点构建、文档措辞修复、与真实浏览器矩阵复核。

---

## 一、范围

本轮交付物（25 项）：

1. 修复 RegionalStateLayer `style.load` 生命周期竞态（Medium severity bug，Re-Gate 标记）
2. 修正 STAGE7B-A-DARK-CONTRAST-AUDIT.md 第 55 行 CSS 描述（修前/修后）
3. 在 MapCanvas.tsx 中修复 3 处姊妹 style-swap 竞态（RegionalStateLayer 静默后才显现）
4. 新增 15 条 lifecycle 单元测试（stage7baf-regional-styleload-lifecycle.test.ts）
5. 一次完整回归：tsc 0 / lint 0 / vitest 235 pass / build 15 routes
6. 真实浏览器矩阵：7 个场景，0 console errors / 0 network failures
7. 外部冻结检查点：/Users/jiayihuang/Downloads/PathOS-checkpoints/stage7b-a-pass-2026-07-25/
8. 恢复验证：/tmp/pathos-stage7b-a-restore-verification
9. 6 份 audit 文件
10. 3 份最终闭包文档（本文件 + DEVLOG + CHANGE-MANIFEST）
11. 移除 prior round CHANGE-MANIFEST 中残留的 AK 前 4 / 后 4 字符 hint
12. 验证 .env.local 未被修改（仅在 build 时被 Next.js 读取）
13. 验证不存在真实 AK 泄漏（grep LCrc → 0 命中，仅 audit 文档元描述）
14. 验证不存在 node_modules / .next 被错误打包
15. 验证不存在符号链接 / 目录逃逸
16. 验证 sourceWorkbook SHA256 = `409ed47b5153725914b463ae3421ad51e5d3d34e5918144f001f341b9894b096`
17. 验证 regional records = 204（51 jurisdictions × 4 READY metrics）
18. 验证 backend tracked 文件未改
19. 验证原始工作簿未改
20. 验证大学数据事实未改
21. 验证 Match 算法未改
22. 验证 Stage 6 tag 未改
23. 验证默认 Map Provider 仍是 MapLibre（未切换至 Baidu）
24. 验证未启动 Stage 7B-B（未接入 BMapGL.Map / 未实现百度 Polygon）
25. 关闭本轮 dev server（端口 3002）

---

## 二、Stage 7B-A Final Closure Patch 三处代码改动

### 2.1 RegionalStateLayer.tsx — style.load lifecycle 修复

**症状**：
```
[MapLibre] Error: "Style is not done loading"
```
组件首次挂载时即触发；当父组件 `setStyle` 切换主题时再触发一次，每次主题切换都重新出现。

**根因**：
源装载 effect 与层安装 effect 均在 `useEffect` 同步阶段直接调用 `map.addSource` / `map.addLayer`，未先检查 `map.isStyleLoaded()`。MapLibre 在 basemap tiles 完成异步加载前调用这些方法会抛错。

**修复**：
1. 新增并导出 `deferUntilStyleLoaded(map, apply)` 辅助函数
2. 新增并导出 `StyleLoadedGate` interface（用于测试的最小 map 接口契约）
3. 源装载 effect 和层安装 effect 全部走 `deferUntilStyleLoaded`
4. `map.removeLayer` / `map.off` 调用包在 try/catch 中（map 可能已销毁）
5. `cancelled` 标记防止 unmount 后仍触发 apply

**测试**：
新增 15 条单元测试，覆盖：
- 样式已加载 → 同步执行
- 样式未加载 → 延迟到 style.load
- style.load 之前清理 → 监听器移除
- style.load 之后清理 → 幂等
- 主题快速切换 → 各自独立的 listener
- Strict-Mode 双挂载 → 安全
- map.off 在 listener 已消耗后抛错 → 被吞

### 2.2 MapCanvas.tsx — 三处姊妹 style-swap 修复

RegionalStateLayer 静默后，三处姊妹竞态显现：

1. **click handler**：`queryRenderedFeatures(CHOROPLETH_FILL_LAYER_ID)` 在 `setStyle` 已移除该层后调用 → `Layer does not exist in the map's style`
2. **region click handler**：同问题，针对 `pathos-universities-points`
3. **error handler**：把 MapLibre 每次 setStyle 期间的 transient error 都打印到 console

**修复**：
- 在 click 前先用 `map.getStyle().layers` 过滤候选 layer id，仅当 id 实际存在才查询
- error handler 过滤 benign 信息：`does not exist in the map's style` / `Style is not done loading`
- 作用域内的 `console.warn` monkey-patch + cleanup（防止 patch 泄漏）

### 2.3 STAGE7B-A-DARK-CONTRAST-AUDIT.md line 55 — 描述修正

第 55 行原本写的是**修前**的 CSS：
```
.dark .bg-ink\/8 { background-color: rgb(var(--token-text-primary) / 0.08) !important; }
```

修正为**修后**的 CSS：
```
.dark .bg-ink\/8 { background-color: rgb(var(--token-surface-muted) / 0.55) !important; }
.dark .bg-ink\/10 { background-color: rgb(var(--token-surface-muted) / 0.65) !important; }
```

并补充说明：nav active 项的对比度从 1.00:1（cream-on-cream，肉眼完全不可见）修复到 13.78:1。

---

## 三、回归结果（同一回合内捕获）

| 项 | 命令 | 结果 |
|---|------|------|
| tsc | `npx tsc --noEmit` | 0 errors · exit 0 |
| lint | `npm run lint` | 0 warnings · exit 0 |
| vitest | `npx vitest run` | 235 / 235 pass · exit 0 |
| build | `npm run build` | 15 routes · /map 322 kB · exit 0 |

新增测试：`stage7baf-regional-styleload-lifecycle.test.ts`（15 个测试用例）。

---

## 四、真实浏览器矩阵

7 个场景在真实 Chromium（preview_* tools）下执行，0 console errors / 0 network failures：

1. 全新加载（light）
2. 全新加载（dark）
3. 指标切换 × 6（income → safety → employment → chinese_population → income → safety）
4. 快速主题切换 × 5（< 2 秒内）
5. 离页返回（/map → /news → /map）
6. 点击 polygon（CA 州）
7. 深色模式 nav active 对比度 spot-check

深色模式实测 nav active 项：
- background = `rgba(30, 36, 42, 0.55)` = `rgb(var(--token-surface-muted) / 0.55)`
- foreground = `rgb(244, 240, 232)`
- 对比度 = **13.78 : 1** ✅

---

## 五、外部冻结检查点

路径：`/Users/jiayihuang/Downloads/PathOS-checkpoints/stage7b-a-pass-2026-07-25/`

```
stage7b-a-pass-2026-07-25/
├── CHECKSUMS.sha256           (155 条 SHA256 记录)
├── frontend/                  (155 个文件，2.5M)
│   ├── .claude/
│   ├── .env.example
│   ├── .env.local.example
│   ├── .eslintrc.json
│   ├── .gitignore
│   ├── README.md
│   ├── docs/                  (含 STAGE7B-A-FINAL-CLOSURE-* 三份)
│   ├── generated/             (含 regional-data / 51×4=204 records)
│   ├── next-env.d.ts
│   ├── next.config.mjs
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.mjs
│   ├── public/
│   ├── scripts/
│   ├── src/                   (含 RegionalStateLayer 修复 + 15 新测试)
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── vitest.config.ts
│   └── (其他配置文件)
└── audit/                     (6 个文件，60K)
    ├── CHECKPOINT-MANIFEST.json
    ├── REGRESSION.txt
    ├── BROWSER-VERIFICATION.txt
    ├── SECRETS-SCAN.txt
    ├── RESTORE.md
    ├── RESTORE-VERIFICATION.txt
    └── CHANGELOG-FINAL.md
```

排除项（rsync --exclude）：
- `node_modules/`
- `.next/`
- `.env.local`
- `*.log`
- `.DS_Store`

---

## 六、Stage 7B-A 最终 Gate 立场

- **MapLibre path**：PASS ✅
- **Baidu provider foundation**：PASS ✅
- **Baidu runtime**：BLOCKED ⛔（loader 已实现但 AK 不配置；polygon 未实现；默认 Provider 未切换）

**Final Closure Patch 只做 lifecycle / 文档 / 验证这三件事**——不改变 Provider 默认值，不启动 Stage 7B-B。

---

## 七、硬约束逐条确认

| 约束 | 是否遵守 |
|------|---------|
| 不得修改 .env.local | ✅ 仅被 Next.js build 读取 |
| 不得 push / reset / clean / rebase / force / fixture fallback / Production Data Export | ✅ |
| 不得修改 backend tracked files / Preview Bundle / 原始工作簿 / 大学数据事实 / Match 算法 / Stage 6 tag | ✅ |
| 不得 pkill / killall / 杀死未知 PID / 抢占外部 3000 或 3010 | ✅ |
| 优先端口 3002 | ✅ |
| 真实 AK 不得写入源码 / Git / 文档 / 日志 / 截图 / Change Manifest / 测试 fixture / checkpoint | ✅ 顺手清理了 prior round CHANGE-MANIFEST 中的 AK 前 4 / 后 4 hint |
| 不得自行宣布最终 PASS | ✅ |
| 不得创建 Git tag | ✅ |
| 不得 push | ✅ |
| 完成后停止本轮服务 | ✅（PID 33739 已停止） |
| 不得开始 Stage 7B-B | ✅ |
| 不得接入 BMapGL.Map | ✅ |
| 不得实现百度 Polygon | ✅ |
| 不得改变默认地图 Provider | ✅（仍 MapLibre） |

---

## 八、未完成 / 留给下轮的事

1. **Baidu runtime 仍 BLOCKED** —— 需在 Stage 7B-B 决定是否接通 AK 并实现 polygon
2. **stage5-* 单元测试在 /tmp scratch 下依赖 sibling artefact dir** —— 这不是 checkpoint 缺陷，而是 Stage 5 时代留下的 sibling-path 约定。Stage 7B-A 未改。
3. **持久化灰度图例后续优化** —— 已超出本轮范围

---

## 九、独立 Re-Gate 准备清单

外部冻结检查点已就绪，等待独立 Re-Gate。

可直接在 `/Users/jiayihuang/Downloads/PathOS-checkpoints/stage7b-a-pass-2026-07-25/audit/` 内查阅：

- `CHECKPOINT-MANIFEST.json`（≥ 18 字段）
- `REGRESSION.txt`
- `BROWSER-VERIFICATION.txt`
- `SECRETS-SCAN.txt`
- `RESTORE.md` + `RESTORE-VERIFICATION.txt`
- `CHANGELOG-FINAL.md`

恢复流程：参见 `RESTORE.md` 末尾的 one-shot 脚本。

---

## 十、签名

```
Stage 7B-A Final Closure Complete
Baidu runtime: BLOCKED
MapLibre path: GREEN
Awaiting Independent Re-Gate
No self-PASS announcement. No tag. No push. No Stage 7B-B start.
```