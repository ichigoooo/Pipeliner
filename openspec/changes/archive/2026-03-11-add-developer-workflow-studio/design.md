## Context

Pipeliner 当前已经实现了 `workflow spec`、runtime、callback、artifact registry 和最小 run 操作闭环，但主要使用方式仍然是 CLI、JSON API 与 FastAPI HTML inspection 页面组合。这个形态足以验证协议和状态机，却不足以支撑你和团队成员进行日常 workflow 创建、运行、调试和配置观察。

在产品方向上，现有总设计已经明确了几项长期原则：

- `workflow spec` 继续作为唯一机器真源。
- 用户应能够通过对话式 authoring 逐步生成 workflow，而不是主要依赖手写 DSL 或表单。
- `Node Card`、graph 和其他人类视图都应从 canonical spec 派生，而不是形成第二份真源。
- 当前阶段的前端优先级从“最小可用检查面”切换为“开发者优先、内部团队可日常使用的工作台”。

这次 change 的目标不是做一个低门槛零代码产品，而是做一个工程控制台：默认帮助理解和操作，但不隐藏底层协议对象、配置和调试细节。

## Goals / Non-Goals

**Goals:**
- 提供一个正式前端工作台，覆盖 workflow authoring、workflow 浏览、run 操作、debug 观察和 settings 查看。
- 提供对话式 authoring session，把聊天、draft、lint、diff、publish 收敛到同一工作区中。
- 为 workflow 提供 cards、graph、spec、lint 四类同步视图，并支持 raw inspector 下钻到底层字段。
- 为 run 提供 timeline、node round、callback、artifact、context、logs 和最小人工介入操作。
- 暴露当前生效的运行时配置、provider/skill 绑定和命令模板来源，便于开发者观察和调试。
- 采用未来正式发布可继续沿用的成熟前端技术栈，同时保留 Python/FastAPI 后端领域模型和 runtime 实现。

**Non-Goals:**
- 不在本轮实现低代码拖拽优先的 workflow 编辑器。
- 不在本轮引入多租户、复杂 RBAC 或面向外部客户的权限体系。
- 不要求把 cards 设计成极简业务视图；第一阶段默认偏向信息密度和可观察性。
- 不在本轮重写 runtime 核心状态机、callback 协议或 artifact registry 的领域边界。
- 不要求立即完成完整分布式部署改造；本轮重点是工作台、authoring 和可观察性。

## Decisions

### 1. 采用独立正式前端应用，而不是继续扩展 FastAPI HTML 页面

**Decision**
- 新增一个独立前端应用，作为 Workflow Studio 的正式 UI 入口。
- 前端采用 `Next.js + React + TypeScript`。
- 使用 `TanStack Query` 处理服务端状态，使用 `React Flow` 展示 workflow graph，使用 `CodeMirror` 或 `Monaco` 承载 raw spec 编辑。
- 现有 FastAPI HTML 页面仅保留为过渡检查入口，不再承担主要产品职责。

**Rationale**
- 当前需求已经明显超出模板页面能够持续承载的范围，尤其是 authoring、graph、debug inspector、diff 和高密度状态页。
- 这套前端栈足够成熟，能够直接承接未来正式 release，而不是临时方案。
- 保持前后端解耦后，后端仍可围绕 canonical protocol objects 演进，前端只负责视图、交互与操作编排。

**Alternatives considered**
- 继续扩展 FastAPI HTML：实现快，但很快会在 graph、editor、state caching 和复杂调试面板上失控。
- 使用轻量 Python GUI/模板方案：适合演示，不适合作为正式产品前端。

### 2. 保持 `workflow spec` 为唯一真源，前端只消费和派生视图

**Decision**
- authoring session 的每次有效修订都落为 canonical draft spec。
- cards、graph、lint、workflow view、diff 结果都从同一份 draft 或已发布 spec 派生。
- 前端允许查看乃至编辑 raw spec，但所有编辑最终都回到 canonical draft spec，再由后端重算派生视图。

**Rationale**
- 这是当前设计最核心的稳定边界，能避免 Node Card、graph 或 draft form 变成第二份真源。
- 对开发者用户而言，下钻和直接编辑 canonical spec 是高价值能力，不应被前端抽象层屏蔽。

**Alternatives considered**
- 把 cards 作为独立编辑模型再反写 spec：交互上更顺手，但同步和一致性成本过高。
- 让前端本地推导 graph 和 lint：会把真源逻辑分散到前端，降低可验证性。

### 3. 引入 authoring session / draft 模型，承载对话式 workflow 创作

**Decision**
- 新增 `authoring session` 作为创作会话边界，记录 `Intent Brief`、聊天历史、当前 draft、修订号和 publish 记录。
- 新增 `authoring draft` 作为结构化产物，至少包括：
  - canonical `workflow spec`
  - 派生 `workflow view`
  - graph projection
  - lint / validation report
  - diff metadata
- publish 只接受当前 lint 通过的 draft，并产出标准 workflow version。

