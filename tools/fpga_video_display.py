#!/usr/bin/env python3
"""Validate and print the I35-S01 FPGA video display profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_video_display


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the FPGA video profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--registers", action="store_true", help="list video MMIO registers")
    parser.add_argument("--signals", action="store_true", help="list framebuffer read-master signals")
    args = parser.parse_args(argv)

    profile = fpga_video_display.fpga_video_display_profile()

    if args.registers:
        for register in profile.mmio.registers:
            print(
                f"{register.name}\t0x{profile.mmio.base_cell + register.offset_cell:08X}"
                f"\t{register.access}\t{register.width_bits}"
            )
        return 0

    if args.signals:
        for signal in profile.read_master_signals:
            print(f"{signal.name}\t{signal.direction}\t{signal.width_bits}")
        return 0

    if args.json:
        print(fpga_video_display.fpga_video_display_json())
        return 0

    issues = fpga_video_display.validate_fpga_video_display(ROOT)
    if issues:
        print("FPGA video display profile issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA video display profile issues: 0")
        return 0

    print(fpga_video_display.render_fpga_video_display_profile())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
