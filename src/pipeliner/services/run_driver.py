from __future__ import annotations

from pipeliner.config import Settings, get_settings
from pipeliner.executor import ClaudeExecutorDispatcher, ClaudeValidatorDispatcher
from pipeliner.persistence.repositories import (
    ArtifactRepository,
    CallbackRepository,
    RunRepository,
    WorkflowRepository,
)
from pipeliner.services.run_service import RunService
from pipeliner.types import NodeRunStatus, RunStatus


class RunDriver:
    def __init__(
        self,
        run_repo: RunRepository,
        workflow_repo: WorkflowRepository,
        callback_repo: CallbackRepository,
        artifact_repo: ArtifactRepository,
        settings: Settings | None = None,
    ) -> None:
        self.run_repo = run_repo
        self.workflow_repo = workflow_repo
        self.callback_repo = callback_repo
        self.artifact_repo = artifact_repo
        self.settings = settings or get_settings()
        self.run_service = RunService(run_repo, workflow_repo, artifact_repo, self.settings)
        self.executor_dispatcher = ClaudeExecutorDispatcher(
            run_repo,
            workflow_repo,
            callback_repo,
            artifact_repo,
            self.settings,
        )
        self.validator_dispatcher = ClaudeValidatorDispatcher(
            run_repo,
            workflow_repo,
            callback_repo,
            artifact_repo,
            self.settings,
        )

    def drive(
        self,
        run_id: str,
        *,
        executor_command_template: str | None = None,
        validator_command_template: str | None = None,
        max_steps: int = 100,
    ) -> dict:
        actions: list[dict] = []
        stop_reason = "terminal_state"

        for _ in range(max_steps):
            run = self.run_service.get_run(run_id)
            if run.status in {
                RunStatus.COMPLETED.value,
                RunStatus.NEEDS_ATTENTION.value,
                RunStatus.STOPPED.value,
            }:
                break

            action = self._next_action(run_id)
            if action is None:
                stop_reason = "no_dispatchable_nodes"
                break

            if action["kind"] == "executor":
                result = self.executor_dispatcher.dispatch(
                    run_id=run_id,
                    node_id=action["node_id"],
                    round_no=action["round_no"],
                    command_template=executor_command_template,
                )
            else:
                result = self.validator_dispatcher.dispatch(
                    run_id=run_id,
                    node_id=action["node_id"],
                    validator_id=action["validator_id"],
                    round_no=action["round_no"],
                    command_template=validator_command_template,
                )
            actions.append(result)
        else:
            stop_reason = "max_steps_exceeded"

        final_run = self.run_service.get_run(run_id)
        return {
            "run_id": run_id,
            "status": final_run.status,
            "stop_reason": stop_reason,
            "steps": actions,
        }

    def _next_action(self, run_id: str) -> dict | None:
        run = self.run_service.get_run(run_id)
        spec = self.run_service.get_run_spec(run)
        latest = self.run_repo.list_latest_node_runs(run.id)

        for node in spec.nodes:
            node_run = latest.get(node.node_id)
            if node_run is None:
                continue
            if node_run.status == NodeRunStatus.WAITING_EXECUTOR.value:
                return {
                    "kind": "executor",
                    "node_id": node.node_id,
                    "round_no": node_run.round_no,
                }
            if node_run.status == NodeRunStatus.WAITING_VALIDATOR.value:
                for validator in node.validators:
                    existing = self.callback_repo.get_validator_round_event(
                        run.id,
                        node.node_id,
                        node_run.round_no,
                        validator.validator_id,
                    )
                    if existing is None:
                        return {
                            "kind": "validator",
                            "node_id": node.node_id,
                            "round_no": node_run.round_no,
                            "validator_id": validator.validator_id,
                        }
        return None
