from __future__ import annotations

import pytest

from pipeliner.skills import naming


@pytest.mark.parametrize(
    "value",
    [
        "draft-wechat-article",
        "wf-demo-node-exec",
        "val-1",
        "a",
    ],
)
def test_is_valid_skill_name_accepts_kebab_case(value: str) -> None:
    assert naming.is_valid_skill_name(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "",
        "Bad_Skill",
        "draft--article",
        "-leading",
        "trailing-",
        "with space",
        "a" * (naming.SKILL_NAME_MAX_LEN + 1),
    ],
)
def test_is_valid_skill_name_rejects_invalid(value: str) -> None:
    assert naming.is_valid_skill_name(value) is False


def test_is_valid_skill_name_rejects_reserved() -> None:
    for reserved in naming.RESERVED_SKILL_NAMES:
        assert naming.is_valid_skill_name(reserved) is False


def test_validate_skill_name_raises_on_invalid() -> None:
    with pytest.raises(ValueError):
        naming.validate_skill_name("Bad_Skill", context="node executor")
