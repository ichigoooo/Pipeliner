## Why

Pipeliner 当前已经具备后端闭环和最小检查界面，但还不具备日常使用级别的工作流创建、运行和调试体验。为了让你和团队成员能够直接在产品中完成对话式创建 pipeline、观察底层协议对象、调试运行态并逐步修改配置，需要把 MVP 的 inspection surface 升级为开发者优先的正式工作台。

## What Changes

- 新增一个面向开发者和小团队的 Workflow Studio 前端，作为未来正式发布所采用的成熟前端入口，而不是继续扩展 FastAPI HTML 检查页。
- 新增对话式 workflow authoring 能力，支持从 `Intent Brief` 发起创作会话、生成结构化 workflow draft，并在发布前查看 lint 与差异。
- 新增 workflow 多视图工作区，围绕同一份 canonical `workflow spec` 提供 cards、graph、spec 和 lint 视图，以及面向高级用户的 raw inspector。
- 扩展 run 操作能力，使用户可以在前端中启动 run、查看 timeline、定位 node round、查看 callback / artifact / context / logs，并执行最小人工介入操作。
- 新增 settings / config 观察面板，展示当前生效的 provider、skill、command template、存储与运行时配置及其来源。
- **BREAKING**: operator 的主要使用路径将从当前最小 CLI + HTML inspection surface 转向 API 驱动的正式前端工作台，后续交互与调试流程以该工作台为主。

## Capabilities

### New Capabilities
- `workflow-authoring`: 提供对话式 workflow 创作会话、draft 管理、lint 反馈、raw spec 编辑与发布能力。
- `developer-console`: 提供开发者优先的 workflow / run / debug / settings 工作台，并保持 cards、graph、spec、raw payload 等多视图对同一真源的同步观察。

### Modified Capabilities
- `run-operations`: 从最小的触发与查看接口扩展为前端驱动的运行、排障、人工介入和 attention 队列能力。

## Impact

- 新增正式前端应用及其构建链路，预计采用 `React + TypeScript` 为核心栈。
- 新增 authoring session、draft、publish、debug 聚合和 settings snapshot 等后端 API。
- 扩展现有 run / callback / artifact 查询模型，使其更适合作为前端工作台的数据源。
- 调整当前 UI 边界：保留最小 HTML 页面作为过渡或回退入口，但不再把它视为主要产品界面。
- 需要补充前后端集成测试，覆盖 authoring、workflow 视图同步、run 调试和人工介入路径。
