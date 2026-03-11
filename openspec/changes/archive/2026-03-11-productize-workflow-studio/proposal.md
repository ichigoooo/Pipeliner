## Why

当前 Workflow Studio 仍偏“可演示”，无法通过前端完成从创作到运行再到迭代的完整闭环。 
尤其缺少 Authoring 阶段的 Claude Code 生成与运行自动驱动入口，导致产品不可用。 
现在需要把 Studio 补齐为可日常使用的工程级工作台。 

## What Changes

- 接入 Claude Code 作为 Authoring 阶段的对话式生成能力，支持基于 intent/instruction 生成新草案版本并保留审计记录。 
- 增加从已发布版本或 attention 运行发起新会话的迭代入口，形成持续改进闭环。 
- 增加 run 自动驱动能力的 API 与 Studio 入口，减少对 CLI 依赖。 
- 增强产物与日志可读性（manifest、预览、链路追踪），提升调试效率。 
- **BREAKING**: 无。 

## Capabilities

### New Capabilities
- `authoring-agent`: 在 authoring 会话中调用 Claude Code 生成/修订草案，并记录生成日志与错误。 
- `workflow-iteration`: 从已发布版本或 attention 运行上下文发起新的 authoring 会话并携带 rework brief。 
- `run-drive-automation`: 提供运行自动驱动 API 与 Studio 入口，可设置步数上限并返回驱动结果。 
- `artifact-inspection`: 在 Studio 中查看 artifact manifest、storage 引用与可预览内容/日志引用。 

### Modified Capabilities
- `run-operations`: 增加“自动驱动运行”与“手动 dispatch executor/validator”的操作要求。 

## Impact

- 后端：新增 authoring agent 服务、run drive API、运行与草案迭代入口。 
- 前端：新增生成/驱动入口、迭代入口、artifact/log 预览与链路查看。 
- 配置：新增或扩展 Claude 命令模板与调用日志/审计记录。 
