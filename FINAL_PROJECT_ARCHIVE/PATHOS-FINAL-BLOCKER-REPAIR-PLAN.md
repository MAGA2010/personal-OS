# PathOS Final Runtime Blocker Repair Plan

日期：2026-07-30
初始状态：`NOT RUNTIME READY`

## 1. 修复范围

本轮只处理两个最终运行阻断：

1. `/compare` 返回 404；
2. MapLibre 大学 Marker 在初始加载和缩放后不可见。

Backend、Preview Bundle、大学事实、区域数据、Match 算法、FIPS Join、Choropleth 数据与配色均保持只读。

## 2. `/compare` Canonical 决策

磁盘盘点确认：最终前端和历史 integration 都没有独立 Compare 页面；真实比较能力位于 `/map` 内的 `ComparePanel`，选择状态由 `useCompareStore` 管理，数据来自当前 DataSource/BFF。Calculator 另有费用比较流程。

因此采用最小、真实的方案 B：新增 `/compare` 稳定路由并重定向到 Canonical `/map` 比较体验。不复制旧页面、不导入 Mock JSON、不虚构排名或学校字段。

## 3. Marker 根因

浏览器运行时诊断确认，阻断时不是“图层存在但透明”，而是大学 GeoJSON source 和四个 Marker 图层根本没有安装。`UniversityPoiLayer` 在 React 取得 map instance 后使用 `map.loaded()` 判断；当一次性的 MapLibre `load` 事件已经发生、但外部瓦片仍在结算时，`map.loaded()` 会短暂返回 false。旧实现随后订阅一个不会再次发生的 `load`，使晚挂载 effect 永久搁置。

最小修复：

- 初次挂载改为检查 `isStyleLoaded()` 的有界、可取消 readiness polling；
- `style.load` 继续显式、幂等地恢复 source、四个 Marker 图层和事件处理器；
- 每次安装前清理本组件旧 handler，Strict Mode 下不产生重复绑定；
- cleanup 只移除本组件拥有的 source/layer/listener；
- 同时把 zoom 可见阈值交给 MapLibre 原生 `minzoom`，去除易随 `setData` 丢失的 `feature-state.visible`；selected、hover、compare、saved 状态保持不变。

修复不使用固定长延迟、不创建第二套 Marker、不改变经纬度、大学筛选或州图层语义。

## 4. 测试顺序

1. 先新增失败测试：`/compare` 路由存在并指向 `/map`；Marker 不再使用 `feature-state.visible`，四个图层共享规范化 `minzoom`；晚挂载时不等待已发生的 `load`。
2. 实现最小路由和 Marker 修复。
3. 运行定向测试，再运行 TypeScript、Lint、全部 Vitest、Build。
4. 核验 Backend 49/49、Bundle SHA 与 62/62/62/904、4/204/51。
5. 创建全新 Clean-Room，从零安装、构建、Production 启动及六视口 Chrome 验证。
6. 只有运行门槛全部满足，才进入 GitHub 认证、普通 push 与 fresh-clone 复核。

## 5. 安全门槛

- 不创建第二套 Marker；
- 不使用外部 Marker 图片或百度 AK；
- 不放宽数据契约；
- 不改变州选择与单州高亮语义；
- 不使用 force、rebase、reset 或 clean；
- GitHub 无写权限时停止，不连续重试。
