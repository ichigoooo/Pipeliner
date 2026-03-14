from __future__ import annotations

from collections import Counter
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipeliner.protocols.guards import RuntimeGuards
from pipeliner.skills.naming import validate_skill_name
from pipeliner.types import GateMode

SUPPORTED_WORKFLOW_INPUT_TYPES = {"string", "number", "boolean", "enum", "file", "json"}


def derive_workflow_input_type(shape: str) -> str:
    normalized = shape.strip().lower()
    if normalized == "file":
        return "file"
    if normalized == "json":
        return "json"
    if normalized == "boolean":
        return "boolean"
    if normalized in {"number", "integer", "float"}:
        return "number"
    return "string"


def validate_workflow_input_value(
    *,
    name: str,
    input_type: str,
    value: Any,
    options: list[str] | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | None = None,
) -> None:
    if input_type in {"string", "file"}:
        if not isinstance(value, str):
            raise ValueError(f"workflow input {name} 必须是字符串")
        if min_length is not None and len(value) < min_length:
            raise ValueError(f"workflow input {name} 长度不能小于 {min_length}")
        if max_length is not None and len(value) > max_length:
            raise ValueError(f"workflow input {name} 长度不能大于 {max_length}")
        if pattern and re.fullmatch(pattern, value) is None:
            raise ValueError(f"workflow input {name} 不匹配要求的 pattern")
        return
    if input_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"workflow input {name} 必须是数字")
        numeric = float(value)
        if minimum is not None and numeric < minimum:
            raise ValueError(f"workflow input {name} 不能小于 {minimum}")
        if maximum is not None and numeric > maximum:
            raise ValueError(f"workflow input {name} 不能大于 {maximum}")
        return
    if input_type == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"workflow input {name} 必须是布尔值")
        return
    if input_type == "enum":
        if not isinstance(value, str):
            raise ValueError(f"workflow input {name} 必须是字符串枚举值")
        allowed = options or []
        if value not in allowed:
            raise ValueError(f"workflow input {name} 必须是以下值之一: {', '.join(allowed)}")
        return
    if input_type == "json":
        return
    raise ValueError(f"workflow input {name} 使用了未知类型 {input_type}")


class WorkflowMetadata(BaseModel):
    workflow_id: str
    title: str
    purpose: str
    version: str
    tags: list[str] = Field(default_factory=list)


class WorkflowInputSpec(BaseModel):
    name: str
    shape: str
    required: bool
    summary: str
    form: "WorkflowInputFormSpec | None" = None

    def normalized_descriptor(self) -> "WorkflowInputDescriptor":
        form = self.form or WorkflowInputFormSpec(type=derive_workflow_input_type(self.shape))
        source = "explicit" if self.form is not None else "derived"
        return WorkflowInputDescriptor(
            name=self.name,
            shape=self.shape,
            required=self.required,
            summary=self.summary,
            type=form.input_type,
            default=form.default,
            options=list(form.options),
            minimum=form.minimum,
            maximum=form.maximum,
            min_length=form.min_length,
            max_length=form.max_length,
            pattern=form.pattern,
            source=source,
        )


class WorkflowInputFormSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    input_type: str = Field(alias="type", serialization_alias="type")
    default: Any | None = None
    options: list[str] = Field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None

    @model_validator(mode="after")
    def validate_form(self) -> "WorkflowInputFormSpec":
        if self.input_type not in SUPPORTED_WORKFLOW_INPUT_TYPES:
            raise ValueError(
                f"workflow input type 仅支持: {', '.join(sorted(SUPPORTED_WORKFLOW_INPUT_TYPES))}"
            )
        if self.input_type == "enum":
            if not self.options:
                raise ValueError("enum workflow input 必须提供 options")
            if len(set(self.options)) != len(self.options):
                raise ValueError("enum workflow input 的 options 不能重复")
        elif self.options:
            raise ValueError("只有 enum workflow input 支持 options")

        if self.minimum is not None or self.maximum is not None:
            if self.input_type != "number":
                raise ValueError("只有 number workflow input 支持 minimum / maximum")
            if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
                raise ValueError("workflow input 的 minimum 不能大于 maximum")

        if self.min_length is not None or self.max_length is not None or self.pattern is not None:
            if self.input_type not in {"string", "file"}:
                raise ValueError("只有 string / file workflow input 支持长度或 pattern 约束")
            if (
                self.min_length is not None
                and self.max_length is not None
                and self.min_length > self.max_length
            ):
                raise ValueError("workflow input 的 min_length 不能大于 max_length")
            if self.pattern:
                re.compile(self.pattern)

        if self.default is not None:
            validate_workflow_input_value(
                name="default",
                input_type=self.input_type,
                value=self.default,
                options=self.options,
                minimum=self.minimum,
                maximum=self.maximum,
                min_length=self.min_length,
                max_length=self.max_length,
                pattern=self.pattern,
            )
        return self