**Rationale**
- 需要把“聊天”与“可执行 workflow”之间插入一个可审查、可回滚、可发布的中间层。
- 这同时满足设计文档中的 `Intent Brief -> Workflow Spec -> Workflow View` 三层表达。

**Alternatives considered**
- 直接把聊天结果注册为 workflow version：过于脆弱，缺少审查和修订边界。
- 仅保存最终 spec，不保存 draft 历史：不利于理解变化来源，也不利于团队协作调试。

### 4. run 工作台采用聚合调试模型，而不是分散 API 列表

**Decision**
- 为 run 详情页提供聚合视图：run summary、graph/timeline、node round detail、callbacks、artifacts、logs/context、raw inspector。
- 后端为前端提供聚合读取接口，而不要求前端自行拼接大量细碎 API 响应。
- attention queue 作为独立视图存在，聚焦 `blocked`、`failed`、`timed_out`、`rework_limit` 等需要人工介入的运行。

**Rationale**
- 你当前最需要的是“直观看到底层设计和运行变化”，而不是跳转多个页面手工拼接上下文。
- 调试体验的关键在于围绕“一个 run / 一个 node round”聚合所有相关协议对象。

**Alternatives considered**
- 前端完全复用现有细粒度 API：实现看似简单，但前端状态和上下文拼装会非常脆弱。
- 只做表格列表，不做 timeline/round inspector：不利于定位 revise、blocked 和 artifact 版本变化。

### 5. settings 面板显示“生效值 + 来源”，服务开发者调试

**Decision**
- settings 页面不仅展示配置值，还展示其来源，例如 default、env、file、runtime override。
- 首批展示项至少包括：
  - executor / validator command template
  - provider / skill 绑定
  - storage root / backend
  - database 连接信息摘要
  - runtime defaults / guard defaults

**Rationale**
- 对内部团队而言，配置问题是最常见的调试来源之一；只显示结果而不显示来源，价值有限。
- 这类界面能显著降低“为什么这次 run 行为和预期不同”的排查成本。

**Alternatives considered**
- 只保留环境变量文档：不够直观，且无法反映当前实际生效值。

### 6. 实时更新先采用查询轮询，保留后续 SSE/WS 升级空间

**Decision**
- workflow studio 的运行态刷新先以前端轮询为主，重点覆盖 run summary、timeline、attention queue 和 node detail。
- API 设计上保留后续升级到 SSE 或 WebSocket 的空间，但不把实时通道作为本轮阻塞项。

**Rationale**
- 轮询更易落地，也更适合当前单机/小团队环境。
- 当前核心价值是统一工作台和可观察性，而不是高频实时协作。

**Alternatives considered**
- 立即引入 WebSocket：体验更即时，但会显著增加后端推送和状态同步复杂度。

## Risks / Trade-offs

- **[前端范围膨胀]** → 先收敛在 developer-first studio，不提前做低代码拖拽、多租户和高 polish 视觉。
- **[authoring 与 canonical spec 同步复杂]** → 强制所有派生视图由后端根据 canonical draft 重算，避免前端本地双真源。
- **[聚合调试接口与现有仓库结构耦合]** → 在 service 层增加只读聚合 DTO，不把前端查询逻辑直接塞进 repository。
- **[正式前端引入后 repo 结构变复杂]** → 明确前后端目录边界和共享类型边界，避免跨层引用。
- **[配置面板暴露信息较多]** → 面向内部团队先以可观察性优先，后续如有权限需求再补细粒度控制。
- **[轮询带来额外请求开销]** → 先控制刷新粒度和页面范围，确认瓶颈后再升级实时方案。

## Migration Plan

1. 新增前端应用骨架与基础依赖，建立 studio 路由、数据获取层和全局布局。
2. 扩展 FastAPI，补齐 authoring session、workflow projections、run debug aggregation、attention queue 和 settings snapshot 接口。
3. 先接入 workflow 浏览和 run 调试工作台，使现有 backend 闭环能够在新前端中完整观测。
4. 再补 authoring session、draft、lint、diff 和 publish 流程，把 workflow 创建入口迁移到新工作台。
5. 保留现有 CLI 和最小 HTML 页面作为回退入口，直到 studio 覆盖主要开发者路径。

回滚策略：
- 前端应用与新 API 可以逐步启用，不影响现有 CLI/runtime 基础流程。
- 若 studio 路径不稳定，可暂时退回现有 CLI + HTML inspection surface，后端 runtime 与 protocol objects 无需回滚。

## Open Questions

- authoring session 是否需要在首版就持久化完整聊天消息，还是先只保存结构化摘要与关键 prompt/result。
- 首版 raw spec 编辑是否允许直接保存，还是必须通过 lint / preview / confirm 三步提交。
- settings 面板中哪些配置只读，哪些允许在工作台内直接修改。
- 前端目录结构采用 `front/`、`web/` 还是 `apps/studio/`，需要在实现前统一约定。
