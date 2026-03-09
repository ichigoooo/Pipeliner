from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class RuntimeGuards(BaseModel):
    timeout: str = Field(default="30m")
    max_rework_rounds: int = Field(default=3, ge=1)
    blocked_requires_manual: bool = True
    failure_requires_manual: bool = True

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("timeout 不能为空")
        return value
