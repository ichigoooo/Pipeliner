from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pipeliner.protocols.guards import RuntimeGuards


def parse_duration(value: str) -> timedelta:
    value = value.strip().lower()
    if not value:
        raise ValueError("duration 不能为空")
    unit = value[-1]
    amount = int(value[:-1])
    if unit == "s":
        return timedelta(seconds=amount)
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    raise ValueError(f"不支持的 duration 单位: {value}")


def is_timeout_exceeded(updated_at: datetime, guards: RuntimeGuards, now: datetime | None = None) -> bool:
    current = now or datetime.now(timezone.utc)
    return current - updated_at >= parse_duration(guards.timeout)
