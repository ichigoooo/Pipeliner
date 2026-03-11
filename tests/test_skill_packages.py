from __future__ import annotations

import json

from pipeliner.services.project_initializer import ProjectInitializer
from pipeliner.skills.naming import (
    build_default_executor_skill,
    build_default_validator_skill,
)


def _spec_missing_skills() -> dict:
    return {
        "schema_version": "pipeliner.workflow/v1alpha1",
        "metadata": {
            "workflow_id": "skill-demo",
            "version": "v1.0.0",
            "title": "Skill Demo",
            "purpose": "Check node skill packaging",
            "tags": [],
        },
        "inputs": [],
        "outputs": [],
        "nodes": [
            {
                "node_id": "draft",
                "title": "Draft",
                "purpose": "Draft content",
                "archetype": "draft-content",
                "depends_on": [],
                "inputs": [],
                "outputs": [
                    {"name": "draft_text", "shape": "markdown", "summary": "Draft output"}
                ],
                "executor": {},
                "validators": [{"validator_id": "review"}],
                "acceptance": {"done_means": "Draft ready", "pass_condition": ["Readable"]},
                "gate": {"mode": "all_validators_pass"},
                "handoff": {"outputs": ["draft_text"]},
            }
        ],
        "defaults": {"runtime_guards": {"timeout": "30m", "max_rework_rounds": 3}},
        "extensions": {},
    }


def test_node_skill_packages_created_and_context_updated(settings) -> None:
    initializer = ProjectInitializer(settings)
    spec = _spec_missing_skills()
    normalized = initializer.ensure_node_skills("skill-demo", spec)

    executor_skill = normalized["nodes"][0]["executor"]["skill"]
    validator_skill = normalized["nodes"][0]["validators"][0]["skill"]
    assert executor_skill == build_default_executor_skill("skill-demo", "draft")
    assert validator_skill == build_default_validator_skill("skill-demo", "draft", "review")

    project_root = settings.projects_root / "skill-demo"
    executor_root = project_root / ".claude" / "skills" / executor_skill
    validator_root = project_root / ".claude" / "skills" / validator_skill

    executor_skill_file = executor_root / "SKILL.md"
    validator_skill_file = validator_root / "SKILL.md"
    assert executor_skill_file.exists()
    assert validator_skill_file.exists()

    executor_context = executor_root / "references" / "node_context.json"
    validator_context = validator_root / "references" / "node_context.json"
    assert executor_context.exists()
    assert validator_context.exists()

    payload = json.loads(executor_context.read_text(encoding="utf-8"))
    assert payload["node_id"] == "draft"
    assert payload["skill"]["role"] == "executor"

    executor_skill_file.write_text("custom skill content", encoding="utf-8")
    initializer.ensure_node_skills("skill-demo", normalized)
    assert executor_skill_file.read_text(encoding="utf-8") == "custom skill content"
