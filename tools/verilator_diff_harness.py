#!/usr/bin/env python3
"""Run or dry-run the I20-S04 Verilator differential harness skeleton."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import verilator_harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--build-dir",
        default="build/verilator",
        help="Verilator build directory boundary",
    )
    parser.add_argument(
        "--observed-trace",
        help="compare an existing observed retire_trace.json against the golden corpus",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="attempt a non-dry-run RTL boundary if Verilator is available",
    )
    parser.add_argument(
        "--require-verilator",
        action="store_true",
        help="return failure instead of skip when Verilator is unavailable",
    )
    parser.add_argument(
        "--verilator",
        default="verilator",
        help="Verilator executable name or path",
    )
    args = parser.parse_args(argv)

    result = verilator_harness.run_harness(
        verilator_harness.HarnessConfig(
            build_dir=Path(args.build_dir),
            observed_trace=Path(args.observed_trace) if args.observed_trace else None,
            dry_run=not args.run,
            verilator_executable=args.verilator,
            require_verilator=args.require_verilator,
        )
    )
    print(verilator_harness.harness_summary(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
