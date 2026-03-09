## Context

Pipeliner 的 MVP 目标不是一次性做出完整产品，而是在单机、本地文件系统、最小界面的前提下，验证一套“以 Skill 驱动的 agent 节点编排模型”是否能够稳定闭环。当前已经沉淀了 `workflow spec`、`node callback payload`、`artifact manifest`、`runtime guards` 和技术栈决策文档，设计重心已从“概念可行性”转向“如何把协议变成可运行系统”。

当前约束如下：

- V1 使用 `Python` 优先实现后端核心，不以复杂 Web UI/UX 为前置目标。
- Runtime 的角色是传话者、状态记录者和流转推进者，而不是语义裁判。
- 节点之间流动的是 `artifact ref + manifest`，不是大文件本体。
- 每个 workflow run 都有独立 run root，本地存储后端先收敛为 `local_fs`。
- `executor` 与 `validator` 都通过 Skill 驱动，Pipeliner 不重复设计 Skill 内部规范。
- `workflow spec` 是机器真源；人类可读视图若存在，也必须从其派生。
- V1 不引入复杂自动重试、分布式执行、拖拽式工作流编辑器和产品级 UI。

## Goals / Non-Goals

**Goals:**
- 实现 `workflow spec` 的加载、校验与版本化管理，使其成为工作流机器真源。
- 实现最小 Runtime，支持 `executor -> validator -> pass / revise / blocked` 的节点闭环。
- 实现 callback 接收与幂等去重，支撑 agent 通过 API 报告执行结果和验收结果。
- 实现 artifact registry、manifest 登记与 run root 目录布局，使大文件和文件集合能稳定流转。
- 实现最小状态持久化，支撑 run、node run、callback event 和 artifact 的查询与排障。
- 提供最简单可用的操作入口，用于触发 run、查看状态和人工介入。

**Non-Goals:**
- 不实现分布式队列、远程 worker 调度或多机协调。
- 不实现复杂自动恢复、自动重试策略或可配置恢复编排。
- 不实现完整的工作流可视化编辑器和高完成度前端体验。
- 不在 MVP 中实现完整的对话式工作流生成入口或高级 authoring copilot，只保留后续接入全局工作流生成 Skill 的边界。
- 不把 `Node Card` 或其他人类视图做成独立真源；若提供查看能力，也仅为从 `workflow spec` 派生的只读视图。
- 不扩展 Skill 协议，不定义 Skill 包内部结构，不接管第三方 agent 的执行细节。
- 不在 MVP 中支持除 `local_fs` 之外的对象存储或外部 artifact backend。

## Decisions

### 1. 采用 Python-first 单体架构承载 MVP

**Decision**
- 使用 `Python 3.12+` 作为后端实现语言。
- 使用 `FastAPI` 提供 callback API 与基础管理接口。
- 使用 `Pydantic v2` 承载协议模型与输入输出校验。
- 使用 `SQLite + SQLAlchemy 2.x + Alembic` 管理持久化。
- 使用 `Typer` 提供本地操作入口。

**Rationale**
- 当前系统的核心问题是协议、文件、状态机和本地编排，而不是前端交互复杂度。
- Python 更适合处理结构化协议建模、文件系统操作、脚本/子进程交互和本地验证工具链。
- 单体架构可以最小化跨进程与分布式复杂度，更快验证核心闭环。

**Alternatives considered**
- `TypeScript + Node.js`：在未来 UI 与前后端同构上更顺手，但当前对文件系统与协议快速收口的收益不如 Python。
- 分离 API 服务与 Runtime worker：扩展性更好，但会过早引入调度、通信和部署复杂度。

### 2. 以协议对象驱动实现，而不是以 UI 或 Skill 驱动实现

**Decision**
- 以 `workflow spec`、`callback payload`、`artifact manifest`、`runtime guards` 作为实现骨架。
- Runtime 直接围绕这些协议对象推进状态，而不是围绕某种 UI 视图或 Skill 模板编码。

**Rationale**
- 当前最稳定的设计资产已经是协议文档。
- 先把机器真源和运行协议做实，后续 UI、编辑器和 authoring 体验才有稳定依附物。

