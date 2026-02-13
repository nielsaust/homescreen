#!/usr/bin/env python3
"""Run unit tests for refactored core components."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    print(f"[unit] project root: {ROOT}")
    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT / "tests" / "unit"), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        print("[unit] FAILED")
        return 1
    print("[unit] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