class WorkflowInputDescriptor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    shape: str
    required: bool
    summary: str
    input_type: str = Field(alias="type", serialization_alias="type")
    default: Any | None = None
    options: list[str] = Field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    source: str


class WorkflowOutputRef(BaseModel):
    node_id: str
    output: str


class WorkflowOutputSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    source: WorkflowOutputRef = Field(alias="from", serialization_alias="from")
    shape: str
    required: bool
    summary: str


class NodeInputSource(BaseModel):
    kind: str
    name: str | None = None
    node_id: str | None = None
    output: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "NodeInputSource":
        if self.kind == "workflow_input":
            if not self.name:
                raise ValueError("workflow_input 必须声明 name")
        elif self.kind == "node_output":
            if not self.node_id or not self.output:
                raise ValueError("node_output 必须声明 node_id 与 output")
        else:
            raise ValueError("未知的 input source kind")
        return self


class NodeInputSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    source: NodeInputSource = Field(alias="from", serialization_alias="from")
    shape: str
    required: bool
    summary: str


class NodeOutputSpec(BaseModel):
    name: str
    shape: str
    summary: str


class NodeExecutorSpec(BaseModel):
    skill: str


class NodeValidatorSpec(BaseModel):
    validator_id: str
    skill: str


class NodeAcceptanceSpec(BaseModel):
    done_means: str
    pass_condition: list[str] = Field(default_factory=list)


class NodeGateSpec(BaseModel):
    mode: GateMode = GateMode.ALL_VALIDATORS_PASS


class NodeHandoffSpec(BaseModel):
    outputs: list[str] = Field(default_factory=list)


class WorkflowNodeSpec(BaseModel):
    node_id: str
    title: str
    purpose: str
    archetype: str
    depends_on: list[str] = Field(default_factory=list)
    inputs: list[NodeInputSpec] = Field(default_factory=list)
    outputs: list[NodeOutputSpec] = Field(default_factory=list)
    executor: NodeExecutorSpec
    validators: list[NodeValidatorSpec] = Field(default_factory=list)
    acceptance: NodeAcceptanceSpec
    gate: NodeGateSpec = Field(default_factory=NodeGateSpec)
    handoff: NodeHandoffSpec = Field(default_factory=NodeHandoffSpec)

    @model_validator(mode="after")
    def validate_names(self) -> "WorkflowNodeSpec":
        output_names = [item.name for item in self.outputs]
        if len(set(output_names)) != len(output_names):
            raise ValueError(f"节点 {self.node_id} 的 outputs 存在重复 name")
        validator_ids = [item.validator_id for item in self.validators]
        if len(set(validator_ids)) != len(validator_ids):
            raise ValueError(f"节点 {self.node_id} 的 validators 存在重复 validator_id")
        if not self.validators:
            raise ValueError(f"节点 {self.node_id} 至少需要一个 validator")
        return self


class WorkflowDefaults(BaseModel):
    runtime_guards: RuntimeGuards | None = None


class WorkflowSpec(BaseModel):
    schema_version: str
    metadata: WorkflowMetadata
    inputs: list[WorkflowInputSpec]
    outputs: list[WorkflowOutputSpec]
    nodes: list[WorkflowNodeSpec]
    defaults: WorkflowDefaults | None = None
    extensions: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_top_level(self) -> "WorkflowSpec":
        if not self.schema_version.startswith("pipeliner.workflow/v1"):
            raise ValueError("暂不支持的 workflow schema_version")
        node_ids = [node.node_id for node in self.nodes]
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("workflow nodes 存在重复 node_id")
        input_names = [item.name for item in self.inputs]
        if len(set(input_names)) != len(input_names):
            raise ValueError("workflow inputs 存在重复 name")
        output_names = [item.name for item in self.outputs]
        if len(set(output_names)) != len(output_names):
            raise ValueError("workflow outputs 存在重复 name")
        skill_names: list[str] = []
        for node in self.nodes:
            validate_skill_name(node.executor.skill, context=f"节点 {node.node_id} executor")
            skill_names.append(node.executor.skill)
            for validator in node.validators:
                validate_skill_name(
                    validator.skill,
                    context=f"节点 {node.node_id} validator {validator.validator_id}",
                )
                skill_names.append(validator.skill)
        duplicates = [name for name, count in Counter(skill_names).items() if count > 1]
        if duplicates:
            duplicates.sort()
            raise ValueError(f"workflow skills 存在重复: {', '.join(duplicates)}")
        return self

    def runtime_guards_or_default(self) -> RuntimeGuards:
        if self.defaults and self.defaults.runtime_guards:
            return self.defaults.runtime_guards
        return RuntimeGuards()
