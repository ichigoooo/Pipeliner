from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from pipeliner.persistence.models import AuthoringDraftModel, AuthoringMessageModel, AuthoringSessionModel
from pipeliner.persistence.repositories import AuthoringRepository
from pipeliner.services.errors import NotFoundError, ValidationError
from pipeliner.services.workflow_service import WorkflowService


class AuthoringService:
    def __init__(self, repo: AuthoringRepository, workflow_service: WorkflowService) -> None:
        self.repo = repo
        self.workflow_service = workflow_service

    def create_session(self, title: str, intent_brief: str) -> AuthoringSessionModel:
        import uuid

        session_id = f"session_{uuid.uuid4().hex[:8]}"
        session = self.repo.create_session(session_id, title, intent_brief)
        self.repo.add_message(session.id, role="user", content=intent_brief)
        bootstrap_spec = self._bootstrap_spec(title, intent_brief)
        projection = self.workflow_service.project_spec(bootstrap_spec)
        self.repo.create_draft(
            session_id=session.id,
            revision=1,
            spec_json=projection["canonical_spec"],
            workflow_view_json=projection["workflow_view"],
            graph_json=projection["graph"],
            lint_report_json=projection["lint_report"],
            lint_warnings=projection["lint_report"]["warnings"],
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
