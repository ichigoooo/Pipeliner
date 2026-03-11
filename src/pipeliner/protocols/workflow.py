from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipeliner.protocols.guards import RuntimeGuards
from pipeliner.skills.naming import validate_skill_name
from pipeliner.types import GateMode


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
