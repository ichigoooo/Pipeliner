from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from pipeliner.persistence.models import AuthoringDraftModel, AuthoringMessageModel, AuthoringSessionModel
from pipeliner.persistence.repositories import AuthoringRepository
from pipeliner.services.authoring_agent import AuthoringAgent, AuthoringAgentError
from pipeliner.services.project_initializer import ProjectInitializer
from pipeliner.services.errors import NotFoundError, ValidationError
from pipeliner.services.workflow_service import WorkflowService


class AuthoringService:
    def __init__(
        self,
        repo: AuthoringRepository,
        workflow_service: WorkflowService,
        authoring_agent: AuthoringAgent | None = None,
        project_initializer: ProjectInitializer | None = None,
    ) -> None:
        self.repo = repo
        self.workflow_service = workflow_service
        self.authoring_agent = authoring_agent or AuthoringAgent()
        self.project_initializer = project_initializer or ProjectInitializer()

    def create_session(
        self,
        title: str,
        intent_brief: str,
        *,
        base_spec: dict[str, Any] | None = None,
        source: dict[str, Any] | None = None,
    ) -> AuthoringSessionModel:
        import uuid

        session_id = f"session_{uuid.uuid4().hex[:8]}"
        source_type = source.get("type") if isinstance(source, dict) else None
        source_payload = source.get("payload") if isinstance(source, dict) else None
        session = self.repo.create_session(
            session_id,
            title,
            intent_brief,
            source_type=source_type,
            source_payload=source_payload,
        )
        self.repo.add_message(session.id, role="user", content=intent_brief)
        bootstrap_spec = base_spec or self._bootstrap_spec(title, intent_brief)
        metadata = bootstrap_spec.get("metadata", {}) if isinstance(bootstrap_spec, dict) else {}
        workflow_id = metadata.get("workflow_id") or session_id
        normalized_spec = self.project_initializer.ensure_node_skills(workflow_id, bootstrap_spec)
        self.project_initializer.ensure_project(
            workflow_id,
            title=metadata.get("title") or title,
            intent_brief=metadata.get("purpose") or intent_brief,
            base_spec=normalized_spec,
        )
        projection = self.workflow_service.project_spec(normalized_spec)
        self.repo.create_draft(
            session_id=session.id,
            revision=1,
            spec_json=projection["canonical_spec"],
            workflow_view_json=projection["workflow_view"],
            graph_json=projection["graph"],
            lint_report_json=projection["lint_report"],
            lint_warnings=projection["lint_report"]["warnings"],
            source_json=self._build_source_payload(session),
        )
        return session

    def get_session(self, session_id: str) -> AuthoringSessionModel:
        session = self.repo.get_session(session_id)
        if session is None:
            raise NotFoundError(f"未找到 authoring session: {session_id}")
        return session

    def list_sessions(self, status: str | None = None) -> list[AuthoringSessionModel]:
        return self.repo.list_sessions(status)

    def save_draft(
        self,
        session_id: str,
        raw_spec: dict[str, Any],
        instruction: str | None = None,
    ) -> AuthoringDraftModel:
        session = self.get_session(session_id)
        metadata = raw_spec.get("metadata", {}) if isinstance(raw_spec, dict) else {}
        workflow_id = (
            metadata.get("workflow_id")
            or session.published_workflow_id
            or session_id
        )
        raw_spec = self.project_initializer.ensure_node_skills(workflow_id, raw_spec)
        self.project_initializer.ensure_project(
            workflow_id,
            title=metadata.get("title") or session.title,
            intent_brief=metadata.get("purpose") or session.intent_brief,
            base_spec=raw_spec,
        )

        try:
            # We attempt to validate to get lint warnings, but we still save it even if it has errors.
            # Drafts are allowed to be temporarily invalid.
            spec, warnings = self.workflow_service.validate_spec(raw_spec)
        except Exception as e:
            # If validation fails completely (e.g. pydantic error, or our custom WorkflowLintError),
            # we extract the messages.
            from pipeliner.services.workflow_service import WorkflowLintError
            if isinstance(e, WorkflowLintError):
                warnings = [f"[{issue.code}] {issue.message}" for issue in e.issues]
            else:
                warnings = [str(e)]

        projection = self.workflow_service.project_spec(raw_spec)
        latest_draft = self.repo.get_latest_draft(session_id)
        next_revision = (latest_draft.revision + 1) if latest_draft else 1
        if instruction:
            self.repo.add_message(session.id, role="user", content=instruction, revision=next_revision)

        return self.repo.create_draft(
            session_id=session.id,
            revision=next_revision,
            spec_json=raw_spec,
            workflow_view_json=projection["workflow_view"],
            graph_json=projection["graph"],
            lint_report_json=projection["lint_report"],
            lint_warnings=warnings,
            source_json=self._build_source_payload(session),
        )

    def continue_session(
        self,
        session_id: str,
        instruction: str,
        raw_spec: dict[str, Any],
    ) -> AuthoringDraftModel:
        return self.save_draft(session_id, raw_spec, instruction=instruction)

    def get_draft(self, session_id: str, revision: int) -> AuthoringDraftModel:
        draft = self.repo.get_draft(session_id, revision)
        if draft is None:
            raise NotFoundError(f"未找到 draft: {session_id}@{revision}")
        return draft

    def get_latest_draft(self, session_id: str) -> AuthoringDraftModel:
        draft = self.repo.get_latest_draft(session_id)
        if draft is None:
            raise NotFoundError(f"session {session_id} 尚无草稿")
        return draft

    def list_messages(self, session_id: str) -> list[AuthoringMessageModel]:
        self.get_session(session_id)
        return self.repo.list_messages(session_id)

    def list_drafts(self, session_id: str) -> list[AuthoringDraftModel]:
        self.get_session(session_id)
        return self.repo.list_drafts(session_id)

    def publish(self, session_id: str, revision: int) -> dict[str, Any]:
        session = self.get_session(session_id)
        draft = self.get_draft(session_id, revision)

        # Before publishing, we MUST validate and ensure no errors.
        try:
            spec, _warnings = self.workflow_service.validate_spec(draft.spec_json)
        except Exception as e:
            raise ValidationError(f"无法发布包含错误的 draft: {e}") from e

        # Register it with the workflow service
        version = self.workflow_service.register_spec(draft.spec_json)

        # Mark session as published
        session.status = "published"
        session.published_workflow_id = version.workflow_definition.workflow_id
        session.published_version = version.version
        session.published_revision = revision
        session.published_at = datetime.now(timezone.utc)
        self.repo.session.add(session)
        self.repo.session.flush()
        self.repo.add_message(
            session.id,
            role="system",
            content=f"Published {version.workflow_definition.workflow_id}@{version.version}",
            revision=revision,
        )

        return {
            "workflow_id": version.workflow_definition.workflow_id,
            "version": version.version,
            "session_id": session.id,
            "revision": revision,
        }

    def generate_draft(
        self,
        session_id: str,
        instruction: str,
        *,
        base_spec: dict[str, Any] | None = None,
    ) -> AuthoringDraftModel:
        session = self.get_session(session_id)
        current_spec = base_spec or self.get_latest_draft(session_id).spec_json
        metadata = current_spec.get("metadata", {}) if isinstance(current_spec, dict) else {}
        workflow_id = metadata.get("workflow_id") or session.published_workflow_id or session_id
        project_root = self.project_initializer.ensure_project(
            workflow_id,
            title=metadata.get("title"),
            intent_brief=metadata.get("purpose"),
            base_spec=current_spec,
        )
        try:
            result = self.authoring_agent.generate(
                session_id=session_id,
                intent_brief=session.intent_brief,
                instruction=instruction,
                base_spec=current_spec,
                project_dir=project_root,
            )
            result_spec = self.project_initializer.ensure_node_skills(workflow_id, result.spec_json)
            result_spec = self._ensure_depends_on(result_spec)
            try:
                self.workflow_service.validate_spec(result_spec)
            except Exception as exc:
                self.repo.create_generation_log(
                    session_id,
                    revision=None,
                    status="failed",
                    duration_ms=result.metadata.get("duration_ms"),
                    error_message=f"authoring spec invalid: {exc}",
                    metadata_json=result.metadata,
                )
                raise ValidationError(f"Claude 生成结果不是合法的 workflow spec: {exc}") from exc
            draft = self.save_draft(session_id, result_spec, instruction=instruction)
            self.repo.create_generation_log(
                session_id,
                revision=draft.revision,
                status="success",
                duration_ms=result.metadata.get("duration_ms"),
                error_message=None,
                metadata_json=result.metadata,
            )
            return draft
        except AuthoringAgentError as exc:
            self.repo.create_generation_log(
                session_id,
                revision=None,
                status="failed",
                duration_ms=exc.metadata.get("duration_ms"),
                error_message=str(exc),
                metadata_json=exc.metadata,
            )
            raise ValidationError(str(exc)) from exc

    def _ensure_depends_on(self, raw_spec: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(raw_spec, dict):
            return raw_spec
        raw_nodes = raw_spec.get("nodes")
        if not isinstance(raw_nodes, list):
            return raw_spec
        node_ids = {
            node.get("node_id")
            for node in raw_nodes
            if isinstance(node, dict) and node.get("node_id")
        }
        for node in raw_nodes:
            if not isinstance(node, dict):
                continue
            depends_on = node.get("depends_on")
            if not isinstance(depends_on, list):
                depends_on = []
            depends_set = {dep for dep in depends_on if isinstance(dep, str)}
            for input_spec in node.get("inputs", []):
                if not isinstance(input_spec, dict):
                    continue
                source = input_spec.get("from")
                if not isinstance(source, dict):
                    continue
                if source.get("kind") != "node_output":
                    continue
                upstream = source.get("node_id")
                if not upstream or upstream not in node_ids:
                    continue
                if upstream not in depends_set:
                    depends_on.append(upstream)
                    depends_set.add(upstream)
            node["depends_on"] = depends_on
        return raw_spec

    def _build_source_payload(self, session: AuthoringSessionModel) -> dict[str, Any] | None:
        if session.source_type or session.source_payload_json:
            return {
                "type": session.source_type,
                "payload": session.source_payload_json,
            }
        return None

    def _bootstrap_spec(self, title: str, intent_brief: str) -> dict[str, Any]:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "authoring-draft"
        return {
            "schema_version": "pipeliner.workflow/v1alpha1",
            "metadata": {
                "workflow_id": slug,
                "title": title,
                "purpose": intent_brief or f"Draft created for {title}",
                "version": "draft",
                "tags": ["authoring-session"],
            },
            "inputs": [],
            "outputs": [],
            "nodes": [],
        }
