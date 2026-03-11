---
name: workflow-authoring
description: 创建或更新 workflow spec 并落盘到 projects/<workflow_id>/workflow.json。使用校验脚本保证结构正确。触发: 生成草案、更新 workflow、authoring。
---

# Workflow Authoring Skill

适用场景：创建新的 workflow spec，或在现有 spec 上进行结构性修改。

目录约定：
- 工作目录：projects/<workflow_id>/
- Spec 文件：workflow.json

必须步骤：
1. 读取 workflow.json，作为唯一真源进行修改。
2. 按 instruction 更新 spec，不要输出 Markdown。
3. 运行校验脚本：
   PYTHONPATH=src python .claude/skills/workflow-authoring/scripts/validate_spec.py --input workflow.json --output workflow.json
4. 输出更新后的 spec 与简短变更摘要。

结构要求：
- inputs/outputs/nodes/validators 必须是对象数组。
- node.outputs 每个元素必须包含 name/shape/summary。
- node 必须包含 acceptance {done_means, pass_condition}。
