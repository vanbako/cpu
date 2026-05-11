#!/usr/bin/env python3
"""Validate and print the I32-S03 FPGA monitor multi-program session."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_monitor_session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the monitor session profile")
    parser.add_argument("--json", action="store_true", help="print the monitor session profile as JSON")
    parser.add_argument("--run", action="store_true", help="run the default session as JSON")
    parser.add_argument("--list", action="store_true", help="list selected session cases")
    args = parser.parse_args(argv)

    profile = fpga_monitor_session.fpga_monitor_session_profile()

    if args.json:
        print(fpga_monitor_session.fpga_monitor_session_json())
        return 0

    if args.run:
        print(fpga_monitor_session.fpga_monitor_session_run_json())
        return 0

    if args.list:
        for selection in profile.selected_cases:
            print(f"{selection.case_id}\t{selection.program_id}\t{selection.expected_result}")
        return 0

    issues = fpga_monitor_session.validate_fpga_monitor_session(ROOT)
    if issues:
        print("FPGA monitor session issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA monitor session issues: 0")
        return 0

    print(fpga_monitor_session.render_fpga_monitor_session(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
