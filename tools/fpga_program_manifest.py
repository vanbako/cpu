#!/usr/bin/env python3
"""Validate and print the I26-S01 FPGA program-image manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_program_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the FPGA program manifest")
    parser.add_argument("--json", action="store_true", help="print the manifest as JSON")
    parser.add_argument("--list", action="store_true", help="list manifest entry IDs")
    parser.add_argument("--entry", metavar="PROGRAM_ID", help="print one manifest entry as JSON")
    args = parser.parse_args(argv)

    profile = fpga_program_manifest.fpga_program_manifest_profile()

    if args.list:
        for entry in profile.entries:
            print(f"{entry.program_id}\t{entry.source_case_id}\t{entry.board_run_class}")
        return 0

    if args.entry:
        try:
            entry = profile.entry_by_id(args.entry)
        except KeyError:
            print(f"unknown FPGA program manifest entry: {args.entry}")
            return 1
        print(json.dumps(entry.as_dict(), indent=2, sort_keys=True))
        return 0

    if args.json:
        print(fpga_program_manifest.fpga_program_manifest_json())
        return 0

    issues = fpga_program_manifest.validate_fpga_program_manifest(ROOT)
    if issues:
        print("FPGA program manifest issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA program manifest issues: 0")
        return 0

    print(fpga_program_manifest.render_fpga_program_manifest(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
