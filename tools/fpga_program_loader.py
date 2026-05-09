#!/usr/bin/env python3
"""Validate and exercise the I26-S04 FPGA program loader."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_program_loader


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the FPGA program loader")
    parser.add_argument("--json", action="store_true", help="print the loader profile as JSON")
    parser.add_argument("--list", action="store_true", help="list loadable manifest programs")
    parser.add_argument("--run", metavar="PROGRAM_ID", help="install one manifest RAM image in the model")
    parser.add_argument("--rejections", action="store_true", help="print malformed-image rejection fixture results")
    args = parser.parse_args(argv)

    profile = fpga_program_loader.fpga_program_loader_profile()

    if args.list:
        for plan in profile.plans:
            print(
                f"{plan.program_id}\t{plan.target_memory}\t"
                f"0x{plan.base_cell:08X}\t{plan.cell_count}\t{plan.ram_image_sha256}"
            )
        return 0

    if args.run:
        try:
            result = fpga_program_loader.install_manifest_program(args.run)
        except KeyError:
            print(f"unknown FPGA program manifest entry: {args.run}")
            return 1
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0 if result.passed else 1

    if args.rejections:
        results = fpga_program_loader.rejection_fixture_results()
        print(json.dumps([result.as_dict() for result in results], indent=2, sort_keys=True))
        return 0 if all(not result.passed for result in results) else 1

    if args.json:
        print(fpga_program_loader.fpga_program_loader_json())
        return 0

    issues = fpga_program_loader.validate_fpga_program_loader(ROOT)
    if issues:
        print("FPGA program loader issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA program loader issues: 0")
        return 0

    print(fpga_program_loader.render_fpga_program_loader())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
