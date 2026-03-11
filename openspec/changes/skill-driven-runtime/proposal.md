## Why

当前仅 Authoring 阶段使用 Claude Skill，运行期 executor/validator 仍是无技能上下文的调度，导致执行与验收质量漂移、节点规范难以固化。需要把 Skill 驱动贯穿到运行期，并在创建/更新 workflow 时自动生成节点级 Skill。

## What Changes

- 运行期 executor/validator 调度切换到 `projects/<workflow_id>` 作为工作目录，确保 `.claude/skills` 被发现并可自动触发。
- Authoring/迭代时为每个节点的 `executor.skill` 与 `validators[].skill` 自动创建 Skill 目录与初始模板，并同步节点上下文参考文件。
- 增加 skill 命名合法性与唯一性校验，保证运行期可解析与可追踪。

## Capabilities

### New Capabilities
- `node-skill-packaging`: 为工作流节点自动生成并维护 executor/validator 的 Skill 包与上下文引用。

### Modified Capabilities
- `workflow-authoring`: 在保存/生成草案时同步节点级 Skill 与上下文文件。
- `workflow-iteration`: 在 rework/attention 迭代中更新节点级 Skill 与上下文文件。
- `authoring-agent`: 提示词与生成流程要求引用并使用节点级 Skill。
- `workflow-runtime`: 运行期调度在 project 目录下执行，确保 Skill 自动发现与触发。

## Impact

- 后端：AuthoringService/ProjectInitializer、AuthoringAgent、RunService/Executor/Validator、WorkflowSpec 校验与 lint。
- 前端：工作流创建/迭代后的提示与可视化（若已有 UI 提示则仅同步文案）。
- 兼容性：保持现有 API 与 spec 结构不变，但新增 skill 名称校验可能暴露历史不合法数据。
