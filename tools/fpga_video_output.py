#!/usr/bin/env python3
"""Validate and print the I35-S03 FPGA video output boundary profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_video_output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the video output profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--signals", action="store_true", help="list board output signals")
    parser.add_argument("--sdc", action="store_true", help="print generated-clock SDC template")
    parser.add_argument("--plan", action="store_true", help="print Verilator command plan")
    args = parser.parse_args(argv)

    profile = fpga_video_output.fpga_video_output_profile()

    if args.signals:
        for signal in profile.output_signals:
            print(f"{signal.name}\t{signal.width_bits}\t{signal.role}")
        return 0

    if args.sdc:
        print(profile.generated_clock_sdc)
        return 0

    if args.plan:
        for command in fpga_video_output.fpga_video_output_verilator_commands():
            print(command)
        return 0

    if args.json:
        print(fpga_video_output.fpga_video_output_json())
        return 0

    issues = fpga_video_output.validate_fpga_video_output(ROOT)
    if issues:
        print("FPGA video output boundary issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA video output boundary issues: 0")
        return 0

    print(fpga_video_output.render_fpga_video_output())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
