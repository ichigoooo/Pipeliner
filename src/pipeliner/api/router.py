from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from pipeliner.db import Database
from pipeliner.executor import ClaudeExecutorDispatcher, ClaudeValidatorDispatcher
from pipeliner.persistence.repositories import (
    ArtifactRepository,
    CallbackRepository,
    RunRepository,
    WorkflowRepository,
    AuthoringRepository,
)
from pipeliner.protocols.artifact import ArtifactManifest
from pipeliner.protocols.callback import NodeCallbackPayload
from pipeliner.runtime import RuntimeCoordinator
from pipeliner.services.artifact_service import ArtifactService
from pipeliner.services.errors import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from pipeliner.config import get_settings
from pipeliner.services.run_driver import RunDriver
from pipeliner.services.run_service import RunService
from pipeliner.services.workflow_service import WorkflowService
from pipeliner.services.authoring_agent import AuthoringAgent
from pipeliner.services.authoring_service import AuthoringService
from pipeliner.services.claude_call import ClaudeCallStore
from pipeliner.services.settings_service import SettingsService
from pipeliner.services.preview_service import PreviewService
from pipeliner.services.project_initializer import ProjectInitializer
from pipeliner.services.report_service import ReportService
from pipeliner.ui.views import render_index, render_run_view, render_workflow_view

router = APIRouter()


class WorkflowRegisterRequest(BaseModel):
    spec: dict[str, Any]


class RunCreateRequest(BaseModel):
    workflow_id: str
    version: str
    inputs: dict[str, Any] = Field(default_factory=dict)


class StopRunRequest(BaseModel):
    reason: str = "manual_stop"


class ExecutorDispatchRequest(BaseModel):
    round_no: int | None = None
    command_template: str | None = None


class ValidatorDispatchRequest(BaseModel):
    round_no: int | None = None
    command_template: str | None = None


class AuthoringSessionCreateRequest(BaseModel):
    title: str
    intent_brief: str


class AuthoringDraftSaveRequest(BaseModel):
    spec: dict[str, Any]
    instruction: str | None = None


class AuthoringGenerateRequest(BaseModel):
    instruction: str
    spec: dict[str, Any] | None = None
    claude_call_id: str | None = None


class AuthoringSessionFromVersionRequest(BaseModel):
    workflow_id: str
    version: str
    title: str | None = None
    intent_brief: str | None = None


class AuthoringSessionFromRunRequest(BaseModel):
    run_id: str
    node_id: str | None = None
    round_no: int | None = None
    title: str | None = None
    intent_brief: str | None = None


class RunRetryRequest(BaseModel):
    rework_brief: dict[str, Any] | None = None


class AuthoringReportRequest(BaseModel):
    session_id: str
    suggestion: str
    explanation: str
    risk: str
    source: dict[str, Any] | None = None


class RunDriveRequest(BaseModel):
    max_steps: int = Field(default=100, ge=1, le=500)
    executor_command_template: str | None = None
    validator_command_template: str | None = None


def get_database(request: Request) -> Database:
    return request.app.state.db


DatabaseDep = Annotated[Database, Depends(get_database)]


def get_session(db: DatabaseDep):
    with db.session() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def _workflow_service(session: Session) -> WorkflowService:
    return WorkflowService(WorkflowRepository(session))


def _authoring_service(session: Session, request: Request) -> AuthoringService:
    return AuthoringService(
        AuthoringRepository(session),
        WorkflowService(WorkflowRepository(session)),
        authoring_agent=AuthoringAgent(request.app.state.settings),
        project_initializer=ProjectInitializer(request.app.state.settings),
    )


def _run_driver(session: Session, request: Request) -> RunDriver:
    return RunDriver(
        RunRepository(session),
        WorkflowRepository(session),
        CallbackRepository(session),
        ArtifactRepository(session),
        request.app.state.settings,
    )


def _preview_service(session: Session, request: Request) -> PreviewService:
    return PreviewService(
        RunRepository(session),
        ArtifactRepository(session),
        request.app.state.settings,
    )


def _run_service(session: Session, request: Request) -> RunService:
    return RunService(
        RunRepository(session),
        WorkflowRepository(session),
        ArtifactRepository(session),
        request.app.state.settings,
    )


def _settings_service(session: Session, request: Request) -> SettingsService:
    return SettingsService(
        request.app.state.settings,
        WorkflowRepository(session),
    )


