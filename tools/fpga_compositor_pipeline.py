#!/usr/bin/env python3
"""Validate and print the I36-S03 FPGA compositor pipeline profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the compositor pipeline profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--demo", action="store_true", help="print demo composition pixels")
    parser.add_argument("--rules", action="store_true", help="list composition rules")
    parser.add_argument("--plan", action="store_true", help="print Verilator command inventory")
    args = parser.parse_args(argv)

    profile = fpga_compositor_pipeline.fpga_compositor_pipeline_profile()

    if args.demo:
        print(
            json.dumps(
                [result.as_dict() for result in fpga_compositor_pipeline.demo_composition()],
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.rules:
        for rule in profile.composition_rules:
            print(rule)
        return 0

    if args.plan:
        for command in profile.verilator_commands:
            print(command)
        return 0

    if args.json:
        print(fpga_compositor_pipeline.fpga_compositor_pipeline_json())
        return 0

    issues = fpga_compositor_pipeline.validate_fpga_compositor_pipeline(ROOT)
    if issues:
        print("FPGA compositor pipeline issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA compositor pipeline issues: 0")
        return 0

    print(fpga_compositor_pipeline.render_fpga_compositor_pipeline())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
