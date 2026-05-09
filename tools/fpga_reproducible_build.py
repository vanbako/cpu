#!/usr/bin/env python3
"""Validate and print the I28-S05 reproducible FPGA build profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_reproducible_build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the reproducible build profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--template", action="store_true", help="print the manifest template")
    parser.add_argument("--steps", action="store_true", help="print reproduction steps")
    parser.add_argument("--artifacts", action="store_true", help="print required artifacts")
    args = parser.parse_args(argv)

    profile = fpga_reproducible_build.fpga_reproducible_build_profile()

    if args.json:
        print(fpga_reproducible_build.fpga_reproducible_build_json())
        return 0

    if args.template:
        print(fpga_reproducible_build.reproducible_build_manifest_template(), end="")
        return 0

    if args.steps:
        for step in profile.reproduction_steps:
            print(step)
        return 0

    if args.artifacts:
        for artifact in profile.artifacts:
            required = "required" if artifact.required else "optional"
            print(f"{artifact.name}\t{artifact.path}\t{artifact.captured_status}\t{required}")
        return 0

    issues = fpga_reproducible_build.validate_fpga_reproducible_build(ROOT)
    if issues:
        print("FPGA reproducible build issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA reproducible build issues: 0")
        return 0

    print(fpga_reproducible_build.render_fpga_reproducible_build())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
