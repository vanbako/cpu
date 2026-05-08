#!/usr/bin/env python3
"""Validate and print the I23-S05 FPGA synthesis gate profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_synthesis


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the FPGA synthesis gate profile and documentation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the FPGA synthesis gate profile as JSON",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="print the synthesis gate command plan",
    )
    parser.add_argument(
        "--gowin-tcl",
        action="store_true",
        help="print the Gowin Tcl batch template",
    )
    parser.add_argument(
        "--check-reports",
        metavar="BUILD_ROOT",
        help="reserved report-audit entry point for generated Gowin reports",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_synthesis.fpga_synthesis_gate_json())
        return 0

    if args.gowin_tcl:
        print(fpga_synthesis.gowin_tcl_script(), end="")
        return 0

    if args.plan:
        for command in fpga_synthesis.fpga_synthesis_command_plan():
            print(command)
        return 0

    if args.check_reports:
        print(
            "FPGA synthesis report audit is defined but blocked until Gowin "
            f"reports exist under {args.check_reports}"
        )
        return 0

    issues = fpga_synthesis.validate_fpga_synthesis_gate(ROOT)
    if issues:
        print("FPGA synthesis gate issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA synthesis gate issues: 0")
        return 0

    print(fpga_synthesis.render_fpga_synthesis_gate())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
