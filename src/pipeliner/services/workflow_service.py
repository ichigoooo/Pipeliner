from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from pipeliner.persistence.models import WorkflowVersionModel
from pipeliner.persistence.repositories import WorkflowRepository
from pipeliner.protocols.workflow import WorkflowSpec
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
                        WorkflowLintIssue("error", "unknown_dependency", f"节点 {node.node_id} 依赖了未知节点 {dep}")
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
                                f"节点 {node.node_id} 的输入引用了 {source.node_id}，但 depends_on 未声明",
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
                                f"节点 {node.node_id} 引用了 {source.node_id}.{source.output}，但该 output 不存在",
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
                issues.append(WorkflowLintIssue("error", "cycle_detected", f"检测到循环依赖，起点 {node_id}"))
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
