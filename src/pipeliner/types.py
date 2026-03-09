from enum import StrEnum


class ActorRole(StrEnum):
    EXECUTOR = "executor"
    VALIDATOR = "validator"


class ExecutionStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class VerdictStatus(StrEnum):
    PASS = "pass"
    REVISE = "revise"
    BLOCKED = "blocked"


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    NEEDS_ATTENTION = "needs_attention"
    STOPPED = "stopped"


class NodeRunStatus(StrEnum):
    WAITING_EXECUTOR = "waiting_executor"
    WAITING_VALIDATOR = "waiting_validator"
    PASSED = "passed"
    REVISE = "revise"
    BLOCKED = "blocked"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    REWORK_LIMIT = "rework_limit"
    STOPPED = "stopped"


class ArtifactKind(StrEnum):
    FILE = "file"
    DIRECTORY = "directory"
    COLLECTION = "collection"


class StorageBackend(StrEnum):
    LOCAL_FS = "local_fs"


class GateMode(StrEnum):
    ALL_VALIDATORS_PASS = "all_validators_pass"
