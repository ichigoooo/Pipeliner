from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Iterable

from pipeliner.services.execution_trace import ExecutionTraceRecorder

_DEFAULT_ALLOWLIST = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_API_URL",
    "CLAUDE_API_BASE",
    "CLAUDE_BASE_URL",
    "PATH",
    "PIPELINER_CLAUDE_API_HOST",
)
_DEFAULT_CACHE_TTL = 60.0
_DEFAULT_SHELL = "/bin/zsh"
_DEFAULT_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

_cached_env: dict[str, str] | None = None
_cached_at: float | None = None


def is_claude_command(command: list[str]) -> bool:
    if not command:
        return False
    name = Path(command[0]).name.lower()
    return name.startswith("claude")


def resolve_claude_api_host(env: dict[str, str]) -> str:
    raw = env.get("PIPELINER_CLAUDE_API_HOST") or os.getenv("PIPELINER_CLAUDE_API_HOST")
    if not raw:
        base_url = _base_url_from_env(env) or _base_url_from_env(os.environ)
        if not base_url:
            base_url = _load_base_url_from_settings()
        if base_url:
            raw = base_url
    if not raw:
        raw = "api.anthropic.com"
    host = raw.strip()
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.split("/", 1)[0]
    host = host.split(":", 1)[0]
    return host or "api.anthropic.com"


def resolve_claude_base_url(env: dict[str, str]) -> tuple[str, str]:
    value = _base_url_from_env(env)
    if value:
        return value, "env"
    value = _load_base_url_from_settings()
    if value:
        return value, "claude_settings"
    return "https://api.anthropic.com", "default"


def resolve_claude_api_host_with_source(
    env: dict[str, str],
    shell_env: dict[str, str] | None = None,
) -> tuple[str, str]:
    env_value = env.get("PIPELINER_CLAUDE_API_HOST")
    if env_value:
        return resolve_claude_api_host({"PIPELINER_CLAUDE_API_HOST": env_value}), "env"
    if shell_env:
        shell_value = shell_env.get("PIPELINER_CLAUDE_API_HOST")
        if shell_value:
            return resolve_claude_api_host({"PIPELINER_CLAUDE_API_HOST": shell_value}), "shell_env"
    base_url, source = resolve_claude_base_url(env)
    host = resolve_claude_api_host({"ANTHROPIC_BASE_URL": base_url})
    return host, "derived" if source != "default" else "default"


def preflight_claude_host(host: str, trace_recorder: ExecutionTraceRecorder | None = None) -> str | None:
    try:
        socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        return None
    except socket.gaierror as exc:
        error = f"Claude API 域名解析失败（{exc.strerror or 'ENOTFOUND'}），请检查 DNS/代理/网络。"
        if trace_recorder is not None:
            trace_recorder.log("claude_preflight_failed", host=host, error=str(exc))
        return error
    except Exception as exc:  # pragma: no cover
        error = f"Claude API 域名解析失败（{exc}），请检查 DNS/代理/网络。"
        if trace_recorder is not None:
            trace_recorder.log("claude_preflight_failed", host=host, error=str(exc))
        return error


def detect_cli_network_error(stdout: str, stderr: str) -> str | None:
    combined = f"{stdout}\n{stderr}"
    if "ENOTFOUND" in combined:
        return "Claude API 域名解析失败（ENOTFOUND），请检查 DNS/代理/网络。"
    if "Unable to connect to API" in combined:
        return "Claude API 无法连接，请检查网络或代理。"
    return None


