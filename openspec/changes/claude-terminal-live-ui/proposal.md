## Why

用户缺少 Claude Code 调用过程的可视化，难以判断执行状态与错误位置，调试与问题定位成本高。 
## What Changes

- 在所有调用 Claude Code 的入口提供可展开的实时终端视图，用于观察执行过程与输出。 
- 终端只读展示，不引入任何交互控制（暂停/继续/重试等）。 
- 终端展示的内容与 CLI 调用时一致，包含过程输出与可用的思维链/流程信息。 
## Capabilities

### New Capabilities
- `claude-terminal-live-ui`: 在 Claude Code 调用入口提供可展开的只读终端实时输出视图。 
## Impact

- 前端：在所有 Claude Code 调用入口增加可展开终端区域，支持流式追加输出与完成态展示。 
- 后端：提供 Claude Code 调用的实时输出流或可轮询日志接口（若已有日志采集则复用）。 
- 兼容性：不改动现有调用协议，仅增加可视化能力。 
