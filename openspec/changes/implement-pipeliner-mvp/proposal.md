## Why

Pipeliner 的核心价值在于把工作流节点提升为“由 Skill 驱动的 agent 工作单”，并以明确交付物和独立 validator 验收来控制放行。当前设计已经收敛到可实施程度，需要尽快实现一个 MVP，把 workflow spec、callback、artifact manifest 与 runtime 闭环真正跑通，验证这套编排模型在本地单机环境下可用。

## What Changes

- 实现 Pipeliner 的 MVP 后端核心，支持基于 `workflow spec` 定义工作流并创建运行实例。
- 实现最小 Runtime，作为协调者、协议转发者与状态记录者，负责节点状态推进、executor/validator 串联、返工闭环、阻塞停机与人工介入边界控制，但不承担语义裁决职责。
- 实现 callback API，允许 executor 与 validator 通过统一协议回传执行结果、artifact 引用与 verdict。
- 实现 artifact registry 与本地工作目录约定，支持 artifact manifest 登记、不可变版本追踪和基于引用的节点间流转。
- 实现最小持久化层，记录 workflow version、run、node run、callback event 和 artifact 元数据。
- 提供最简单可用的操作入口与查看能力，用于触发 run、查看状态和排查问题；如提供 workflow 人类视图，也仅作为从 `workflow spec` 派生的只读视图。
- 保持 `workflow spec` 作为工作流机器真源；MVP 暂不实现完整的对话式工作流生成入口与高级 authoring 体验，但需保留后续接入 `Claude Code` 全局工作流生成 Skill 的边界。
- **BREAKING**: 当前 MVP 只覆盖 Python-first 后端核心与最小可用界面，不包含完整工作流编辑器、Node Card authoring、复杂 GUI/UX 或分布式执行能力。

## Capabilities

### New Capabilities
- `workflow-definition`: 定义、加载并校验 `workflow spec`，作为工作流机器真源，并为后续工作流生成入口保留稳定边界。
- `workflow-runtime`: 创建 workflow run，推进节点执行状态，并处理 executor → validator → pass/revise/blocked 的最小闭环；Runtime 仅负责转发、记录与推进，不负责语义裁决。
- `callback-reporting`: 接收 executor 与 validator 的 callback，支持幂等去重、结果登记与流程推进。
- `artifact-registry`: 管理 artifact manifest、不可变版本引用、本地文件存储与 run root 下的交付物流转。
- `run-operations`: 提供最小操作与查看能力，支持触发运行、查看 workflow/run/node 状态、查看 artifact 基本信息与人工介入点。

### Modified Capabilities
- None.

## Impact

- 新增 Python 后端核心模块，包括 workflow spec loader、runtime coordinator、callback receiver、artifact registry、state store 与基础 operator surface。
- 新增本地持久化与迁移，预计使用 `SQLite`、`SQLAlchemy`、`Alembic`。
- 新增 callback API 与相关协议模型，预计使用 `FastAPI` 与 `Pydantic v2`。
- 新增 run root / local_fs artifact 存储结构，以及与 callback、manifest、runtime guards 对齐的运行时实现。
- 明确 MVP 只围绕 canonical `workflow spec` 和运行时闭环实施，不在本轮引入独立的工作流编辑真源或复杂 authoring 系统。
- 需要把现有设计文档落为可执行实现边界，并在实现过程中补充最小测试与调试工具。
