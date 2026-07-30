# Security Policy

PathOS 当前是 Demo / Research project。公开仓库不应包含真实凭据或用户申请材料。

## 凭据管理

- 不要在 Issue、Commit、Pull Request、Screenshot、日志或文档中提交 API Key、AK、Token、Cookie、私钥或数据库连接串。
- 本地凭据只放在 `.env.local`；该文件被 `.gitignore` 排除。
- `.env.example` 只能包含空值或明确的安全占位符。
- 不要把学生姓名、联系方式、成绩单、文书或其他申请资料上传到公开仓库。

## 发现凭据泄露时

1. 立即在对应服务控制台撤销并轮换凭据。
2. 从当前分支删除凭据并提交普通修复 commit。
3. 检查日志、构建产物、截图和 Git 历史中的传播范围。
4. 不要在公开讨论中粘贴完整凭据；只报告类型、文件路径和已撤销状态。
5. 如需改写公开 Git 历史，必须单独评估并明确授权；不要自行 force push。

## 报告安全问题

请通过 GitHub 仓库的私密安全报告能力联系维护者。报告中请提供复现步骤和受影响路径，但不要附带仍有效的真实凭据或用户数据。

## 范围说明

当前项目没有生产级账户、支付或隐私合规体系。AI 和 Preview 数据仅用于演示，不构成录取保证或专业顾问意见。Production Data Export 未启用。
