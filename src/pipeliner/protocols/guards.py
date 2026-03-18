from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class RuntimeGuards(BaseModel):
    timeout: str = Field(default="2h")
    first_byte_timeout: str = Field(default="180s")
    max_rework_rounds: int = Field(default=3, ge=1)
    blocked_requires_manual: bool = True
    failure_requires_manual: bool = True

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("timeout 不能为空")
        return value

    @field_validator("first_byte_timeout")
    @classmethod
    def validate_first_byte_timeout(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("first_byte_timeout 不能为空")
        return value