**Alternatives considered**
- 先做 Node Card 或图编辑器再反推协议：更直观，但极易在 V1 阶段引入双真源问题。
- 直接围绕 Skill 执行器接口建系统：会把本应稳定的工作流合同退化为工具细节。

### 3. Runtime 采用“协调者/转发者”状态机，而非语义仲裁器

**Decision**
- Runtime 只负责：
  - 启动 run 与 node round
  - 记录当前等待的 actor
  - 接收 callback 并做幂等去重
  - 把 executor 产物转交给 validator
  - 根据 validator 的 `pass / revise / blocked` 推进或返工
  - 在超时、失败或阻塞时停在人工介入边界
- Runtime 不自行判断文案质量、JSON 语义正确性等业务含义。

**Rationale**
- 这是当前设计里最关键的职责边界。
- 一旦 Runtime 介入语义判断，就会和 validator Skill 的职责重叠，导致系统边界混乱。

**Alternatives considered**
- 让 Runtime 内置一部分规则判断：短期看似省事，但会快速形成一套与 Skill 验收重复的规则系统。

### 4. MVP 采用最小状态机与最小落库模型

**Decision**
- 定义两层状态：`run` 状态与 `node_run` 状态。
- `run` 至少包括：`pending`、`running`、`blocked`、`failed`、`completed`。
- `node_run` 至少包括：`pending`、`awaiting_executor`、`awaiting_validator`、`revising`、`passed`、`blocked`、`failed`、`timed_out`。
- 持久化最小表集包括：
  - `workflow_definitions`
  - `workflow_versions`
  - `runs`
  - `node_runs`
  - `callback_events`
  - `artifacts`

**Rationale**
- 这组状态与表结构足以支撑 MVP 的闭环、排障和人工介入，不需要提前引入更多维度。
- 将 `round_no` 直接记录在 `node_runs` 中，可以自然表达返工轮次和 artifact 版本递增。

**Alternatives considered**
- 为 validator verdict、handoff、manual intervention 单独拆更多表：查询更细，但会增加模型复杂度。
- 只落文件不落库：实现快，但无法可靠支撑状态查询、幂等处理和后续界面。

### 5. callback API 使用统一结果入口

**Decision**
- MVP 使用统一 callback 入口，例如 `POST /api/runs/{run_id}/nodes/{node_id}/callback`。
- executor 与 validator 共用同一结果通道，通过 payload 内的 `actor.role` 和 `validator_id` 区分身份。
- `event_id` 作为幂等键，重复提交不得造成重复推进。

**Rationale**
- 统一入口更适合当前“Runtime 是协议转发者”的模型。
- 把身份区分放在 payload 中，有利于保持 API 面最薄。

**Alternatives considered**
- executor / validator 分两个端点：语义更直观，但接口面更宽，后续仍需在内部汇合。
- 由 Runtime 轮询 agent 结果：不符合当前“agent 主动 API 汇报”的顶层设计。

### 6. artifact 流转采用 run root + manifest 登记

**Decision**
- 每个 workflow run 创建独立 run root。
- run root 下至少包含：
  - workflow 输入快照
  - node 工作目录
  - artifact payload
  - artifact manifest
  - callback 原始事件归档
- 节点之间流动的是 `{ artifact_id, version }`，Runtime 通过 manifest 解析到实际位置。
- artifact 发布版本不可变；返工必须生成新版本，不得原地覆盖已发布版本。

**Rationale**
- 这样既能支撑大文件/多文件集合流转，也能保留强追踪和排障能力。
- artifact 发布后不可变，返工生成新版本，天然适配 validator 返工模型。

**Alternatives considered**
- 直接在 callback 中传文件本体：对大文件不友好，也不利于版本追踪。
- 只传路径不登记 manifest：会让引用语义脆弱，且不利于后续迁移存储后端。

### 7. 先提供最小操作界面，而不是完整产品前端

