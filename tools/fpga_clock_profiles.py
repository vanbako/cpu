#!/usr/bin/env python3
"""Validate and print the I28-S01 FPGA clock profiles."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_clock_profiles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the FPGA clock profiles")
    parser.add_argument("--json", action="store_true", help="print the clock profiles as JSON")
    parser.add_argument("--plan", action="store_true", help="print the clock-profile command plan")
    parser.add_argument("--profiles", action="store_true", help="list clock profile identifiers")
    parser.add_argument(
        "--sdc",
        nargs="?",
        const=fpga_clock_profiles.DEBUG_PROFILE_ID,
        metavar="PROFILE_ID",
        help="print the SDC fragment for PROFILE_ID",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_clock_profiles.fpga_clock_profiles_json())
        return 0

    if args.plan:
        for command in fpga_clock_profiles.fpga_clock_command_plan():
            print(command)
        return 0

    if args.profiles:
        profile_set = fpga_clock_profiles.fpga_clock_profile_set()
        for profile in profile_set.profiles:
            selected = "current" if profile.selected_for_current_build else "available"
            print(f"{profile.profile_id}\t{profile.role}\t{profile.status}\t{selected}")
        return 0

    if args.sdc is not None:
        try:
            print(fpga_clock_profiles.clock_profile_sdc(args.sdc), end="")
        except KeyError as exc:
            print(f"unknown FPGA clock profile: {exc}")
            return 1
        return 0

    issues = fpga_clock_profiles.validate_fpga_clock_profiles(ROOT)
    if issues:
        print("FPGA clock profile issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA clock profile issues: 0")
        return 0

    print(fpga_clock_profiles.render_fpga_clock_profiles())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