def _runtime_coordinator(session: Session, request: Request) -> RuntimeCoordinator:
    return RuntimeCoordinator(
        RunRepository(session),
        WorkflowRepository(session),
        CallbackRepository(session),
        ArtifactRepository(session),
        request.app.state.settings,
    )


def _artifact_service(session: Session, request: Request) -> ArtifactService:
    return ArtifactService(
        ArtifactRepository(session),
        RunRepository(session),
        request.app.state.settings,
    )


def _claude_call_store(request: Request) -> ClaudeCallStore:
    return ClaudeCallStore(request.app.state.settings)


def _executor_dispatcher(
    session: Session,
    request: Request,
) -> ClaudeExecutorDispatcher:
    return ClaudeExecutorDispatcher(
        RunRepository(session),
        WorkflowRepository(session),
        CallbackRepository(session),
        ArtifactRepository(session),
        request.app.state.settings,
    )


def _validator_dispatcher(
    session: Session,
    request: Request,
) -> ClaudeValidatorDispatcher:
    return ClaudeValidatorDispatcher(
        RunRepository(session),
        WorkflowRepository(session),
        CallbackRepository(session),
        ArtifactRepository(session),
        request.app.state.settings,
    )


def _authoring_draft_payload(draft, claude_call_id: str | None = None) -> dict[str, Any]:
    payload = {
        "session_id": draft.session_id,
        "revision": draft.revision,
        "spec_json": draft.spec_json,
        "workflow_view": draft.workflow_view_json,
        "graph": draft.graph_json,
        "lint_report": draft.lint_report_json,
        "lint_warnings": draft.lint_warnings,
        "workflow_id": draft.spec_json.get("metadata", {}).get("workflow_id"),
        "version": draft.spec_json.get("metadata", {}).get("version"),
        "source": draft.source_json,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
    }
    if claude_call_id is not None:
        payload["claude_call_id"] = claude_call_id
    return payload


def _extract_claude_call_id(metadata: dict[str, Any] | None) -> str | None:
    if not isinstance(metadata, dict):
        return None
    call_id = metadata.get("claude_call_id")
    if isinstance(call_id, str) and call_id:
        return call_id
    return None


def _build_generation_call_map(
    repo: AuthoringRepository,
    session_id: str,
) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for log in repo.list_generation_logs(session_id):
        revision = log.revision
        if revision is None or revision in mapping:
            continue
        call_id = _extract_claude_call_id(log.metadata_json)
        if call_id:
            mapping[revision] = call_id
    return mapping


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse)
def ui_index(request: Request, session: SessionDep) -> str:
    run_service = _run_service(session, request)
    attention_runs = [
        {
            "run_id": run.id,
            "workflow_id": run.workflow_id,
            "status": run.status,
            "stop_reason": run.stop_reason,
        }
        for run in run_service.run_repo.list_runs_requiring_attention()
    ]
    return render_index(attention_runs)


