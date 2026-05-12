#!/usr/bin/env python3
"""Validate and print the I35-S02 FPGA video timing scanout profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_video_timing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the video timing profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--plan", action="store_true", help="print Verilator command plan")
    parser.add_argument("--frame-summary", action="store_true", help="print one-frame timing summary as JSON")
    args = parser.parse_args(argv)

    if args.plan:
        for command in fpga_video_timing.fpga_video_timing_verilator_commands():
            print(command)
        return 0

    if args.frame_summary:
        print(json.dumps(fpga_video_timing.summarize_one_frame().as_dict(), indent=2, sort_keys=True))
        return 0

    if args.json:
        print(fpga_video_timing.fpga_video_timing_json())
        return 0

    issues = fpga_video_timing.validate_fpga_video_timing(ROOT)
    if issues:
        print("FPGA video timing issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA video timing issues: 0")
        return 0

    print(fpga_video_timing.render_fpga_video_timing())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
