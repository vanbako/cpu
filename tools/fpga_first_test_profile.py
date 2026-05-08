#!/usr/bin/env python3
"""Validate and print the I23-S01 FPGA first-test profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_first_test


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the FPGA first-test profile and documentation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the FPGA first-test profile as JSON",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_first_test.fpga_first_test_profile_json())
        return 0

    issues = fpga_first_test.validate_fpga_first_test_profile(
        root=ROOT,
    )
    if issues:
        print("FPGA first-test profile issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA first-test profile issues: 0")
        return 0

    print(
        fpga_first_test.render_fpga_first_test_profile(
            fpga_first_test.FPGA_FIRST_TEST_PROFILE,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
