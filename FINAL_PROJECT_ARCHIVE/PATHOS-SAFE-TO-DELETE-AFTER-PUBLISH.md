# PathOS 发布后可安全删除清单

日期：2026-07-30

本清单仅提供人工删除建议。任务没有自动删除任何下列目录。

## 必须永久保留

1. `/Users/jiayihuang/Downloads/PathOS合并`
2. `/Users/jiayihuang/Downloads/PathOS合并-prepublish-backup-2026-07-30.zip`
3. GitHub：`https://github.com/MAGA2010/PathOS`

至少在用户确认 GitHub 页面与本地最终目录均可访问前，不要删除外部备份。

## 可在人工确认后删除

| 路径 | 类型 | 删除前条件 |
| --- | --- | --- |
| `/Users/jiayihuang/Downloads/PathOS-runtime-verification-2026-07-30` | 旧 Clean-Room | 已阅读旧 NOT RUNTIME READY 报告 |
| `/Users/jiayihuang/Downloads/PathOS-runtime-verification-final-2026-07-30` | 最终 Clean-Room | 已保存截图/日志或不再需要现场证据 |
| `/Users/jiayihuang/Downloads/PathOS合并-integration-workspace` | 历史 integration workspace | 已确认最终整合内容位于最终目录和 GitHub |
| `/Users/jiayihuang/Downloads/PathOS-github-publish` | 发布 clone | GitHub `main` 已核验且不再需要本地发布历史 |
| `/Users/jiayihuang/Downloads/PathOS-post-push-final-verify` | 第一轮 post-push fresh clone | 最终远端 HEAD 的第二轮 fresh clone 已完成 |
| `/Users/jiayihuang/Downloads/PathOS-post-push-final-verify-2` | 最终 post-push fresh clone | 用户已完成仓库验收 |

## 不要批量删除

- 不要使用模糊 `rm -rf`、`git clean` 或通配符删除 Downloads 下的目录。
- 删除前逐项核对绝对路径。
- 不要删除未知目录、其他项目、外部备份或最终保存目录。
- 这些路径含构建缓存和依赖，可重新生成，但也包含本轮验收证据；是否保留由用户决定。
