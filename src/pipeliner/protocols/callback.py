from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from pipeliner.protocols.artifact import ArtifactRef
from pipeliner.types import ActorRole, ExecutionStatus, VerdictStatus


class CallbackActor(BaseModel):
    role: ActorRole
    validator_id: str | None = None


class CallbackExecution(BaseModel):
    status: ExecutionStatus
    message: str | None = None


class CallbackSubmission(BaseModel):
    artifacts: list[ArtifactRef] = Field(default_factory=list)


class CallbackVerdict(BaseModel):
    status: VerdictStatus
    target_artifacts: list[ArtifactRef] = Field(default_factory=list)
    summary: str | None = None


class ReworkItem(BaseModel):
    target: str
    problem: str
    expected: str


class ReworkBrief(BaseModel):
    must_fix: list[ReworkItem]
    preserve: list[str] = Field(default_factory=list)
    resubmit_instruction: str | None = None
    evidence: list[str] = Field(default_factory=list)


class NodeCallbackPayload(BaseModel):
    schema_version: str = "pipeliner.callback/v1alpha1"
    event_id: str
    sent_at: datetime
    run_id: str
    node_id: str
    round_no: int = Field(ge=1)
    actor: CallbackActor
    execution: CallbackExecution
    submission: CallbackSubmission | None = None
    verdict: CallbackVerdict | None = None
    rework_brief: ReworkBrief | None = None

    @model_validator(mode="after")
    def validate_role_payload(self) -> "NodeCallbackPayload":
        if not self.schema_version.startswith("pipeliner.callback/v1"):
            raise ValueError("暂不支持的 callback schema_version")

        if self.actor.role == ActorRole.EXECUTOR:
            if self.execution.status == ExecutionStatus.COMPLETED and self.submission is None:
                raise ValueError("executor completed callback 必须包含 submission")
            if self.verdict is not None or self.rework_brief is not None:
                raise ValueError("executor callback 不应包含 verdict 或 rework_brief")
        if self.actor.role == ActorRole.VALIDATOR:
            if not self.actor.validator_id:
                raise ValueError("validator callback 必须包含 validator_id")
            if self.verdict is None:
                raise ValueError("validator callback 必须包含 verdict")
            if self.submission is not None:
                raise ValueError("validator callback 不应包含 submission")
            if self.verdict.status == VerdictStatus.REVISE:
                if self.rework_brief is None or not self.rework_brief.must_fix:
                    raise ValueError("revise verdict 必须携带非空 must_fix")
            if self.verdict.status == VerdictStatus.PASS and self.rework_brief is not None:
                raise ValueError("pass verdict 不应携带 rework_brief")
        return self
