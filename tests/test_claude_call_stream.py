from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from pipeliner.config import Settings
from pipeliner.services.claude_call import ClaudeCallStore, run_streamed_command


def test_streamed_command_records_output_in_order(tmp_path: Path) -> None:
    script = tmp_path / "stream_script.py"
    script.write_text(
        "\n".join(
            [
                "import sys, time",
                "print('OUT-1')",
                "sys.stdout.flush()",
                "time.sleep(0.05)",
                "print('ERR-1', file=sys.stderr)",
                "sys.stderr.flush()",
                "time.sleep(0.05)",
                "print('OUT-2')",
                "sys.stdout.flush()",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(data_dir=tmp_path / ".pipeliner", projects_root=tmp_path / "projects")
    store = ClaudeCallStore(settings)
    call = store.start_call(role="test", context={}, command=[sys.executable, str(script)])
    stdout_path = tmp_path / "stdout.log"
    stderr_path = tmp_path / "stderr.log"

    result = run_streamed_command(
        command=[sys.executable, str(script)],
        cwd=tmp_path,
        env=dict(os.environ),
        input_text=None,
        output_session=call,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )

    call.complete(
        status="completed" if result.returncode == 0 else "failed",
        exit_code=result.returncode,
        error_message=None,
        duration_ms=None,
    )

    log_path = settings.data_dir / "claude_calls" / f"{call.call_id}.log"
    output = log_path.read_text(encoding="utf-8", errors="replace")
    assert output == "OUT-1\nERR-1\nOUT-2\n"
