## Context

当前运行链路已经具备 run 创建、手动 `drive`、node round 详情、callback / artifact / log 查看，以及 Claude 输出流式读取能力，但这些能力尚未串成一条连续的操作路径。Studio 中点击“启动运行”后只会创建 run，不会自动 dispatch executor / validator；运行页默认也更偏向离线排障视图，而不是运行中监控视图。

这次变更是一个跨后端运行控制、运行态聚合 API 和前端 run workspace 的联动优化。现有实现已经有可复用的 `RunDriver`、`ClaudeTerminalPanel` 和 `claude-calls/{call_id}/poll|stream` 能力，因此设计重点不是新增一套实时基础设施，而是把现有运行信号聚合为面向操作员的实时进度体验。

## Goals / Non-Goals

**Goals:**
- 启动 run 后默认自动驱动执行，减少“创建了 run 但实际上还没跑”的断层。
- 在 run workspace 中以流程图方式突出当前焦点节点，并结合活动流表达最近进展。
- 复用现有 Claude call 输出流，在节点详情中默认展开当前活跃节点的终端输出。
- 在保持手动 `Drive` 能力的同时，避免与自动驱动产生冲突。

**Non-Goals:**
- 不引入消息队列、分布式 worker 或新的任务调度系统。
- 不重构 runtime 状态机、callback 协议或 artifact 存储模型。
- 不引入 WebSocket 专用推送层；v1 继续沿用轮询和现有 SSE 输出。

## Decisions

### 1) 启动 run 默认触发后台自动驱动
**Decision**: 为 `POST /api/runs` 增加 `auto_drive` 请求参数，默认值为 `true`，在 run 创建完成后立即启动后台自动驱动。  
**Rationale**: 让“启动运行”语义与用户直觉一致，避免用户额外理解 `Drive` 的存在。  
**Alternatives**: 保持手动 `Drive` 为主路径，只补提示与可视化；这仍无法消除“run 已创建但未执行”的根因。

### 2) 自动驱动采用进程内协调器而不是新基础设施
**Decision**: 引入轻量 `RunDriveCoordinator`，以进程内 daemon thread 执行 `RunDriver.drive`。每个后台线程都通过 `Database.session()` 新建 session，不复用请求线程中的 session。  
**Rationale**: 仓库当前是单实例本地 Studio / API 模式，已有 SQLite `check_same_thread=False` 与标准 session 工厂，足以支撑轻量后台驱动。  
**Alternatives**: 
- 使用外部队列 / worker：超出当前复杂度预算。
- 在请求线程内同步 drive：会阻塞创建 run 的响应，也无法形成“先跳转到运行页再看实时进度”的体验。

### 3) 自动驱动与手动 drive 使用 per-run single-flight 互斥
**Decision**: 同一 run 在任意时刻只允许一个 driver 实例运行；若已有自动驱动在跑，手动 `/drive` 请求返回冲突错误，前端同时禁用 `Drive` 按钮。  
**Rationale**: 避免并发 dispatch 导致同一节点重复执行，保持状态机简单可推理。  
**Alternatives**: 允许多个 drive 请求竞争同一 run；这会放大状态竞争与重复 callback 风险。

### 4) 活动流从现有状态源动态聚合，不新增持久化事件表
**Decision**: 扩展 `RunOverview`，新增 `driver`、`current_focus`、`activity` 三个聚合块；其中 `activity` 由 `RunModel`、`NodeRunModel`、`CallbackEventModel` 和 Claude call metadata 动态拼装。  
**Rationale**: 现有状态源已经包含足够的运行痕迹，新增聚合层即可支撑 UI，而不必引入额外写路径或迁移。  
**Alternatives**: 新建 run activity 表；这会增加写入耦合与迁移成本。

### 5) Run workspace 以“流程图 + 当前节点详情”作为默认视图
**Decision**: 运行页在 `run.status=running` 时默认聚焦 `current_focus`，主区域顶部展示 workflow 流程图并高亮当前节点，主区域下半部分展示所选节点当前轮次的详情。节点详情以 `Terminal / Artifacts / Callbacks / Raw` 分 tab 组织，并默认展开当前 executor / validator 的 `ClaudeTerminalPanel`。左侧保留当前焦点、最近活动流、driver 状态和手动 `Drive` 高级控制。  
**Rationale**: 用户首先需要知道“当前跑到 workflow 的哪里了”，其次才是查看该节点的终端输出与产物；流程图比纯 timeline 更容易帮助非开发者理解执行位置。  
**Alternatives**:
- 保持 timeline 或 Node Detail 为唯一主视图；更偏向排障而不是运行中理解。
- 仅增加活动流而不提供图形化定位；用户仍然难以快速建立 workflow 全局上下文。

### 6) 运行中使用更快轮询，终态后回退
**Decision**: `run` / `overview` / `nodeRound` 在运行中每 `1500ms` 轮询一次，终态后回退到 `8000ms`。  
**Rationale**: 在不新增推送机制的前提下，把运行中反馈延迟压到用户可接受范围。  
**Alternatives**: 全程 `8000ms` 轮询；中间反馈仍会显著滞后。

## Risks / Trade-offs

- **[自动驱动线程在单进程模型下不适合多实例部署]** → v1 明确目标为当前单实例 Studio；后续如需多实例再把协调器抽象为独立 worker。
- **[活动流来自动态聚合，时间戳精度受现有模型限制]** → UI 以“最近活动”和状态演进为主，不承诺事件总线级别精确时序。
- **[长时间运行会持续轮询]** → 仅在 `running` 态使用高频轮询，终态立即降频。
- **[driver 冲突导致用户误以为按钮失效]** → 后端返回明确冲突信息，前端在 driver 运行中显式展示“自动驱动中”并禁用 `Drive`。
