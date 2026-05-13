#!/usr/bin/env python3
"""Validate and print the I36-S04 FPGA compositor vblank descriptor profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_vblank


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the compositor vblank profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--demo", action="store_true", help="print descriptor update demo states")
    parser.add_argument("--fields", action="store_true", help="list descriptor fields")
    parser.add_argument("--plan", action="store_true", help="print Verilator command inventory")
    args = parser.parse_args(argv)

    profile = fpga_compositor_vblank.fpga_compositor_vblank_profile()

    if args.demo:
        print(
            json.dumps(
                [state.as_dict() for state in fpga_compositor_vblank.demo_vblank_update()],
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.fields:
        for field in profile.descriptor_fields:
            print(field)
        return 0

    if args.plan:
        for command in profile.verilator_commands:
            print(command)
        return 0

    if args.json:
        print(fpga_compositor_vblank.fpga_compositor_vblank_json())
        return 0

    issues = fpga_compositor_vblank.validate_fpga_compositor_vblank(ROOT)
    if issues:
        print("FPGA compositor vblank issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA compositor vblank issues: 0")
        return 0

    print(fpga_compositor_vblank.render_fpga_compositor_vblank())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
