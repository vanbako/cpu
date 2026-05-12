#!/usr/bin/env python3
"""Validate and print the I35-S04 FPGA video MMIO/IRQ profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_video_mmio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the video MMIO profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--registers", action="store_true", help="list video register behavior")
    parser.add_argument("--irq-demo", action="store_true", help="print the executable vblank IRQ demo")
    parser.add_argument("--plan", action="store_true", help="print the Verilator command")
    args = parser.parse_args(argv)

    profile = fpga_video_mmio.fpga_video_mmio_profile()

    if args.registers:
        for behavior in profile.register_behaviors:
            print(f"{behavior.register}\t{behavior.behavior}")
        return 0

    if args.irq_demo:
        print(json.dumps(fpga_video_mmio.simulate_video_mmio_irq_demo().as_dict(), indent=2, sort_keys=True))
        return 0

    if args.plan:
        print(profile.verilator_command)
        return 0

    if args.json:
        print(fpga_video_mmio.fpga_video_mmio_json())
        return 0

    issues = fpga_video_mmio.validate_fpga_video_mmio(ROOT)
    if issues:
        print("FPGA video MMIO issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA video MMIO issues: 0")
        return 0

    print(fpga_video_mmio.render_fpga_video_mmio())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
