from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from pipeliner.db import Database
from pipeliner.executor import ClaudeExecutorDispatcher, ClaudeValidatorDispatcher
from pipeliner.persistence.repositories import ArtifactRepository, CallbackRepository, RunRepository, WorkflowRepository
from pipeliner.protocols.artifact import ArtifactManifest
from pipeliner.protocols.callback import NodeCallbackPayload
from pipeliner.runtime import RuntimeCoordinator
from pipeliner.services.artifact_service import ArtifactService
from pipeliner.services.errors import ConflictError, InvalidStateError, NotFoundError, ValidationError
from pipeliner.services.run_service import RunService
from pipeliner.services.workflow_service import WorkflowService
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


def get_database(request: Request) -> Database:
    return request.app.state.db


def get_session(db: Database = Depends(get_database)):
    with db.session() as session:
        yield session


def _workflow_service(session: Session) -> WorkflowService:
    return WorkflowService(WorkflowRepository(session))


def _run_service(session: Session, request: Request) -> RunService:
    return RunService(
        RunRepository(session),
        WorkflowRepository(session),
        ArtifactRepository(session),
        request.app.state.settings,
    )


def _runtime_coordinator(session: Session, request: Request) -> RuntimeCoordinator:
    return RuntimeCoordinator(
        RunRepository(session),
        WorkflowRepository(session),
        CallbackRepository(session),
        ArtifactRepository(session),
        request.app.state.settings,
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse)
def ui_index(request: Request, session: Session = Depends(get_session)) -> str:
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


@router.post("/api/workflows/register")
def register_workflow(request_body: WorkflowRegisterRequest, session: Session = Depends(get_session)) -> dict[str, Any]:
    service = _workflow_service(session)
    version = service.register_spec(request_body.spec)
    return {
        "workflow_id": version.workflow_definition.workflow_id,
        "version": version.version,
        "schema_version": version.schema_version,
        "warnings": version.lint_warnings,
    }


@router.get("/api/workflows/{workflow_id}/versions/{version}")
def get_workflow(workflow_id: str, version: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    service = _workflow_service(session)
    workflow_version = service.get_version(workflow_id, version)
    return {
        "workflow_id": workflow_id,
        "version": version,
        "title": workflow_version.workflow_definition.title,
        "warnings": workflow_version.lint_warnings,
        "spec": workflow_version.spec_json,
    }


@router.get("/ui/workflows/{workflow_id}/versions/{version}", response_class=HTMLResponse)
def workflow_view(workflow_id: str, version: str, session: Session = Depends(get_session)) -> str:
    payload = get_workflow(workflow_id, version, session)
    payload["warnings"] = json.dumps(payload["warnings"], ensure_ascii=False, indent=2)
    return render_workflow_view(payload)


@router.post("/api/runs")
def create_run(request_body: RunCreateRequest, request: Request, session: Session = Depends(get_session)) -> dict[str, Any]:
    service = _run_service(session, request)
    run = service.start_run(request_body.workflow_id, request_body.version, request_body.inputs)
    return {
        "run_id": run.id,
        "status": run.status,
        "workspace_root": run.workspace_root,
    }


@router.post("/api/runs/reconcile-timeouts")
def reconcile_timeouts(request: Request, session: Session = Depends(get_session)) -> dict[str, Any]:
    coordinator = _runtime_coordinator(session, request)
    items = coordinator.reconcile_timeouts()
    return {"timed_out": items, "count": len(items)}


@router.get("/api/runs/attention")
def list_attention_runs(request: Request, session: Session = Depends(get_session)) -> dict[str, Any]:
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
            }
            for run in runs
        ]
    }


@router.get("/api/runs/{run_id}")
def get_run(run_id: str, request: Request, session: Session = Depends(get_session)) -> dict[str, Any]:
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
            }
            for item in detail["artifacts"]
        ],
    }


@router.get("/api/runs/{run_id}/callbacks")
def get_run_callbacks(run_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
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
def get_run_artifacts(run_id: str, request: Request, session: Session = Depends(get_session)) -> dict[str, Any]:
    service = ArtifactService(ArtifactRepository(session), RunRepository(session), request.app.state.settings)
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


@router.get("/ui/runs/{run_id}", response_class=HTMLResponse)
def run_view(run_id: str, request: Request, session: Session = Depends(get_session)) -> str:
    detail = get_run(run_id, request, session)
    callbacks = get_run_callbacks(run_id, session)["events"]
    return render_run_view(detail, callbacks)


@router.post("/api/runs/{run_id}/stop")
def stop_run(run_id: str, request_body: StopRunRequest, request: Request, session: Session = Depends(get_session)) -> dict[str, Any]:
    service = _run_service(session, request)
    run = service.stop_run(run_id, request_body.reason)
    return {"run_id": run.id, "status": run.status, "stop_reason": run.stop_reason}


@router.post("/api/artifacts")
def publish_artifact(manifest: ArtifactManifest, request: Request, session: Session = Depends(get_session)) -> dict[str, Any]:
    service = ArtifactService(ArtifactRepository(session), RunRepository(session), request.app.state.settings)
    artifact, created = service.publish_manifest(manifest)
    return {
        "created": created,
        "artifact_id": artifact.artifact_id,
        "version": artifact.version,
        "storage_uri": artifact.storage_uri,
    }


@router.post("/api/callbacks")
def submit_callback(payload: NodeCallbackPayload, request: Request, session: Session = Depends(get_session)) -> dict[str, Any]:
    coordinator = _runtime_coordinator(session, request)
    return coordinator.submit_callback(payload)


@router.post("/api/runs/{run_id}/nodes/{node_id}/executor/dispatch")
def dispatch_executor(
    run_id: str,
    node_id: str,
    request_body: ExecutorDispatchRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    dispatcher = ClaudeExecutorDispatcher(
        RunRepository(session),
        WorkflowRepository(session),
        CallbackRepository(session),
        ArtifactRepository(session),
        request.app.state.settings,
    )
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
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    dispatcher = ClaudeValidatorDispatcher(
        RunRepository(session),
        WorkflowRepository(session),
        CallbackRepository(session),
        ArtifactRepository(session),
        request.app.state.settings,
    )
    return dispatcher.dispatch(
        run_id=run_id,
        node_id=node_id,
        validator_id=validator_id,
        round_no=request_body.round_no,
        command_template=request_body.command_template,
    )


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
