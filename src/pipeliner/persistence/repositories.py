from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from pipeliner.persistence.models import (
    ArtifactModel,
    AuthoringDraftModel,
    AuthoringMessageModel,
    CallbackEventModel,
    NodeRunModel,
    RunModel,
    WorkflowDefinitionModel,
    WorkflowVersionModel,
    AuthoringSessionModel,
)


class WorkflowRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_definition(self, workflow_id: str) -> WorkflowDefinitionModel | None:
        return self.session.scalar(
            select(WorkflowDefinitionModel).where(
                WorkflowDefinitionModel.workflow_id == workflow_id
            )
        )

    def get_version(self, workflow_id: str, version: str) -> WorkflowVersionModel | None:
        stmt: Select[tuple[WorkflowVersionModel]] = (
            select(WorkflowVersionModel)
            .join(WorkflowDefinitionModel)
            .where(WorkflowDefinitionModel.workflow_id == workflow_id)
            .where(WorkflowVersionModel.version == version)
        )
        return self.session.scalar(stmt)

    def create_or_update_definition(
        self,
        workflow_id: str,
        title: str,
        purpose: str,
    ) -> WorkflowDefinitionModel:
        definition = self.get_definition(workflow_id)
        if definition is None:
            definition = WorkflowDefinitionModel(
                workflow_id=workflow_id,
                title=title,
                purpose=purpose,
            )
            self.session.add(definition)
            self.session.flush()
            return definition
        definition.title = title
        definition.purpose = purpose
        self.session.add(definition)
        self.session.flush()
        return definition

    def create_version(
        self,
        definition: WorkflowDefinitionModel,
        *,
        version: str,
        schema_version: str,
        spec_json: dict,
        lint_warnings: list[str],
    ) -> WorkflowVersionModel:
        existing = self.get_version(definition.workflow_id, version)
        if existing is not None:
            raise ValueError(f"workflow {definition.workflow_id}@{version} 已存在")
        workflow_version = WorkflowVersionModel(
            workflow_definition_id=definition.id,
            version=version,
            schema_version=schema_version,
            spec_json=spec_json,
            lint_warnings=lint_warnings,
        )
        self.session.add(workflow_version)
        self.session.flush()
        return workflow_version

    def list_versions(self, workflow_id: str) -> list[WorkflowVersionModel]:
        stmt = (
            select(WorkflowVersionModel)
            .join(WorkflowDefinitionModel)
            .where(WorkflowDefinitionModel.workflow_id == workflow_id)
            .order_by(WorkflowVersionModel.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def list_definitions(self) -> list[WorkflowDefinitionModel]:
        stmt = select(WorkflowDefinitionModel).order_by(WorkflowDefinitionModel.updated_at.desc())
        return list(self.session.scalars(stmt))


class RunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_run(self, run: RunModel) -> RunModel:
        self.session.add(run)
        self.session.flush()
        return run

    def get_run(self, run_id: str) -> RunModel | None:
        return self.session.get(RunModel, run_id)

    def list_runs(self) -> list[RunModel]:
        stmt = select(RunModel).order_by(RunModel.created_at.desc())
        return list(self.session.scalars(stmt))

    def list_workflow_runs(self, workflow_id: str) -> list[RunModel]:
        stmt = (
            select(RunModel)
            .where(RunModel.workflow_id == workflow_id)
            .order_by(RunModel.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def list_runs_requiring_attention(self) -> list[RunModel]:
        stmt = (
            select(RunModel)
            .where(RunModel.status == "needs_attention")
            .order_by(RunModel.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def create_node_run(self, node_run: NodeRunModel) -> NodeRunModel:
        self.session.add(node_run)
        self.session.flush()
        return node_run

    def get_node_run(
        self,
        run_id: str,
        node_id: str,
        round_no: int,
    ) -> NodeRunModel | None:
        stmt = (
            select(NodeRunModel)
            .where(NodeRunModel.run_id == run_id)
            .where(NodeRunModel.node_id == node_id)
            .where(NodeRunModel.round_no == round_no)
        )
        return self.session.scalar(stmt)

    def get_latest_node_run(self, run_id: str, node_id: str) -> NodeRunModel | None:
        stmt = (
            select(NodeRunModel)
            .where(NodeRunModel.run_id == run_id)
            .where(NodeRunModel.node_id == node_id)
            .order_by(NodeRunModel.round_no.desc())
        )
        return self.session.scalars(stmt).first()

    def list_node_runs(self, run_id: str) -> list[NodeRunModel]:
        stmt = (
            select(NodeRunModel)
            .where(NodeRunModel.run_id == run_id)
            .order_by(NodeRunModel.node_id.asc(), NodeRunModel.round_no.asc())
        )
        return list(self.session.scalars(stmt))

    def list_latest_node_runs(self, run_id: str) -> dict[str, NodeRunModel]:
        node_runs = self.list_node_runs(run_id)
        latest: dict[str, NodeRunModel] = {}
        for node_run in node_runs:
            latest[node_run.node_id] = node_run
        return latest


class CallbackRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_event(self, event_id: str) -> CallbackEventModel | None:
        return self.session.get(CallbackEventModel, event_id)

    def create_event(self, event: CallbackEventModel) -> CallbackEventModel:
        self.session.add(event)
        self.session.flush()
        return event

    def list_node_round_events(
        self,
        run_id: str,
        node_id: str,
        round_no: int,
    ) -> list[CallbackEventModel]:
        stmt = (
            select(CallbackEventModel)
            .where(CallbackEventModel.run_id == run_id)
            .where(CallbackEventModel.node_id == node_id)
            .where(CallbackEventModel.round_no == round_no)
            .order_by(CallbackEventModel.processed_at.asc())
        )
        return list(self.session.scalars(stmt))

    def list_run_events(self, run_id: str) -> list[CallbackEventModel]:
        stmt = (
            select(CallbackEventModel)
            .where(CallbackEventModel.run_id == run_id)
            .order_by(CallbackEventModel.processed_at.asc())
        )
        return list(self.session.scalars(stmt))

    def get_validator_round_event(
        self,
        run_id: str,
        node_id: str,
        round_no: int,
        validator_id: str,
    ) -> CallbackEventModel | None:
        stmt = (
            select(CallbackEventModel)
            .where(CallbackEventModel.run_id == run_id)
            .where(CallbackEventModel.node_id == node_id)
            .where(CallbackEventModel.round_no == round_no)
            .where(CallbackEventModel.validator_id == validator_id)
        )
        return self.session.scalar(stmt)


class ArtifactRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_artifact(
        self,
        run_id: str,
        artifact_id: str,
        version: str,
    ) -> ArtifactModel | None:
        stmt = (
            select(ArtifactModel)
            .where(ArtifactModel.run_id == run_id)
            .where(ArtifactModel.artifact_id == artifact_id)
            .where(ArtifactModel.version == version)
        )
        return self.session.scalar(stmt)

    def create_artifact(self, artifact: ArtifactModel) -> ArtifactModel:
        self.session.add(artifact)
        self.session.flush()
        return artifact

    def list_run_artifacts(self, run_id: str) -> list[ArtifactModel]:
        stmt = (
            select(ArtifactModel)
            .where(ArtifactModel.run_id == run_id)
            .order_by(ArtifactModel.created_at.asc())
        )
        return list(self.session.scalars(stmt))


class AuthoringRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_session(self, session_id: str, title: str, intent_brief: str) -> AuthoringSessionModel:
        authoring_session = AuthoringSessionModel(
            id=session_id,
            title=title,
            intent_brief=intent_brief,
            status="active",
        )
        self.session.add(authoring_session)
        self.session.flush()
        return authoring_session

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        revision: int | None = None,
    ) -> AuthoringMessageModel:
        message = AuthoringMessageModel(
            session_id=session_id,
            revision=revision,
            role=role,
            content=content,
        )
        self.session.add(message)
        self.session.flush()
        return message

    def get_session(self, session_id: str) -> AuthoringSessionModel | None:
        return self.session.get(AuthoringSessionModel, session_id)

    def list_sessions(self, status: str | None = None) -> list[AuthoringSessionModel]:
        stmt = select(AuthoringSessionModel)
        if status:
            stmt = stmt.where(AuthoringSessionModel.status == status)
        stmt = stmt.order_by(AuthoringSessionModel.updated_at.desc())
        return list(self.session.scalars(stmt))

    def create_draft(
        self,
        session_id: str,
        revision: int,
        spec_json: dict,
        workflow_view_json: dict,
        graph_json: dict,
        lint_report_json: dict,
        lint_warnings: list[str],
    ) -> AuthoringDraftModel:
        draft = AuthoringDraftModel(
            session_id=session_id,
            revision=revision,
            spec_json=spec_json,
            workflow_view_json=workflow_view_json,
            graph_json=graph_json,
            lint_report_json=lint_report_json,
            lint_warnings=lint_warnings,
        )
        self.session.add(draft)
        self.session.flush()
        return draft

    def list_drafts(self, session_id: str) -> list[AuthoringDraftModel]:
        stmt = (
            select(AuthoringDraftModel)
            .where(AuthoringDraftModel.session_id == session_id)
            .order_by(AuthoringDraftModel.revision.asc())
        )
        return list(self.session.scalars(stmt))

    def get_draft(self, session_id: str, revision: int) -> AuthoringDraftModel | None:
        stmt = (
            select(AuthoringDraftModel)
            .where(AuthoringDraftModel.session_id == session_id)
            .where(AuthoringDraftModel.revision == revision)
        )
        return self.session.scalar(stmt)

    def get_latest_draft(self, session_id: str) -> AuthoringDraftModel | None:
        stmt = (
            select(AuthoringDraftModel)
            .where(AuthoringDraftModel.session_id == session_id)
            .order_by(AuthoringDraftModel.revision.desc())
        )
        return self.session.scalars(stmt).first()

    def list_messages(self, session_id: str) -> list[AuthoringMessageModel]:
        stmt = (
            select(AuthoringMessageModel)
            .where(AuthoringMessageModel.session_id == session_id)
            .order_by(AuthoringMessageModel.created_at.asc(), AuthoringMessageModel.id.asc())
        )
        return list(self.session.scalars(stmt))