**Decision**
- MVP 提供 CLI 与最小可用管理界面即可。
- 管理面优先满足：触发 run、查看 workflow/run/node 状态、查看 artifact 基本信息、查看 callback 事件和人工介入点。
- 如提供 workflow 人类视图，也只提供从 `workflow spec` 派生的只读摘要或卡片式查看，不引入独立编辑真源。

**Rationale**
- 当前最需要验证的是协议和 Runtime 闭环，而不是产品级 UI。
- 最小操作面已经足以支撑自测、演示和设计迭代。

**Alternatives considered**
- 先做完整 Web 编辑器：投入大、返工风险高，会显著拖慢核心验证。

### 8. 工作流生成与人类视图在 MVP 中只保留稳定边界

**Decision**
- `workflow spec` 保持为唯一机器真源。
- MVP 不实现完整对话式工作流生成入口，但 workflow 定义加载、校验、版本化接口必须足够稳定，以便后续接入 `Claude Code` 全局工作流生成 Skill。
- MVP 不把 `Node Card` 做成独立文件或独立存储模型；若需要更友好的理解视图，统一从 `workflow spec` 派生。

**Rationale**
- 这样既保留了未来 authoring 能力的接入点，又避免在 MVP 阶段过早承担生成式 authoring 与双真源同步复杂度。
- 当前先把 canonical spec 和 runtime 闭环做实，才适合承接更高层的工作流创作体验。

**Alternatives considered**
- 现在就实现对话式工作流生成：价值明确，但会立刻引入 prompt 编排、authoring lint、交互雕琢和大量边界情况。
- 为 Node Card 建独立存储：短期看似友好，但会明显增加同步与一致性成本。

## Risks / Trade-offs

- **[状态机边界仍需谨慎收口]** → 先按最小状态集合实现，避免在 MVP 引入过细状态；若实现期发现缺口，再通过文档先补再扩展。
- **[设计文档与实现之间可能出现偏差]** → 以协议模型和 OpenSpec artifact 为实施真源，避免开发时各处自行发挥。
- **[单机 local_fs 方案未来扩展性有限]** → 明确把 `storage.backend = local_fs` 视为 V1 约束，并在实现中保持 storage adapter 边界。
- **[统一 callback 入口对 payload 约束要求更高]** → 强制使用 Pydantic 模型和幂等检查，避免 executor/validator 混淆。
- **[Skill 执行细节不受 Pipeliner 控制]** → 把系统边界收紧在输入合同、回调协议和验收闭环，避免承担外部 agent 的执行内部正确性。
- **[MVP 暂不实现 workflow generation]** → 先把加载/校验/版本化边界做稳，避免后续接入生成入口时再返工核心模型。
- **[最小 GUI 能力较弱]** → 接受可用性优先于精致体验，用它服务核心调试而不是产品展示。

## Migration Plan

1. 搭建 Python 项目骨架与基础依赖，建立 API、runtime、models、storage、cli、ui 的最小目录边界。
2. 先实现协议模型与 workflow spec loader，确保协议对象可被读取、校验与持久化，并保持 canonical spec 边界清晰。
3. 实现 runs / node_runs / callback_events / artifacts 的最小持久化与迁移。
4. 实现 callback API、幂等去重和 Runtime 状态推进。
5. 实现 run root、artifact manifest 登记与本地 payload 存储。
6. 实现基础操作入口与最小状态查看能力，包括从 `workflow spec` 派生的基础可读摘要视图（如实现该查看能力）。
7. 用一个最小 workflow 样例跑通 executor 完成、validator 通过、validator 返工、blocked 和 timeout 等核心路径。

回滚策略：
- MVP 仅在本地开发环境推进，不涉及生产迁移。
- 若中途发现模型失配，以数据库可重建、run root 可清理的方式快速回退；以协议文档和 OpenSpec artifacts 为修正基线。

## Open Questions

- `node_runs` 是否需要把每轮返工作为独立记录，还是以 `(run_id, node_id, round_no)` 复合唯一约束承载即可。
- 最小 GUI 是先用 FastAPI 模板页面承载，还是先只做 CLI + JSON API。
- manual intervention 在 MVP 中是否只需要“标记与查看”，还是需要最小“继续执行/重试”操作。
