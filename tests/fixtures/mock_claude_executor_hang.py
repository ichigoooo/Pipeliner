from __future__ import annotations

import sys
import time


def main() -> int:
    if len(sys.argv) < 2:
        return 2
    time.sleep(2.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
