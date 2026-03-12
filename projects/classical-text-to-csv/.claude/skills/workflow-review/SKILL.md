---
name: workflow-review
description: 审核 workflow spec 的结构与完整性，输出问题清单与修复建议。触发: review、lint、校验。
---

# Workflow Review Skill

适用场景：需要检查 spec 合规性、质量、完整性。

步骤：
1. 读取 workflow.json。
2. 运行校验脚本：
   PYTHONPATH=src python .claude/skills/workflow-review/scripts/validate_spec.py --input workflow.json
3. 运行回调脚本上报结果：
   python scripts/authoring/report_callback.py --suggestion "..." --explanation "..." --risk "..."
3. 输出错误/警告清单与修复建议。
