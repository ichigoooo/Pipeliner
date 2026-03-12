---
name: workflow-iteration
description: 基于 rework brief 或 attention 上下文迭代 workflow spec。触发: 迭代、rework、attention 修订。
---

# Workflow Iteration Skill

适用场景：收到 rework brief 或 attention run 反馈，需要修订现有 spec。

必须步骤：
1. 读取 workflow.json，保持 schema_version 不变。
2. 根据 rework brief 精确修改节点/输入输出/验收标准。
3. 运行校验脚本：
   PYTHONPATH=src python .claude/skills/workflow-iteration/scripts/validate_spec.py --input workflow.json --output workflow.json
4. 运行回调脚本上报结果：
   python scripts/authoring/report_callback.py --suggestion "..." --explanation "..." --risk "..."
5. 输出更新后的 spec 与迭代摘要（列出关键变更）。