@router.post("/api/authoring/sessions")
def create_authoring_session(
    request_body: AuthoringSessionCreateRequest,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _authoring_service(session, request)
    authoring_session = service.create_session(
        title=request_body.title,
        intent_brief=request_body.intent_brief,
    )
    latest_draft = service.get_latest_draft(authoring_session.id)
    return {
        "session_id": authoring_session.id,
        "title": authoring_session.title,
        "status": authoring_session.status,
        "latest_revision": latest_draft.revision,
    }


@router.post("/api/authoring/sessions/from-version")
def create_authoring_session_from_version(
    request_body: AuthoringSessionFromVersionRequest,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    workflow_repo = WorkflowRepository(session)
    workflow_version = workflow_repo.get_version(
        request_body.workflow_id,
        request_body.version,
    )
    if workflow_version is None:
        raise NotFoundError(
            f"未找到 workflow version: {request_body.workflow_id}@{request_body.version}"
        )
    spec = workflow_version.spec_json
    metadata = spec.get("metadata", {}) if isinstance(spec, dict) else {}
    title = request_body.title or f"{metadata.get('title') or request_body.workflow_id} Iteration"
    intent_brief = (
        request_body.intent_brief
        or metadata.get("purpose")
        or f"Iterate {request_body.workflow_id}@{request_body.version}"
    )
    source = {
        "type": "workflow_version",
        "payload": {
            "workflow_id": request_body.workflow_id,
            "version": request_body.version,
            "created_at": workflow_version.created_at.isoformat()
            if workflow_version.created_at
            else None,
        },
    }
    service = _authoring_service(session, request)
    authoring_session = service.create_session(
        title=title,
        intent_brief=intent_brief,
        base_spec=spec,
        source=source,
    )
    latest_draft = service.get_latest_draft(authoring_session.id)
    return {
        "session_id": authoring_session.id,
        "title": authoring_session.title,
        "status": authoring_session.status,
        "latest_revision": latest_draft.revision,
        "source": source,
    }


@router.post("/api/authoring/sessions/from-run")
def create_authoring_session_from_run(
    request_body: AuthoringSessionFromRunRequest,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    run_repo = RunRepository(session)
    run = run_repo.get_run(request_body.run_id)
    if run is None:
        raise NotFoundError(f"未找到 run: {request_body.run_id}")
    workflow_version = WorkflowRepository(session).get_version(
        run.workflow_id,
        run.workflow_version,
    )
    if workflow_version is None:
        raise NotFoundError(f"未找到 workflow version: {run.workflow_id}@{run.workflow_version}")

    selected_node = None
    if request_body.node_id:
        if request_body.round_no is not None:
            selected_node = run_repo.get_node_run(
                run.id,
                request_body.node_id,
                request_body.round_no,
            )
        else:
            selected_node = run_repo.get_latest_node_run(run.id, request_body.node_id)
        if selected_node is None:
            raise NotFoundError(f"未找到 node run: {request_body.node_id}")
    else:
        attention_statuses = {
            "blocked",
            "failed",
            "timed_out",
            "rework_limit",
            "stopped",
        }
        latest = run_repo.list_latest_node_runs(run.id)
        attention_nodes = [item for item in latest.values() if item.status in attention_statuses]
        attention_nodes.sort(key=lambda item: item.updated_at or item.created_at)
        selected_node = attention_nodes[-1] if attention_nodes else None

    if selected_node is None:
        raise ValidationError("未找到需要迭代的 attention 节点")

    spec = workflow_version.spec_json
    metadata = spec.get("metadata", {}) if isinstance(spec, dict) else {}
    title = request_body.title or f"{metadata.get('title') or run.workflow_id} Iteration"
    intent_brief = (
        request_body.intent_brief
        or metadata.get("purpose")
        or f"Iterate {run.workflow_id}@{run.workflow_version} from run {run.id}"
    )
    source = {
        "type": "attention_run",
        "payload": {
            "run_id": run.id,
            "workflow_id": run.workflow_id,
            "version": run.workflow_version,
            "node_id": selected_node.node_id,
            "round_no": selected_node.round_no,
            "status": selected_node.status,
            "rework_brief": selected_node.rework_brief_json,
            "stop_reason": selected_node.stop_reason,
        },
    }
    service = _authoring_service(session, request)
    authoring_session = service.create_session(
        title=title,
        intent_brief=intent_brief,
        base_spec=spec,
        source=source,
    )
    latest_draft = service.get_latest_draft(authoring_session.id)
    return {
        "session_id": authoring_session.id,
        "title": authoring_session.title,
        "status": authoring_session.status,
        "latest_revision": latest_draft.revision,
        "source": source,
    }


@router.get("/api/authoring/sessions")
def list_authoring_sessions(
    request: Request,
    session: SessionDep,
    status: str | None = None,
) -> dict[str, Any]:
    service = _authoring_service(session, request)
    sessions = service.list_sessions(status=status)
    return {
        "sessions": [
            {
                "session_id": s.id,
                "title": s.title,
                "status": s.status,
                "latest_revision": s.drafts[-1].revision if s.drafts else None,
                "draft_count": len(s.drafts),
                "published_workflow_id": s.published_workflow_id,
                "published_version": s.published_version,
                "published_revision": s.published_revision,
                "source": (
                    {"type": s.source_type, "payload": s.source_payload_json}
                    if s.source_type or s.source_payload_json
                    else None
                ),
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ]
    }


@router.get("/api/authoring/sessions/{session_id}")
def get_authoring_session(
    session_id: str,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _authoring_service(session, request)
    authoring_session = service.get_session(session_id)
    return {
        "session_id": authoring_session.id,
        "title": authoring_session.title,
        "intent_brief": authoring_session.intent_brief,
        "status": authoring_session.status,
        "published_workflow_id": authoring_session.published_workflow_id,
        "published_version": authoring_session.published_version,
        "published_revision": authoring_session.published_revision,
        "published_at": (
            authoring_session.published_at.isoformat()
            if authoring_session.published_at
            else None
        ),
        "source": (
            {"type": authoring_session.source_type, "payload": authoring_session.source_payload_json}
            if authoring_session.source_type or authoring_session.source_payload_json
            else None
        ),
    }


@router.post("/api/authoring/sessions/{session_id}/drafts")
def save_authoring_draft(
    session_id: str,
    request_body: AuthoringDraftSaveRequest,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _authoring_service(session, request)
    draft = service.save_draft(
        session_id,
        request_body.spec,
        instruction=request_body.instruction,
    )
    repo = AuthoringRepository(session)
    call_log = repo.get_generation_log(session_id, draft.revision)
    return _authoring_draft_payload(
        draft,
        _extract_claude_call_id(call_log.metadata_json if call_log else None),
    )


@router.post("/api/authoring/sessions/{session_id}/continue")
def continue_authoring_session(
    session_id: str,
    request_body: AuthoringDraftSaveRequest,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    if not request_body.instruction:
        raise ValidationError("continue authoring 需要 instruction")
    service = _authoring_service(session, request)
    draft = service.continue_session(session_id, request_body.instruction, request_body.spec)
    repo = AuthoringRepository(session)
    call_log = repo.get_generation_log(session_id, draft.revision)
    return _authoring_draft_payload(
        draft,
        _extract_claude_call_id(call_log.metadata_json if call_log else None),
    )


@router.post("/api/authoring/sessions/{session_id}/generate")
def generate_authoring_draft(
    session_id: str,
    request_body: AuthoringGenerateRequest,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    if not request_body.instruction:
        raise ValidationError("generate authoring 需要 instruction")
    service = _authoring_service(session, request)
    draft, metadata = service.generate_draft(
        session_id,
        request_body.instruction,
        base_spec=request_body.spec,
        claude_call_id=request_body.claude_call_id,
    )
    return _authoring_draft_payload(draft, _extract_claude_call_id(metadata))


@router.post("/api/authoring/reports")
def submit_authoring_report(
    request_body: AuthoringReportRequest,
    request: Request,
) -> dict[str, Any]:
    service = ReportService(request.app.state.settings)
    result = service.save_authoring_report(request_body.model_dump(mode="json"))
    return {"stored": result["stored"]}


@router.get("/api/authoring/sessions/{session_id}/drafts/latest")
def get_latest_authoring_draft(
    session_id: str,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _authoring_service(session, request)
    draft = service.get_latest_draft(session_id)
    repo = AuthoringRepository(session)
    call_log = repo.get_generation_log(session_id, draft.revision)
    return _authoring_draft_payload(
        draft,
        _extract_claude_call_id(call_log.metadata_json if call_log else None),
    )


@router.get("/api/authoring/sessions/{session_id}/drafts/{revision}")
def get_authoring_draft(
    session_id: str,
    revision: int,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _authoring_service(session, request)
    draft = service.get_draft(session_id, revision)
    repo = AuthoringRepository(session)
    call_log = repo.get_generation_log(session_id, draft.revision)
    return _authoring_draft_payload(
        draft,
        _extract_claude_call_id(call_log.metadata_json if call_log else None),
    )


@router.get("/api/authoring/sessions/{session_id}/drafts")
def list_authoring_drafts(
    session_id: str,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _authoring_service(session, request)
    drafts = service.list_drafts(session_id)
    repo = AuthoringRepository(session)
    call_map = _build_generation_call_map(repo, session_id)
    return {
        "drafts": [
            _authoring_draft_payload(item, call_map.get(item.revision))
            for item in drafts
        ]
    }


@router.get("/api/authoring/sessions/{session_id}/messages")
def list_authoring_messages(
    session_id: str,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _authoring_service(session, request)
    items = service.list_messages(session_id)
    return {
        "messages": [
            {
                "id": item.id,
                "session_id": item.session_id,
                "revision": item.revision,
                "role": item.role,
                "content": item.content,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
    }





@router.post("/api/authoring/sessions/{session_id}/publish")
def publish_authoring_session(
    session_id: str,
    request: Request,
    session: SessionDep,
    revision: int | None = None,
) -> dict[str, Any]:
    service = _authoring_service(session, request)
    if revision is None:
        latest = service.get_latest_draft(session_id)
        revision = latest.revision
    result = service.publish(session_id, revision)
    return result

@router.get("/api/authoring/sessions/{session_id}/drafts/{revision}/derive")
def derive_draft_graph_projection(
    session_id: str,
    revision: int,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _authoring_service(session, request)
    draft = service.get_draft(session_id, revision)
    return {
        "session_id": draft.session_id,
        "revision": draft.revision,
        "workflow_view": draft.workflow_view_json,
        "graph": draft.graph_json,
        "lint_report": draft.lint_report_json,
        "lint_warnings": draft.lint_warnings,
    }


@router.post("/api/workflows/register")
def register_workflow(
    request_body: WorkflowRegisterRequest,
    session: SessionDep,
) -> dict[str, Any]:
    service = _workflow_service(session)
    version = service.register_spec(request_body.spec)
    return {
        "workflow_id": version.workflow_definition.workflow_id,
        "version": version.version,
        "schema_version": version.schema_version,
        "warnings": version.lint_warnings,
    }


@router.get("/api/workflows")
def list_workflows(session: SessionDep) -> dict[str, Any]:
    service = _workflow_service(session)
    workflows = service.list_workflows()
    return {
        "workflows": [
            {
                "workflow_id": item.workflow_id,
                "title": item.title,
                "purpose": item.purpose,
                "version_count": len(item.versions),
                "latest_version": (
                    max(
                        item.versions,
                        key=lambda version: version.created_at,
                    ).version
                    if item.versions
                    else None
                ),
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            }
            for item in workflows
        ]
    }


@router.get("/api/workflows/{workflow_id}/versions")
def list_workflow_versions(
    workflow_id: str,
    session: SessionDep,
) -> dict[str, Any]:
    versions = WorkflowRepository(session).list_versions(workflow_id)
    if not versions:
        raise NotFoundError(f"未找到 workflow: {workflow_id}")
    return {
        "workflow_id": workflow_id,
        "versions": [
            {
                "version": item.version,
                "schema_version": item.schema_version,
                "warnings": item.lint_warnings,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in versions
        ],
    }


@router.get("/api/workflows/{workflow_id}/versions/{version}")
def get_workflow(
    workflow_id: str,
    version: str,
    session: SessionDep,
) -> dict[str, Any]:
    service = _workflow_service(session)
    workflow_version = service.get_version(workflow_id, version)
    projection = service.project_spec(workflow_version.spec_json)
    return {
        "workflow_id": workflow_id,
        "version": version,
        "title": workflow_version.workflow_definition.title,
        "warnings": workflow_version.lint_warnings,
        "spec": workflow_version.spec_json,
        "workflow_view": projection["workflow_view"],
        "graph": projection["graph"],
        "lint_report": projection["lint_report"],
    }


@router.get("/ui/workflows/{workflow_id}/versions/{version}", response_class=HTMLResponse)
def workflow_view(
    workflow_id: str,
    version: str,
    session: SessionDep,
) -> str:
    payload = get_workflow(workflow_id, version, session)
    payload["warnings"] = json.dumps(payload["warnings"], ensure_ascii=False, indent=2)
    return render_workflow_view(payload)


@router.post("/api/runs")
def create_run(
    request_body: RunCreateRequest,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _run_service(session, request)
    run = service.start_run(
        request_body.workflow_id,
        request_body.version,
        request_body.inputs,
    )
    return {
        "run_id": run.id,
        "status": run.status,
        "workspace_root": run.workspace_root,
    }


@router.post("/api/runs/reconcile-timeouts")
def reconcile_timeouts(
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    coordinator = _runtime_coordinator(session, request)
    items = coordinator.reconcile_timeouts()
    return {"timed_out": items, "count": len(items)}


@router.get("/api/runs/attention")
def list_attention_runs(
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _run_service(session, request)
    runs = service.run_repo.list_runs_requiring_attention()
    return {
        "runs": [
            {
                "run_id": run.id,
                "workflow_id": run.workflow_id,
                "version": run.workflow_version,
                "status": run.status,
                "stop_reason": run.stop_reason,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "updated_at": run.updated_at.isoformat() if run.updated_at else None,
                "actions": ["retry_node", "stop_run"],
            }
            for run in runs
        ]
    }


@router.get("/api/runs")
def list_runs(
    request: Request,
    session: SessionDep,
    workflow_id: str | None = None,
) -> dict[str, Any]:
    service = _run_service(session, request)
    return {"runs": service.list_run_summaries(workflow_id=workflow_id)}


@router.get("/api/runs/{run_id}")
def get_run(
    run_id: str,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _run_service(session, request)
    detail = service.get_run_detail(run_id)
    return {
        "run": {
            "id": detail["run"].id,
            "status": detail["run"].status,
            "workspace_root": detail["run"].workspace_root,
            "stop_reason": detail["run"].stop_reason,
        },
        "workflow": detail["workflow"],
        "nodes": [
            {
                "node_id": item.node_id,
                "round_no": item.round_no,
                "status": item.status,
                "waiting_for_role": item.waiting_for_role,
                "stop_reason": item.stop_reason,
            }
            for item in detail["nodes"]
        ],
        "artifacts": [
            {
                "artifact_id": item.artifact_id,
                "version": item.version,
                "kind": item.kind,
                "storage_uri": item.storage_uri,
                "node_id": item.node_id,
                "round_no": item.round_no,
            }
            for item in detail["artifacts"]
        ],
    }


@router.post("/api/runs/{run_id}/drive")
def drive_run(
    run_id: str,
    request_body: RunDriveRequest,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    driver = _run_driver(session, request)
    result = driver.drive(
        run_id=run_id,
        executor_command_template=request_body.executor_command_template,
        validator_command_template=request_body.validator_command_template,
        max_steps=request_body.max_steps,
    )
    return result


@router.get("/api/runs/{run_id}/debug/overview")
def get_run_debug_overview(
    run_id: str,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _run_service(session, request)
    overview = service.get_run_debug_overview(run_id)
    return overview


@router.get("/api/runs/{run_id}/debug/nodes/{node_id}/rounds/{round_no}")
def get_run_node_debug_details(
    run_id: str,
    node_id: str,
    round_no: int,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _run_service(session, request)
    run_repo = RunRepository(session)

    node_run = run_repo.get_node_run(run_id, node_id, round_no)
    if not node_run:
        raise NotFoundError(f"未找到 node run: {node_id}@{round_no}")

    events = CallbackRepository(session).list_run_events(run_id)
    node_events = [e for e in events if e.node_id == node_id and e.round_no == round_no]
    run = service.get_run(run_id)
    workspace = service.get_workspace(run)
    try:
        context = service.workspace.read_executor_context(workspace, node_id, round_no)
    except FileNotFoundError:
        context = None

    artifacts = [
        item
        for item in ArtifactRepository(session).list_run_artifacts(run_id)
        if item.node_id == node_id and item.round_no == round_no
    ]

    log_refs = []
    round_dir = workspace.nodes_dir / node_id / "rounds" / str(round_no)
    if round_dir.exists():
        for file_path in sorted(round_dir.rglob("*")):
            if file_path.is_file():
                log_refs.append(
                    {
                        "path": str(file_path.relative_to(workspace.root)),
                        "kind": "file",
                    }
                )

    def _read_call_id(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        call_id = payload.get("call_id")
        if not call_id:
            return None
        return payload

    executor_call_payload = _read_call_id(round_dir / "executor" / "claude_call.json")
    executor_call_id = executor_call_payload.get("call_id") if executor_call_payload else None
    validator_calls: list[dict[str, str]] = []
    validators_dir = round_dir / "validators"
    if validators_dir.exists():
        for file_path in sorted(validators_dir.glob("*.claude_call.json")):
            payload = _read_call_id(file_path)
            if not payload:
                continue
            validator_id = payload.get("validator_id") or file_path.name.split(".")[0]
            validator_calls.append(
                {
                    "validator_id": validator_id,
                    "call_id": payload["call_id"],
                }
            )

    return {
        "node_id": node_id,
        "round_no": round_no,
        "status": node_run.status,
        "waiting_for_role": node_run.waiting_for_role,
        "stop_reason": node_run.stop_reason,
        "rework_brief": node_run.rework_brief_json,
        "context": context,
        "callbacks": [
            {
                "event_id": item.event_id,
                "actor_role": item.actor_role,
                "validator_id": item.validator_id,
                "execution_status": item.execution_status,
                "verdict_status": item.verdict_status,
                "payload": item.payload_json,
            }
            for item in node_events
        ],
        "artifacts": [
            {
                "artifact_id": item.artifact_id,
                "version": item.version,
                "kind": item.kind,
                "storage_uri": item.storage_uri,
                "digest": item.digest,
            }
            for item in artifacts
        ],
        "log_refs": log_refs,
        "claude_calls": {
            "executor_call_id": executor_call_id,
            "validator_calls": validator_calls,
        },
    }


@router.get("/api/runs/{run_id}/callbacks")
def get_run_callbacks(run_id: str, session: SessionDep) -> dict[str, Any]:
    run_repo = RunRepository(session)
    if run_repo.get_run(run_id) is None:
        raise NotFoundError(f"未找到 run: {run_id}")
    events = CallbackRepository(session).list_run_events(run_id)
    return {
        "events": [
            {
                "event_id": item.event_id,
                "node_id": item.node_id,
                "round_no": item.round_no,
                "actor_role": item.actor_role,
                "validator_id": item.validator_id,
                "execution_status": item.execution_status,
                "verdict_status": item.verdict_status,
            }
            for item in events
        ]
    }


@router.get("/api/runs/{run_id}/artifacts")
def get_run_artifacts(
    run_id: str,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _artifact_service(session, request)
    return {
        "artifacts": [
            {
                "artifact_id": item.artifact_id,
                "version": item.version,
                "kind": item.kind,
                "digest": item.digest,
                "storage_uri": item.storage_uri,
            }
            for item in service.list_run_artifacts(run_id)
        ]
    }


@router.get("/api/runs/{run_id}/artifacts/{artifact_id}/versions/{version}/preview")
def preview_run_artifact(
    run_id: str,
    artifact_id: str,
    version: str,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _preview_service(session, request)
    return service.preview_artifact(run_id, artifact_id, version)


@router.get("/api/runs/{run_id}/logs/preview")
def preview_run_log(
    run_id: str,
    path: str,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _preview_service(session, request)
    return service.preview_log(run_id, path)


@router.get("/ui/runs/{run_id}", response_class=HTMLResponse)
def run_view(
    run_id: str,
    request: Request,
    session: SessionDep,
) -> str:
    detail = get_run(run_id, request, session)
    callbacks = get_run_callbacks(run_id, session)["events"]
    return render_run_view(detail, callbacks)


@router.post("/api/runs/{run_id}/stop")
def stop_run(
    run_id: str,
    request_body: StopRunRequest,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _run_service(session, request)
    run = service.stop_run(run_id, request_body.reason)
    return {"run_id": run.id, "status": run.status, "stop_reason": run.stop_reason}


@router.post("/api/runs/{run_id}/nodes/{node_id}/retry")
def retry_run_node(
    run_id: str,
    node_id: str,
    request_body: RunRetryRequest,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _run_service(session, request)
    node_run = service.retry_node(run_id, node_id, request_body.rework_brief)
    return {
        "run_id": run_id,
        "node_id": node_id,
        "round_no": node_run.round_no,
        "status": node_run.status,
        "waiting_for_role": node_run.waiting_for_role,
    }


@router.post("/api/artifacts")
def publish_artifact(
    manifest: ArtifactManifest,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    service = _artifact_service(session, request)
    artifact, created = service.publish_manifest(manifest)
    return {
        "created": created,
        "artifact_id": artifact.artifact_id,
        "version": artifact.version,
        "storage_uri": artifact.storage_uri,
    }


@router.post("/api/callbacks")
def submit_callback(
    payload: NodeCallbackPayload,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    coordinator = _runtime_coordinator(session, request)
    return coordinator.submit_callback(payload)


@router.post("/api/runs/{run_id}/nodes/{node_id}/executor/dispatch")
def dispatch_executor(
    run_id: str,
    node_id: str,
    request_body: ExecutorDispatchRequest,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    dispatcher = _executor_dispatcher(session, request)
    return dispatcher.dispatch(
        run_id=run_id,
        node_id=node_id,
        round_no=request_body.round_no,
        command_template=request_body.command_template,
    )


@router.post("/api/runs/{run_id}/nodes/{node_id}/validators/{validator_id}/dispatch")
def dispatch_validator(
    run_id: str,
    node_id: str,
    validator_id: str,
    request_body: ValidatorDispatchRequest,
    request: Request,
    session: SessionDep,
) -> dict[str, Any]:
    dispatcher = _validator_dispatcher(session, request)
    return dispatcher.dispatch(
        run_id=run_id,
        node_id=node_id,
        validator_id=validator_id,
        round_no=request_body.round_no,
        command_template=request_body.command_template,
    )


@router.get("/api/settings")
def get_settings_snapshot(request: Request, session: SessionDep) -> dict[str, Any]:
    service = _settings_service(session, request)
    return {"settings": service.build_snapshot()}


@router.get("/api/claude-calls/{call_id}")
def get_claude_call(call_id: str, request: Request) -> dict[str, Any]:
    store = _claude_call_store(request)
    metadata = store.load_metadata(call_id)
    if not request.app.state.settings.claude_trace_enabled:
        metadata["redacted"] = True
    return metadata


@router.get("/api/claude-calls/{call_id}/poll")
def poll_claude_call(
    call_id: str,
    request: Request,
    offset: int = 0,
    limit: int = 20000,
) -> dict[str, Any]:
    store = _claude_call_store(request)
    metadata = store.load_metadata(call_id)
    status = metadata.get("status")
    done = status != "running"
    if not request.app.state.settings.claude_trace_enabled:
        return {
            "call_id": call_id,
            "offset": offset,
            "chunk": "",
            "status": status,
            "done": done,
            "truncated": metadata.get("truncated", False),
            "redacted": True,
        }
    chunk_bytes = store.read_chunk(call_id, offset, limit)
    new_offset = offset + len(chunk_bytes)
    return {
        "call_id": call_id,
        "offset": new_offset,
        "chunk": chunk_bytes.decode("utf-8", errors="replace"),
        "status": status,
        "done": done,
        "truncated": metadata.get("truncated", False),
        "redacted": False,
    }


@router.get("/api/claude-calls/{call_id}/stream")
def stream_claude_call(
    call_id: str,
    request: Request,
    offset: int = 0,
) -> StreamingResponse:
    store = _claude_call_store(request)
    settings = request.app.state.settings
    metadata = store.load_metadata(call_id)
    log_path = settings.data_dir / metadata["output_path"]

    def event_stream():
        current_offset = offset
        if not settings.claude_trace_enabled:
            payload = {
                "call_id": call_id,
                "offset": current_offset,
                "chunk": "",
                "status": metadata.get("status"),
                "done": metadata.get("status") != "running",
                "truncated": metadata.get("truncated", False),
                "redacted": True,
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            return
        if not log_path.exists():
            raise NotFoundError(f"未找到 Claude 输出日志: {call_id}")
        with log_path.open("rb") as handle:
            if current_offset:
                handle.seek(current_offset)
            while True:
                chunk = handle.read(4096)
                if chunk:
                    current_offset += len(chunk)
                    payload = {
                        "call_id": call_id,
                        "offset": current_offset,
                        "chunk": chunk.decode("utf-8", errors="replace"),
                        "status": metadata.get("status"),
                        "done": False,
                        "truncated": metadata.get("truncated", False),
                        "redacted": False,
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    continue
                latest = store.load_metadata(call_id)
                status = latest.get("status")
                if status != "running":
                    payload = {
                        "call_id": call_id,
                        "offset": current_offset,
                        "chunk": "",
                        "status": status,
                        "done": True,
                        "truncated": latest.get("truncated", False),
                        "redacted": False,
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    break
                time.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def install_exception_handlers(app: FastAPI) -> None:
    def _json(status_code: int, message: str) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": message})

    @app.exception_handler(NotFoundError)
    async def handle_not_found(_request: Request, exc: NotFoundError) -> JSONResponse:
        return _json(404, str(exc))

    @app.exception_handler(ValidationError)
    @app.exception_handler(InvalidStateError)
    async def handle_bad_request(_request: Request, exc: Exception) -> JSONResponse:
        return _json(400, str(exc))

    @app.exception_handler(ConflictError)
    async def handle_conflict(_request: Request, exc: ConflictError) -> JSONResponse:
        return _json(409, str(exc))