def build_claude_env(
    base_env: dict[str, str],
    trace_recorder: ExecutionTraceRecorder | None = None,
) -> dict[str, str]:
    allowlist = _parse_allowlist(os.getenv("PIPELINER_CLAUDE_ENV_ALLOWLIST"))
    cache_ttl = _parse_cache_ttl(os.getenv("PIPELINER_CLAUDE_ENV_CACHE_TTL"))
    shell = os.getenv("SHELL") or _DEFAULT_SHELL
    shell_env = _load_shell_env(allowlist, shell, cache_ttl, trace_recorder)
    merged = dict(base_env)
    for key, value in shell_env.items():
        if key not in merged or merged[key] == "":
            merged[key] = value
    settings_env = _load_settings_env(allowlist)
    for key, value in settings_env.items():
        if key not in merged or merged[key] == "":
            merged[key] = value
    settings_base_url = _base_url_from_env(settings_env) or _load_base_url_from_settings()
    if settings_base_url and not merged.get("ANTHROPIC_BASE_URL"):
        merged["ANTHROPIC_BASE_URL"] = settings_base_url
    if settings_base_url and not merged.get("PIPELINER_CLAUDE_API_HOST"):
        merged["PIPELINER_CLAUDE_API_HOST"] = resolve_claude_api_host(
            {"ANTHROPIC_BASE_URL": settings_base_url}
        )
    if trace_recorder is not None:
        if settings_base_url:
            trace_recorder.log("claude_settings_loaded", base_url=settings_base_url)
        trace_recorder.log(
            "claude_env_merged",
            keys=sorted(set(shell_env.keys()) | set(settings_env.keys())),
        )
    return merged


def collect_claude_diagnostics(base_env: dict[str, str]) -> dict[str, object]:
    allowlist = _parse_allowlist(os.getenv("PIPELINER_CLAUDE_ENV_ALLOWLIST"))
    cache_ttl = _parse_cache_ttl(os.getenv("PIPELINER_CLAUDE_ENV_CACHE_TTL"))
    shell = os.getenv("SHELL") or _DEFAULT_SHELL
    shell_env = _load_shell_env(allowlist, shell, cache_ttl, None)
    merged = dict(base_env)
    for key, value in shell_env.items():
        if key not in merged or merged[key] == "":
            merged[key] = value
    settings_env = _load_settings_env(allowlist)
    for key, value in settings_env.items():
        if key not in merged or merged[key] == "":
            merged[key] = value
    settings_base_url = _base_url_from_env(settings_env) or _load_base_url_from_settings()
    if settings_base_url and not merged.get("ANTHROPIC_BASE_URL"):
        merged["ANTHROPIC_BASE_URL"] = settings_base_url
    if settings_base_url and not merged.get("PIPELINER_CLAUDE_API_HOST"):
        merged["PIPELINER_CLAUDE_API_HOST"] = resolve_claude_api_host(
            {"ANTHROPIC_BASE_URL": settings_base_url}
        )

    base_url, base_source = resolve_claude_base_url(merged)
    host, host_source = resolve_claude_api_host_with_source(merged, shell_env)
    proxy_keys = {
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    }
    process_keys = sorted(key for key in proxy_keys if base_env.get(key))
    shell_keys = sorted(key for key in proxy_keys if shell_env.get(key))
    effective_keys = sorted(key for key in proxy_keys if merged.get(key))
    return {
        "base_url": {"value": base_url, "source": base_source},
        "api_host": {"value": host, "source": host_source},
        "proxy": {
            "process_keys": process_keys,
            "shell_keys": shell_keys,
            "effective_keys": effective_keys,
            "missing": len(effective_keys) == 0,
        },
        "sources": {
            "settings_path": str(
                Path(os.getenv("PIPELINER_CLAUDE_SETTINGS_PATH") or _DEFAULT_SETTINGS_PATH)
            ),
            "settings_loaded": settings_base_url is not None,
            "settings_env_keys": sorted(settings_env.keys()),
        },
    }


def _parse_allowlist(raw: str | None) -> list[str]:
    if not raw:
        return list(_DEFAULT_ALLOWLIST)
    items = []
    for token in raw.replace(",", " ").split():
        if token:
            items.append(token)
    if "PATH" not in items:
        items.append("PATH")
    if "PIPELINER_CLAUDE_API_HOST" not in items:
        items.append("PIPELINER_CLAUDE_API_HOST")
    return items


def _parse_cache_ttl(raw: str | None) -> float:
    if not raw:
        return _DEFAULT_CACHE_TTL
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_CACHE_TTL
    if value <= 0:
        return _DEFAULT_CACHE_TTL
    return value


