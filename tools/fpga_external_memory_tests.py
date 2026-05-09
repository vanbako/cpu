#!/usr/bin/env python3
"""Validate and print the I29-S03 FPGA external-memory test firmware profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_external_memory_tests


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the external-memory tests")
    parser.add_argument("--json", action="store_true", help="print the firmware profile as JSON")
    parser.add_argument("--run", action="store_true", help="run the modeled firmware tests as JSON")
    parser.add_argument("--cases", action="store_true", help="list test cases")
    parser.add_argument("--progress", action="store_true", help="print progress status codes")
    args = parser.parse_args(argv)

    profile = fpga_external_memory_tests.fpga_external_memory_tests_profile()

    if args.json:
        print(fpga_external_memory_tests.fpga_external_memory_tests_json())
        return 0

    if args.run:
        print(fpga_external_memory_tests.fpga_external_memory_tests_run_json())
        return 0

    if args.cases:
        for case in profile.cases:
            print(f"{case.case_id}\t{case.category}\t0x{case.progress_code:06X}")
        return 0

    if args.progress:
        run = fpga_external_memory_tests.run_fpga_external_memory_tests()
        print(json.dumps([f"0x{code:06X}" for code in run.status_codes], indent=2))
        return 0

    issues = fpga_external_memory_tests.validate_fpga_external_memory_tests(ROOT)
    if issues:
        print("FPGA external-memory test issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA external-memory test issues: 0")
        return 0

    print(fpga_external_memory_tests.render_fpga_external_memory_tests())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
