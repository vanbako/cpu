#!/usr/bin/env python3
"""Validate and print the I23-S03 FPGA memory adapter inventory."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_memory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate FPGA memory adapter RTL and documentation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the FPGA memory adapter inventory as JSON",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_memory.fpga_memory_adapters_json())
        return 0

    issues = fpga_memory.validate_fpga_memory_adapters(ROOT)
    if issues:
        print("FPGA memory adapter issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA memory adapter issues: 0")
        return 0

    print("FPGA memory adapters:")
    for adapter in fpga_memory.fpga_memory_adapters():
        print(f"- {adapter.module}: {adapter.role}, {adapter.response_latency}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
