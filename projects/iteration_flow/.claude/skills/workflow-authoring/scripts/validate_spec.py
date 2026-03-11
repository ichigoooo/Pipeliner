#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeliner.protocols.workflow import WorkflowSpec

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output')
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding='utf-8'))
    spec = WorkflowSpec.model_validate(payload)
    canonical = spec.model_dump(by_alias=True, mode='json')
    if args.output:
        Path(args.output).write_text(
            json.dumps(canonical, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
    print(json.dumps(canonical, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