def _load_shell_env(
    allowlist: Iterable[str],
    shell: str,
    cache_ttl: float,
    trace_recorder: ExecutionTraceRecorder | None,
) -> dict[str, str]:
    global _cached_env
    global _cached_at
    now = time.time()
    if _cached_env is not None and _cached_at is not None and now - _cached_at < cache_ttl:
        return _cached_env
    command = _build_shell_env_command(shell)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception as exc:
        if trace_recorder is not None:
            trace_recorder.log("claude_env_load_failed", error=str(exc))
        return {}
    if result.returncode != 0:
        if trace_recorder is not None:
            trace_recorder.log(
                "claude_env_load_failed",
                error=f"shell env exit={result.returncode}",
                stderr=result.stderr.strip(),
            )
        return {}
    parsed = _parse_env_lines(result.stdout.splitlines(), allowlist)
    _cached_env = parsed
    _cached_at = now
    if trace_recorder is not None:
        trace_recorder.log("claude_env_loaded", keys=sorted(parsed.keys()))
    return parsed


def _build_shell_env_command(shell: str) -> list[str]:
    name = Path(shell).name
    if name == "zsh":
        command = (
            "set -a; "
            "[ -f \"$HOME/.zprofile\" ] && source \"$HOME/.zprofile\"; "
            "[ -f \"$HOME/.zshrc\" ] && source \"$HOME/.zshrc\"; "
            "env"
        )
        return [shell, "-lc", command]
    if name == "bash":
        command = (
            "set -a; "
            "[ -f \"$HOME/.bash_profile\" ] && source \"$HOME/.bash_profile\"; "
            "[ -f \"$HOME/.bashrc\" ] && source \"$HOME/.bashrc\"; "
            "env"
        )
        return [shell, "-lc", command]
    return [shell, "-lc", "env"]


def _parse_env_lines(lines: Iterable[str], allowlist: Iterable[str]) -> dict[str, str]:
    allow_rules = list(allowlist)
    parsed: dict[str, str] = {}
    for line in lines:
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if _is_allowed_env(key, allow_rules):
            parsed[key] = value
    return parsed


def _is_allowed_env(key: str, allow_rules: list[str]) -> bool:
    for rule in allow_rules:
        if not rule:
            continue
        if rule.endswith("*"):
            if key.startswith(rule[:-1]):
                return True
        elif key == rule:
            return True
    return False


def _base_url_from_env(env: dict[str, str] | os._Environ[str]) -> str | None:
    return (
        env.get("ANTHROPIC_BASE_URL")
        or env.get("ANTHROPIC_API_URL")
        or env.get("CLAUDE_API_BASE")
        or env.get("CLAUDE_BASE_URL")
    )


def _load_base_url_from_settings() -> str | None:
    settings_env = _load_settings_env(_DEFAULT_ALLOWLIST)
    value = _base_url_from_env(settings_env)
    if value:
        return value
    data = _load_settings_payload()
    if not isinstance(data, dict):
        return None
    for key in (
        "ANTHROPIC_BASE_URL",
        "anthropic_base_url",
        "api_base",
        "base_url",
        "endpoint",
    ):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _load_settings_env(allowlist: Iterable[str]) -> dict[str, str]:
    data = _load_settings_payload()
    if not isinstance(data, dict):
        return {}
    raw_env = data.get("env")
    if not isinstance(raw_env, dict):
        return {}
    parsed: dict[str, str] = {}
    rules = list(allowlist)
    for key, value in raw_env.items():
        if isinstance(key, str) and isinstance(value, str) and value and _is_allowed_env(key, rules):
            parsed[key] = value
    return parsed


def _load_settings_payload() -> dict[str, object] | None:
    settings_path = os.getenv("PIPELINER_CLAUDE_SETTINGS_PATH")
    path = Path(settings_path).expanduser() if settings_path else _DEFAULT_SETTINGS_PATH
    if not path.exists():
        return None
    try:
        payload = path.read_text(encoding="utf-8")
    except Exception:
        return None
    try:
        data = json.loads(payload)
    except Exception:
        return None
    return data if isinstance(data, dict) else None
