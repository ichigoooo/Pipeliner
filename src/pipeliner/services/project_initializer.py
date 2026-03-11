from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeliner.config import Settings, get_settings
from pipeliner.skills.naming import (
    build_default_executor_skill,
    build_default_validator_skill,
    is_valid_skill_name,
    normalize_skill_name,
)


class ProjectInitializer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def ensure_project(
        self,
        workflow_id: str,
        *,
        title: str | None = None,
        intent_brief: str | None = None,
        base_spec: dict[str, Any] | None = None,
    ) -> Path:
        project_root = self.ensure_project_root(workflow_id)

        spec_path = project_root / "workflow.json"
        if not spec_path.exists():
            spec_payload = base_spec or self._bootstrap_spec(workflow_id, title, intent_brief)
            spec_path.write_text(
                json.dumps(spec_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        self._ensure_authoring_skills(project_root)
        return project_root

    def ensure_project_root(self, workflow_id: str) -> Path:
        project_root = self.settings.projects_root / workflow_id
        project_root.mkdir(parents=True, exist_ok=True)
        (project_root / ".claude" / "skills").mkdir(parents=True, exist_ok=True)
        return project_root

    def ensure_node_skills(self, workflow_id: str, spec: dict[str, Any]) -> dict[str, Any]:
        normalized_spec = self._apply_default_skill_names(workflow_id, spec)
        metadata = normalized_spec.get("metadata", {}) if isinstance(normalized_spec, dict) else {}
        effective_workflow_id = (
            metadata.get("workflow_id") if isinstance(metadata, dict) else None
        ) or workflow_id
        project_root = self.ensure_project_root(effective_workflow_id)
        nodes = normalized_spec.get("nodes", []) if isinstance(normalized_spec, dict) else []
        if not isinstance(nodes, list):
            return normalized_spec

        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            node_id = node.get("node_id") or f"node_{index + 1}"
            executor = node.get("executor", {})
            if isinstance(executor, dict):
                executor_skill = self._normalized_skill_name(executor.get("skill"))
                if executor_skill and is_valid_skill_name(executor_skill):
                    self._ensure_node_skill(
                        project_root,
                        executor_skill,
                        role="executor",
                        node_id=node_id,
                        validator_id=None,
                        metadata=metadata,
                        node_spec=node,
                    )
            validators = node.get("validators", [])
            if not isinstance(validators, list):
                continue
            for validator_index, validator in enumerate(validators):
                if not isinstance(validator, dict):
                    continue
                validator_id = validator.get("validator_id") or f"validator_{validator_index + 1}"
                validator_skill = self._normalized_skill_name(validator.get("skill"))
                if validator_skill and is_valid_skill_name(validator_skill):
                    self._ensure_node_skill(
                        project_root,
                        validator_skill,
                        role="validator",
                        node_id=node_id,
                        validator_id=validator_id,
                        metadata=metadata,
                        node_spec=node,
                    )
        return normalized_spec

    def _ensure_authoring_skills(self, project_root: Path) -> None:
        self._ensure_skill(
            project_root,
            "workflow-authoring",
            self._authoring_skill_content(),
            scripts={
                "validate_spec.py": self._validate_script_content(),
            },
        )
        self._ensure_skill(
            project_root,
            "workflow-iteration",
            self._iteration_skill_content(),
            scripts={
                "validate_spec.py": self._validate_script_content(),
            },
        )
        self._ensure_skill(
            project_root,
            "workflow-review",
            self._review_skill_content(),
            scripts={
                "validate_spec.py": self._validate_script_content(),
            },
        )

    def _ensure_skill(
        self,
        project_root: Path,
        skill_name: str,
        skill_content: str,
        *,
        scripts: dict[str, str] | None = None,
    ) -> None:
        skill_root = project_root / ".claude" / "skills" / skill_name
        skill_root.mkdir(parents=True, exist_ok=True)
        skill_file = skill_root / "SKILL.md"
        if not skill_file.exists():
            skill_file.write_text(skill_content, encoding="utf-8")
        if scripts:
            scripts_dir = skill_root / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            for name, content in scripts.items():
                script_path = scripts_dir / name
                if not script_path.exists():
                    script_path.write_text(content, encoding="utf-8")

    def _apply_default_skill_names(
        self,
        workflow_id: str,
        spec: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(spec, dict):
            return spec
        normalized_spec = copy.deepcopy(spec)
        metadata = normalized_spec.get("metadata", {})
        if isinstance(metadata, dict):
            workflow_id = metadata.get("workflow_id") or workflow_id
        nodes = normalized_spec.get("nodes", [])
        if not isinstance(nodes, list):
            return normalized_spec

        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            node_id = node.get("node_id") or f"node_{index + 1}"
            executor = node.get("executor")
            if not isinstance(executor, dict):
                executor = {}
                node["executor"] = executor
            executor_skill = self._normalized_skill_name(executor.get("skill"))
            if not executor_skill:
                executor["skill"] = build_default_executor_skill(workflow_id, node_id)

            validators = node.get("validators", [])
            if not isinstance(validators, list):
                continue
            for validator_index, validator in enumerate(validators):
                if not isinstance(validator, dict):
                    continue
                validator_id = validator.get("validator_id") or f"validator_{validator_index + 1}"
                validator_skill = self._normalized_skill_name(validator.get("skill"))
                if not validator_skill:
                    validator["skill"] = build_default_validator_skill(
                        workflow_id,
                        node_id,
                        validator_id,
                    )

        return normalized_spec

    def _normalized_skill_name(self, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = normalize_skill_name(value)
        return normalized or None

    def _ensure_node_skill(
        self,
        project_root: Path,
        skill_name: str,
        *,
        role: str,
        node_id: str,
        validator_id: str | None,
        metadata: dict[str, Any],
        node_spec: dict[str, Any],
    ) -> None:
        skill_content = self._node_skill_content(
            skill_name,
            role=role,
            node_id=node_id,
            validator_id=validator_id,
        )
        self._ensure_skill(project_root, skill_name, skill_content)
        references_dir = project_root / ".claude" / "skills" / skill_name / "references"
        references_dir.mkdir(parents=True, exist_ok=True)
        context_path = references_dir / "node_context.json"
        payload = self._node_context_payload(
            metadata,
            node_spec,
            role=role,
            node_id=node_id,
            validator_id=validator_id,
            skill_name=skill_name,
        )
        context_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _node_skill_content(
        self,
        skill_name: str,
        *,
        role: str,
        node_id: str,
        validator_id: str | None,
    ) -> str:
        validator_hint = f"（validator_id={validator_id}）" if validator_id else ""
        return (
            "---\n"
            f"name: {skill_name}\n"
            f"description: 节点 {node_id} 的 {role} skill{validator_hint}。\n"
            "---\n\n"
            f"# Node {role.capitalize()} Skill\n\n"
            f"- node_id: {node_id}\n"
            f"- role: {role}\n"
            f"- validator_id: {validator_id or ''}\n\n"
            "参考资料：\n"
            "- references/node_context.json\n"
        )

    def _node_context_payload(
        self,
        metadata: dict[str, Any],
        node_spec: dict[str, Any],
        *,
        role: str,
        node_id: str,
        validator_id: str | None,
        skill_name: str,
    ) -> dict[str, Any]:
        workflow_id = metadata.get("workflow_id") if isinstance(metadata, dict) else None
        return {
            "workflow": {
                "workflow_id": workflow_id,
                "title": metadata.get("title") if isinstance(metadata, dict) else None,
                "version": metadata.get("version") if isinstance(metadata, dict) else None,
            },
            "skill": {
                "name": skill_name,
                "role": role,
                "validator_id": validator_id,
            },
            "node_id": node_id,
            "node_spec": node_spec,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _bootstrap_spec(
        self,
        workflow_id: str,
        title: str | None,
        intent_brief: str | None,
    ) -> dict[str, Any]:
        return {
            "schema_version": "pipeliner.workflow/v1alpha1",
            "metadata": {
                "workflow_id": workflow_id,
                "title": title or workflow_id,
                "purpose": intent_brief or "Draft workflow specification",
                "version": "draft",
                "tags": ["authoring-session"],
            },
            "inputs": [],
            "outputs": [],
            "nodes": [],
            "defaults": {"runtime_guards": {"timeout": "30m", "max_rework_rounds": 3}},
            "extensions": {},
        }

    def _authoring_skill_content(self) -> str:
        return (
            "---\n"
            "name: workflow-authoring\n"
            "description: 创建或更新 workflow spec 并落盘到 projects/<workflow_id>/workflow.json。"
            "使用校验脚本保证结构正确。触发: 生成草案、更新 workflow、authoring。\n"
            "---\n\n"
            "# Workflow Authoring Skill\n\n"
            "适用场景：创建新的 workflow spec，或在现有 spec 上进行结构性修改。\n\n"
            "目录约定：\n"
            "- 工作目录：projects/<workflow_id>/\n"
            "- Spec 文件：workflow.json\n\n"
            "必须步骤：\n"
            "1. 读取 workflow.json，作为唯一真源进行修改。\n"
            "2. 按 instruction 更新 spec，不要输出 Markdown。\n"
            "3. 运行校验脚本：\n"
            "   PYTHONPATH=src python .claude/skills/workflow-authoring/scripts/validate_spec.py "
            "--input workflow.json --output workflow.json\n"
            "4. 运行回调脚本上报结果：\n"
            "   python scripts/authoring/report_callback.py "
            "--suggestion \"...\" --explanation \"...\" --risk \"...\"\n"
            "5. 输出更新后的 spec 与简短变更摘要。\n\n"
            "结构要求：\n"
            "- inputs/outputs/nodes/validators 必须是对象数组。\n"
            "- node.outputs 每个元素必须包含 name/shape/summary。\n"
            "- node 必须包含 acceptance {done_means, pass_condition}。\n"
        )

    def _iteration_skill_content(self) -> str:
        return (
            "---\n"
            "name: workflow-iteration\n"
            "description: 基于 rework brief 或 attention 上下文迭代 workflow spec。"
            "触发: 迭代、rework、attention 修订。\n"
            "---\n\n"
            "# Workflow Iteration Skill\n\n"
            "适用场景：收到 rework brief 或 attention run 反馈，需要修订现有 spec。\n\n"
            "必须步骤：\n"
            "1. 读取 workflow.json，保持 schema_version 不变。\n"
            "2. 根据 rework brief 精确修改节点/输入输出/验收标准。\n"
            "3. 运行校验脚本：\n"
            "   PYTHONPATH=src python .claude/skills/workflow-iteration/scripts/validate_spec.py "
            "--input workflow.json --output workflow.json\n"
            "4. 运行回调脚本上报结果：\n"
            "   python scripts/authoring/report_callback.py "
            "--suggestion \"...\" --explanation \"...\" --risk \"...\"\n"
            "5. 输出更新后的 spec 与迭代摘要（列出关键变更）。\n"
        )

    def _review_skill_content(self) -> str:
        return (
            "---\n"
            "name: workflow-review\n"
            "description: 审核 workflow spec 的结构与完整性，输出问题清单与修复建议。"
            "触发: review、lint、校验。\n"
            "---\n\n"
            "# Workflow Review Skill\n\n"
            "适用场景：需要检查 spec 合规性、质量、完整性。\n\n"
            "步骤：\n"
            "1. 读取 workflow.json。\n"
            "2. 运行校验脚本：\n"
            "   PYTHONPATH=src python .claude/skills/workflow-review/scripts/validate_spec.py "
            "--input workflow.json\n"
            "3. 运行回调脚本上报结果：\n"
            "   python scripts/authoring/report_callback.py "
            "--suggestion \"...\" --explanation \"...\" --risk \"...\"\n"
            "3. 输出错误/警告清单与修复建议。\n"
        )

    def _validate_script_content(self) -> str:
        return (
            "#!/usr/bin/env python3\n"
            "from __future__ import annotations\n\n"
            "import argparse\n"
            "import json\n"
            "from pathlib import Path\n\n"
            "from pipeliner.protocols.workflow import WorkflowSpec\n\n"
            "def main() -> int:\n"
            "    parser = argparse.ArgumentParser()\n"
            "    parser.add_argument('--input', required=True)\n"
            "    parser.add_argument('--output')\n"
            "    args = parser.parse_args()\n\n"
            "    payload = json.loads(Path(args.input).read_text(encoding='utf-8'))\n"
            "    spec = WorkflowSpec.model_validate(payload)\n"
            "    canonical = spec.model_dump(by_alias=True, mode='json')\n"
            "    if args.output:\n"
            "        Path(args.output).write_text(\n"
            "            json.dumps(canonical, ensure_ascii=False, indent=2),\n"
            "            encoding='utf-8',\n"
            "        )\n"
            "    print(json.dumps(canonical, ensure_ascii=False))\n"
            "    return 0\n\n"
            "if __name__ == '__main__':\n"
            "    raise SystemExit(main())\n"
        )
