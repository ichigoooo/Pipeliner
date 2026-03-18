## Why

Workflow Studio 的主闭环已经基本跑通，但当前仍存在明显的产品化收口缺口：Claude 调用失败时诊断信息不够聚焦、慢启动与超时语义容易混淆、运行列表和批次历史会不断积压、文档基线也已经落后于真实能力。现在需要把这些“最后一公里”问题收紧，否则系统虽然可用，但还不够稳定、清晰、易维护。

## What Changes

- 统一 Claude executor / validator / authoring 的环境诊断与失败分类，优先暴露可操作的网络、代理、域名解析与配置问题。
- 明确首字节慢启动与真实超时的产品语义，在 Run Workspace 中持续可见，并避免把“无输出但仍在运行”误判成空闲或其他失败类型。
- 提升运行操作易用性：将运行列表按“需处理 / 进行中 / 归档”分组展示，支持批量清理非运行中 run 与已结束 batch，并保持批次历史可追溯。
- 提升 Run Detail 的连续操作体验，包括“跟随当前焦点 / 固定查看历史轮次”的切换，以及在无终端输出时仍能解释当前状态。
- 同步 README、开发计划与测试基线，使 OpenSpec、文档与当前产品能力重新对齐。
- **BREAKING**: 无。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `run-operations`: 强化运行列表分组、批量清理、历史轮次查看和慢启动/超时状态解释的要求。
- `developer-console`: 扩展设置页，要求展示 Claude 连接诊断信息，而不仅是静态配置溯源。
- `claude-terminal-live-ui`: 扩展终端面板行为，要求在无输出时仍提供排队、慢启动和连接失败提示。
- `authoring-agent`: 扩展生成失败场景，要求返回可操作的诊断信息并保持现有草案不被覆盖。

## Impact

- 后端：`claude_env`、`claude_call`、executor/validator/authoring dispatcher、`RunService`、`SettingsService`、相关 API。
- 前端：`/runs`、`/runs/[run_id]`、`/settings`、Claude terminal 相关组件与国际化文案。
- 测试：后端运行时语义测试、Claude 诊断测试、前端运行页与设置页交互测试。
- 文档：`README.md`、`docs/development-plan.md`、必要的 Studio 使用说明与 OpenSpec 归档准备。
