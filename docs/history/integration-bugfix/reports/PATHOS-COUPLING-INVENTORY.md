# PathOS 多仓库与候选版本盘点

## 总览

- 物理候选 Git 仓库：1。
- 候选版本实体：3（dirty 工作树、Git HEAD、历史 Backend ZIP）。
- Canonical 项目：1 套稳定前端 + 1 套只读 standalone Backend。
- Canonical 前端：14 个路由、49 个组件、22 个测试文件、9 个既有媒体资产。
- 候选工作树：14 个路由、23 个根级组件、41 个测试文件、6 个资产。
- 候选 HEAD：11 个路由、17 个组件、41 个测试文件、11 个资产。
- 候选 Backend ZIP：历史归档，1 个路由、7 个组件、45 个测试，未解压进入运行路径。

## 血缘

共分析 144 个模块：

- exactDuplicate：17；
- nearDuplicate：13；
- canonicalOnly：92；
- independentImplementation：10；
- sameNameDifferentPurpose：11；
- forkedFromCandidate：1。

识别 27 组完全重复文件。详细记录见 `MODULE-LINEAGE.json` 与 `DUPLICATE-MATRIX.json`。

## Canonical

- 前端来源：`/Users/jiayihuang/Downloads/PathOS合并/PathOS-main/frontend` 的只读快照。
- Backend：`/Users/jiayihuang/Downloads/PathOS合并/PathOS-db-ranking-standalone`。
- Backend HEAD：`b73e61ec4fda11b7c72e74c14e414fbe2c74300f`。
- Preview manifest SHA-256：`88f3dd6081df38b051872cc5c8bf5b12dd08e9dee072780f20becfc8e9170bd2`。

候选的修改时间只记录，不参与选择。候选仓库 dirty、存在 stash、包含历史 Backend ZIP，因此所有候选代码默认只读；未恢复 stash、未运行 migration、未使用候选数据。
