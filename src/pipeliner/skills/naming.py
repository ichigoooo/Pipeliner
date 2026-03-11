from __future__ import annotations

import re

SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SKILL_NAME_MIN_LEN = 1
SKILL_NAME_MAX_LEN = 64
# 注意：新增系统级 skill 时需同步更新该列表。 
RESERVED_SKILL_NAMES = frozenset(
    {
        "workflow-authoring",
        "workflow-iteration",
        "workflow-review",
    }
)


def normalize_skill_name(value: str) -> str:
    return value.strip()


def is_valid_skill_name(name: str) -> bool:
    if not name:
        return False
    if name in RESERVED_SKILL_NAMES:
        return False
    if len(name) < SKILL_NAME_MIN_LEN or len(name) > SKILL_NAME_MAX_LEN:
        return False
    return SKILL_NAME_PATTERN.match(name) is not None


def validate_skill_name(name: str, *, context: str) -> None:
    if not is_valid_skill_name(name):
        raise ValueError(f"{context} 的 skill 名称无效: {name}")


def slugify_component(value: str | None) -> str:
    if not value:
        return "unknown"
    lowered = value.strip().lower()
    if not lowered:
        return "unknown"
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized or "unknown"


def truncate_skill_name(name: str) -> str:
    if len(name) <= SKILL_NAME_MAX_LEN:
        return name
    trimmed = name[:SKILL_NAME_MAX_LEN].rstrip("-")
    return trimmed or name[:SKILL_NAME_MAX_LEN]


def build_default_executor_skill(workflow_id: str, node_id: str) -> str:
    base = f"wf-{slugify_component(workflow_id)}-{slugify_component(node_id)}-exec"
    return truncate_skill_name(base)


def build_default_validator_skill(
    workflow_id: str,
    node_id: str,
    validator_id: str,
) -> str:
    base = (
        f"wf-{slugify_component(workflow_id)}-"
        f"{slugify_component(node_id)}-val-{slugify_component(validator_id)}"
    )
    return truncate_skill_name(base)
