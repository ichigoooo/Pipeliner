## Context

当前 Pipeliner 仅在 Authoring 阶段引入 Claude Skill，运行期 executor/validator 仍按通用命令模板在节点工作目录执行，缺少项目级 `.claude/skills` 发现与上下文约束，导致执行与验收质量不稳定。现有 `executor.skill` 与 `validators[].skill` 仅作为字符串引用，缺少对应 Skill 包的自动生成与维护机制。

## Goals / Non-Goals

**Goals:**
- 在 Authoring 与 Iteration 阶段自动生成并维护节点级 Skill 包与上下文引用。
- 运行期调度以 `projects/<workflow_id>` 为工作目录，使 Claude Code 自动发现 `.claude/skills` 并可触发对应 Skill。
- 增加 skill 命名合法性与唯一性校验，避免运行期无法解析或冲突。

**Non-Goals:**
- 不引入新的 workflow spec 结构字段或变更现有 API 形状。
- 不要求运行期强制手动触发 Skill（仍允许自动触发）。
- 不覆盖用户手工编辑的 `SKILL.md` 内容。

## Decisions

1) **以 `projects/<workflow_id>` 作为 Skill 发现根目录**  
选择在 Authoring/Run 统一使用项目目录作为工作目录，确保 Claude Code 自动发现 `.claude/skills`。替代方案是在运行时复制技能到 executor/validator workspace，但会引入同步与清理成本。

2) **节点级 Skill 自动生成采用“模板+上下文引用”**  
系统仅在缺失时创建 `SKILL.md` 初始模板，并维护 `references/node_context.json` 作为持续同步入口，避免覆盖用户自定义内容。替代方案是每次重写 `SKILL.md`，但会破坏手工编辑。

3) **Skill 命名采用“系统默认+允许覆盖”**  
系统可基于 workflow_id/node_id/validator_id 生成默认名，Authoring 允许覆盖为自定义名称；运行前进行格式与唯一性校验。完全手工命名将增加错误概率，完全系统命名会限制可读性与外部协作。

4) **仅新增 ADDED 需求，不修改既有 spec 结构**  
通过 delta specs 增加要求（生成、校验、运行目录），避免修改既有 spec 结构与历史行为，降低兼容性风险。

## Risks / Trade-offs

- [Risk] 历史 workflow 中的 skill 名称不合法 → 通过校验提示并提供兼容处理路径（不阻塞已有版本运行，或提供修复建议）。
- [Risk] 运行期切换工作目录影响相对路径输出 → 运行期仍使用绝对输出路径，避免依赖当前目录。
- [Risk] Skill 自动生成与用户手工编辑冲突 → 仅在缺失时创建 `SKILL.md`，后续只更新 `references/` 下的上下文文件。

## Migration Plan

- 增加兼容性校验但默认不破坏已有运行；对不合法 skill 名称给出清晰错误或修复建议。
- 运行期若发现 project 目录缺失，则最小化初始化目录结构，不覆盖已有内容。

## Open Questions

- 默认 skill 命名规则最终采用何种格式（如 `wf-<id>-<node>-exec` 等）。
- 是否在 Studio 中显式展示或编辑节点级 Skill 内容。
