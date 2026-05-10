#!/usr/bin/env python3
"""Validate and print the I31-S06 board retest matrix."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_first_pass_retest_matrix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the retest matrix")
    parser.add_argument("--json", action="store_true", help="print the retest matrix profile as JSON")
    parser.add_argument("--commands", action="store_true", help="list retest commands")
    parser.add_argument("--captures", action="store_true", help="list required captures by phase")
    parser.add_argument("--criteria", action="store_true", help="list first-pass and blocker acceptance criteria")
    args = parser.parse_args(argv)

    profile = fpga_first_pass_retest_matrix.fpga_first_pass_retest_matrix_profile()

    if args.json:
        print(fpga_first_pass_retest_matrix.fpga_first_pass_retest_matrix_json())
        return 0

    if args.commands:
        for row in profile.matrix_rows:
            print(f"{row.phase}\t{row.command}")
        return 0

    if args.captures:
        for row in profile.matrix_rows:
            print(f"{row.phase}: {'; '.join(row.required_captures)}")
        return 0

    if args.criteria:
        print("first_pass:")
        for criterion in profile.first_pass_acceptance:
            print(f"- {criterion}")
        print("blocker:")
        for criterion in profile.blocker_acceptance:
            print(f"- {criterion}")
        return 0

    issues = fpga_first_pass_retest_matrix.validate_fpga_first_pass_retest_matrix(ROOT)
    if issues:
        print("FPGA first-pass retest matrix issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA first-pass retest matrix issues: 0")
        return 0

    print(fpga_first_pass_retest_matrix.render_fpga_first_pass_retest_matrix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
