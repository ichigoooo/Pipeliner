from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pipeliner.persistence.models import WorkflowDefinitionModel, WorkflowVersionModel
from pipeliner.persistence.repositories import WorkflowRepository
from pipeliner.protocols.workflow import WorkflowSpec, validate_workflow_input_value
from pipeliner.services.errors import NotFoundError, ValidationError


@dataclass(slots=True)
class WorkflowLintIssue:
    severity: str
    code: str
    message: str


class WorkflowLintError(ValidationError):
    def __init__(self, issues: list[WorkflowLintIssue]) -> None:
        self.issues = issues
        message = "; ".join(f"[{issue.code}] {issue.message}" for issue in issues)
        super().__init__(message)


class WorkflowService:
    def __init__(self, repo: WorkflowRepository) -> None:
        self.repo = repo

    def load_raw_file(self, path: str | Path) -> dict:
        file_path = Path(path)
        content = file_path.read_text(encoding="utf-8")
        if file_path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(content)
        return json.loads(content)

    def validate_spec(self, raw_spec: dict) -> tuple[WorkflowSpec, list[str]]:
        spec = WorkflowSpec.model_validate(raw_spec)
        issues = self._lint(spec)
        errors = [issue for issue in issues if issue.severity == "error"]
        if errors:
            raise WorkflowLintError(errors)
        warnings = [issue.message for issue in issues if issue.severity == "warning"]
        return spec, warnings

    def register_spec(self, raw_spec: dict) -> WorkflowVersionModel:
        spec, warnings = self.validate_spec(raw_spec)
        definition = self.repo.create_or_update_definition(
            workflow_id=spec.metadata.workflow_id,
            title=spec.metadata.title,
            purpose=spec.metadata.purpose,
        )
        return self.repo.create_version(
            definition,
            version=spec.metadata.version,
            schema_version=spec.schema_version,
            spec_json=spec.model_dump(by_alias=True, mode="json"),
            lint_warnings=warnings,
        )

    def get_version(self, workflow_id: str, version: str) -> WorkflowVersionModel:
        workflow_version = self.repo.get_version(workflow_id, version)
        if workflow_version is None:
            raise NotFoundError(f"未找到 workflow version: {workflow_id}@{version}")
        return workflow_version

    def load_spec_model(self, workflow_id: str, version: str) -> WorkflowSpec:
        workflow_version = self.get_version(workflow_id, version)
        return WorkflowSpec.model_validate(workflow_version.spec_json)

    def list_workflows(self) -> list[WorkflowDefinitionModel]:
        return self.repo.list_definitions()

    def validate_run_inputs(self, spec: WorkflowSpec, inputs: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        missing: list[str] = []

        for item in spec.inputs:
            descriptor = item.normalized_descriptor()
            value = inputs.get(item.name)
            if value is None and descriptor.default is not None:
                value = descriptor.default
            if value is None:
                if descriptor.required:
                    missing.append(item.name)
                continue
            try:
                validate_workflow_input_value(
                    name=item.name,
                    input_type=descriptor.input_type,
                    value=value,
                    options=descriptor.options,
                    minimum=descriptor.minimum,
                    maximum=descriptor.maximum,
                    min_length=descriptor.min_length,
                    max_length=descriptor.max_length,
                    pattern=descriptor.pattern,
                )
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
            normalized[item.name] = value

        if missing:
            raise ValidationError(f"缺少必填 workflow inputs: {', '.join(missing)}")
        return normalized

    def project_spec(self, raw_spec: dict[str, Any]) -> dict[str, Any]:
        lint_errors: list[str] = []
        warnings: list[str] = []
        validated_spec: WorkflowSpec | None = None
        canonical_spec = raw_spec

        try:
            validated_spec, warnings = self.validate_spec(raw_spec)
            canonical_spec = validated_spec.model_dump(by_alias=True, mode="json")
        except WorkflowLintError as exc:
            lint_errors = [f"[{issue.code}] {issue.message}" for issue in exc.issues]
        except Exception as exc:  # pragma: no cover - fallback for malformed payloads
            lint_errors = [str(exc)]

        spec_data = canonical_spec if isinstance(canonical_spec, dict) else raw_spec
        metadata = spec_data.get("metadata", {})
        raw_nodes = spec_data.get("nodes", []) if isinstance(spec_data.get("nodes", []), list) else []
        input_descriptors = (
            [item.normalized_descriptor().model_dump(by_alias=True, mode="json") for item in validated_spec.inputs]
            if validated_spec is not None
            else []
        )

        cards: list[dict[str, Any]] = []
        graph_nodes: list[dict[str, Any]] = []
        graph_edges: list[dict[str, Any]] = []
        for index, node in enumerate(raw_nodes):
            node_id = node.get("node_id", f"node_{index + 1}")
            depends_on = node.get("depends_on", [])
            inputs = node.get("inputs", [])
            outputs = node.get("outputs", [])
            validators = node.get("validators", [])
            executor = node.get("executor", {})
            if not isinstance(depends_on, list):
                depends_on = []
            if not isinstance(inputs, list):
                inputs = []
            if not isinstance(outputs, list):
                outputs = []
            if not isinstance(validators, list):
                validators = []
            if not isinstance(executor, dict):
                executor = {}
            cards.append(
                {
                    "node_id": node_id,
                    "title": node.get("title", node_id),
                    "purpose": node.get("purpose", ""),
                    "archetype": node.get("archetype", ""),
                    "depends_on": depends_on,
                    "executor_skill": executor.get("skill"),
                    "validator_ids": [item.get("validator_id") for item in validators],
                    "input_names": [item.get("name") for item in inputs],
                    "output_names": [item.get("name") for item in outputs],
                    "done_means": node.get("acceptance", {}).get("done_means"),
                    "raw": node,
                }
            )
            graph_nodes.append(
                {
                    "id": node_id,
                    "type": "workflowNode",
                    "data": {
                        "label": node.get("title", node_id),
                        "node_id": node_id,
                        "spec": node,
                    },
                    "position": {"x": 80 + (index % 3) * 260, "y": 80 + (index // 3) * 180},
                }
            )
            for dep in depends_on:
                graph_edges.append(
                    {
                        "id": f"{dep}->{node_id}",
                        "source": dep,
                        "target": node_id,
                        "type": "smoothstep",
                        "animated": True,
                    }
                )

        return {
            "canonical_spec": canonical_spec,
            "workflow_view": {
                "metadata": {
                    "workflow_id": metadata.get("workflow_id"),
                    "title": metadata.get("title"),
                    "purpose": metadata.get("purpose"),
                    "version": metadata.get("version"),
                    "tags": metadata.get("tags", []),
                },
                "inputs": spec_data.get("inputs", []),
                "input_descriptors": input_descriptors,
                "outputs": spec_data.get("outputs", []),
                "cards": cards,
            },
            "graph": {
                "nodes": graph_nodes,
                "edges": graph_edges,
            },
            "lint_report": {
                "warnings": warnings,
                "errors": lint_errors,
                "blocking": bool(lint_errors),
            },
        }

    def _lint(self, spec: WorkflowSpec) -> list[WorkflowLintIssue]:
        issues: list[WorkflowLintIssue] = []
        node_map = {node.node_id: node for node in spec.nodes}
        workflow_input_names = {item.name for item in spec.inputs}

        for node in spec.nodes:
            declared_deps = set(node.depends_on)
            referenced_upstreams: set[str] = set()
            for dep in node.depends_on:
                if dep not in node_map:
                    issues.append(
                        WorkflowLintIssue(
                            "error",
                            "unknown_dependency",
                            f"节点 {node.node_id} 依赖了未知节点 {dep}",
                        )
                    )
            for input_spec in node.inputs:
                source = input_spec.source
                if source.kind == "workflow_input":
                    if source.name not in workflow_input_names:
                        issues.append(
                            WorkflowLintIssue(
                                "error",
                                "unknown_workflow_input",
                                f"节点 {node.node_id} 引用了未知 workflow input {source.name}",
                            )
                        )
                if source.kind == "node_output":
                    referenced_upstreams.add(source.node_id or "")
                    if source.node_id not in declared_deps:
                        issues.append(
                            WorkflowLintIssue(
                                "error",
                                "missing_depends_on",
                                (
                                    f"节点 {node.node_id} 的输入引用了 "
                                    f"{source.node_id}，但 depends_on 未声明"
                                ),
                            )
                        )
                    upstream = node_map.get(source.node_id or "")
                    if upstream is None:
                        issues.append(
                            WorkflowLintIssue(
                                "error",
                                "unknown_upstream",
                                f"节点 {node.node_id} 引用了未知上游 {source.node_id}",
                            )
                        )
                    elif source.output not in {output.name for output in upstream.outputs}:
                        issues.append(
                            WorkflowLintIssue(
                                "error",
                                "unknown_upstream_output",
                                (
                                    f"节点 {node.node_id} 引用了 "
                                    f"{source.node_id}.{source.output}，但该 output 不存在"
                                ),
                            )
                        )
            extra_deps = sorted(declared_deps - referenced_upstreams)
            for dep in extra_deps:
                issues.append(
                    WorkflowLintIssue(
                        "warning",
                        "unused_dependency",
                        f"节点 {node.node_id} 声明了 depends_on {dep}，但没有任何输入实际引用它",
                    )
                )

        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(node_id: str) -> None:
            if node_id in visiting:
                issues.append(
                    WorkflowLintIssue(
                        "error",
                        "cycle_detected",
                        f"检测到循环依赖，起点 {node_id}",
                    )
                )
                return
            if node_id in visited:
                return
            visiting.add(node_id)
            for dep in node_map[node_id].depends_on:
                if dep in node_map:
                    dfs(dep)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in node_map:
            dfs(node_id)

        for output in spec.outputs:
            upstream = node_map.get(output.source.node_id)
            if upstream is None:
                issues.append(
                    WorkflowLintIssue(
                        "error",
                        "unknown_workflow_output_node",
                        f"workflow output {output.name} 引用了未知节点 {output.source.node_id}",
                    )
                )
                continue
            if output.source.output not in {item.name for item in upstream.outputs}:
                issues.append(
                    WorkflowLintIssue(
                        "error",
                        "unknown_workflow_output_mapping",
                        f"workflow output {output.name} 引用了未知 output {output.source.output}",
                    )
                )
        return issues
