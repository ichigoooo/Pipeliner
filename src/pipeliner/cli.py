from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from pipeliner.config import get_settings
from pipeliner.db import Database
from pipeliner.executor import ClaudeExecutorDispatcher, ClaudeValidatorDispatcher
from pipeliner.persistence.repositories import ArtifactRepository, CallbackRepository, RunRepository, WorkflowRepository
from pipeliner.protocols.artifact import ArtifactManifest
from pipeliner.runtime import RuntimeCoordinator
from pipeliner.services.artifact_service import ArtifactService
from pipeliner.services.run_driver import RunDriver
from pipeliner.services.run_service import RunService
from pipeliner.services.workflow_service import WorkflowService

app = typer.Typer(help="Pipeliner MVP operator CLI")
workflow_app = typer.Typer(help="Workflow operations")
run_app = typer.Typer(help="Run operations")
artifact_app = typer.Typer(help="Artifact operations")
executor_app = typer.Typer(help="Executor operations")
validator_app = typer.Typer(help="Validator operations")
app.add_typer(workflow_app, name="workflow")
app.add_typer(run_app, name="run")
app.add_typer(artifact_app, name="artifact")
app.add_typer(executor_app, name="executor")
app.add_typer(validator_app, name="validator")


def _db() -> Database:
    return Database(get_settings())


def _print(payload: Any) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


@app.command("db-init")
def db_init() -> None:
    db = _db()
    db.create_all()
    typer.echo("database initialized")


@workflow_app.command("register")
def workflow_register(path: Path) -> None:
    db = _db()
    with db.session() as session:
        service = WorkflowService(WorkflowRepository(session))
        raw = service.load_raw_file(path)
        version = service.register_spec(raw)
        _print(
            {
                "workflow_id": version.workflow_definition.workflow_id,
                "version": version.version,
                "warnings": version.lint_warnings,
            }
        )


@workflow_app.command("show")
def workflow_show(workflow_id: str, version: str) -> None:
    db = _db()
    with db.session() as session:
        service = WorkflowService(WorkflowRepository(session))
        workflow_version = service.get_version(workflow_id, version)
        _print(workflow_version.spec_json)


@run_app.command("start")
def run_start(workflow_id: str, version: str, inputs_file: Path) -> None:
    db = _db()
    with db.session() as session:
        service = RunService(RunRepository(session), WorkflowRepository(session), ArtifactRepository(session), get_settings())
        inputs = json.loads(inputs_file.read_text(encoding="utf-8")) if inputs_file.exists() else {}
        run = service.start_run(workflow_id, version, inputs)
        _print({"run_id": run.id, "status": run.status, "workspace_root": run.workspace_root})


@run_app.command("show")
def run_show(run_id: str) -> None:
    db = _db()
    with db.session() as session:
        service = RunService(RunRepository(session), WorkflowRepository(session), ArtifactRepository(session), get_settings())
        detail = service.get_run_detail(run_id)
        _print(
            {
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
        )


@run_app.command("stop")
def run_stop(run_id: str, reason: str = "manual_stop") -> None:
    db = _db()
    with db.session() as session:
        service = RunService(RunRepository(session), WorkflowRepository(session), ArtifactRepository(session), get_settings())
        run = service.stop_run(run_id, reason)
        _print({"run_id": run.id, "status": run.status, "stop_reason": run.stop_reason})


@run_app.command("attention")
def run_attention() -> None:
    db = _db()
    with db.session() as session:
        service = RunService(RunRepository(session), WorkflowRepository(session), ArtifactRepository(session), get_settings())
        _print(
            [
                {
                    "run_id": item.id,
                    "workflow_id": item.workflow_id,
                    "version": item.workflow_version,
                    "status": item.status,
                    "stop_reason": item.stop_reason,
                }
                for item in service.run_repo.list_runs_requiring_attention()
            ]
        )


@run_app.command("reconcile-timeouts")
def run_reconcile_timeouts() -> None:
    db = _db()
    with db.session() as session:
        coordinator = RuntimeCoordinator(
            RunRepository(session),
            WorkflowRepository(session),
            CallbackRepository(session),
            ArtifactRepository(session),
            get_settings(),
        )
        _print(coordinator.reconcile_timeouts())


@run_app.command("drive")
def run_drive(
    run_id: str,
    executor_command_template: str | None = typer.Option(
        default=None,
        help="Override executor command template for this drive session",
    ),
    validator_command_template: str | None = typer.Option(
        default=None,
        help="Override validator command template for this drive session",
    ),
    max_steps: int = typer.Option(default=100, min=1, help="Maximum dispatch actions to execute"),
) -> None:
    db = _db()
    with db.session() as session:
        driver = RunDriver(
            RunRepository(session),
            WorkflowRepository(session),
            CallbackRepository(session),
            ArtifactRepository(session),
            get_settings(),
        )
        result = driver.drive(
            run_id=run_id,
            executor_command_template=executor_command_template,
            validator_command_template=validator_command_template,
            max_steps=max_steps,
        )
        _print(result)


@artifact_app.command("publish")
def artifact_publish(manifest_file: Path) -> None:
    db = _db()
    manifest = ArtifactManifest.model_validate_json(manifest_file.read_text(encoding="utf-8"))
    with db.session() as session:
        service = ArtifactService(ArtifactRepository(session), RunRepository(session), get_settings())
        artifact, created = service.publish_manifest(manifest)
        _print({"created": created, "artifact_id": artifact.artifact_id, "version": artifact.version})


@executor_app.command("dispatch")
def executor_dispatch(
    run_id: str,
    node_id: str,
    round_no: int | None = typer.Option(default=None, help="Optional node round number"),
    command_template: str | None = typer.Option(
        default=None,
        help="Override executor command template, e.g. 'claude -p --permission-mode bypassPermissions'",
    ),
) -> None:
    db = _db()
    with db.session() as session:
        dispatcher = ClaudeExecutorDispatcher(
            RunRepository(session),
            WorkflowRepository(session),
            CallbackRepository(session),
            ArtifactRepository(session),
            get_settings(),
        )
        result = dispatcher.dispatch(
            run_id=run_id,
            node_id=node_id,
            round_no=round_no,
            command_template=command_template,
        )
        _print(result)


@validator_app.command("dispatch")
def validator_dispatch(
    run_id: str,
    node_id: str,
    validator_id: str,
    round_no: int | None = typer.Option(default=None, help="Optional node round number"),
    command_template: str | None = typer.Option(
        default=None,
        help="Override validator command template, e.g. 'claude -p --permission-mode bypassPermissions'",
    ),
) -> None:
    db = _db()
    with db.session() as session:
        dispatcher = ClaudeValidatorDispatcher(
            RunRepository(session),
            WorkflowRepository(session),
            CallbackRepository(session),
            ArtifactRepository(session),
            get_settings(),
        )
        result = dispatcher.dispatch(
            run_id=run_id,
            node_id=node_id,
            validator_id=validator_id,
            round_no=round_no,
            command_template=command_template,
        )
        _print(result)


if __name__ == "__main__":
    app()
