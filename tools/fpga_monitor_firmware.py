#!/usr/bin/env python3
"""Validate and print the I32-S02 FPGA monitor firmware fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_monitor_firmware


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate monitor firmware fixtures")
    parser.add_argument("--json", action="store_true", help="print the fixture profile as JSON")
    parser.add_argument("--fixtures", action="store_true", help="run all firmware fixtures as JSON")
    parser.add_argument("--list", action="store_true", help="list fixture IDs")
    parser.add_argument("--run-fixture", metavar="ID", help="run one fixture as JSON")
    args = parser.parse_args(argv)

    profile = fpga_monitor_firmware.fpga_monitor_firmware_profile()

    if args.json:
        print(fpga_monitor_firmware.fpga_monitor_firmware_json())
        return 0

    if args.fixtures:
        print(fpga_monitor_firmware.fpga_monitor_firmware_run_json())
        return 0

    if args.list:
        for fixture in profile.fixtures:
            print(f"{fixture.fixture_id}\t{fixture.expected_final_state}")
        return 0

    if args.run_fixture:
        try:
            run = fpga_monitor_firmware.run_monitor_firmware_fixture(args.run_fixture)
        except KeyError:
            print(f"unknown monitor firmware fixture: {args.run_fixture}")
            return 1
        print(json.dumps(run.as_dict(), indent=2, sort_keys=True))
        return 0 if run.passed else 1

    issues = fpga_monitor_firmware.validate_fpga_monitor_firmware(ROOT)
    if issues:
        print("FPGA monitor firmware issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA monitor firmware issues: 0")
        return 0

    print(fpga_monitor_firmware.render_fpga_monitor_firmware(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
