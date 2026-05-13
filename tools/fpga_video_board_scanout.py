#!/usr/bin/env python3
"""Validate and audit the I35-S06 FPGA video board scanout archive."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_video_board_scanout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the video board scanout archive profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--template", action="store_true", help="print an archive template")
    parser.add_argument("--audit", metavar="PATH", help="audit a specific key=value archive record")
    parser.add_argument("--fields", action="store_true", help="list required archive fields")
    parser.add_argument("--retest", action="store_true", help="list retest commands")
    args = parser.parse_args(argv)

    profile = fpga_video_board_scanout.fpga_video_board_scanout_profile()

    if args.json:
        print(fpga_video_board_scanout.fpga_video_board_scanout_json())
        return 0

    if args.template:
        print(fpga_video_board_scanout.video_board_scanout_template(), end="")
        return 0

    if args.audit:
        path = Path(args.audit)
        if not path.is_absolute():
            path = ROOT / path
        try:
            record = fpga_video_board_scanout.parse_video_board_scanout(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            print(f"could not audit video board scanout evidence: {exc}")
            return 1
        audit = fpga_video_board_scanout.audit_video_board_scanout(
            record,
            evidence_path=str(path),
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    if args.fields:
        for field in profile.required_fields:
            print(f"{field.name}\t{field.required}\t{field.description}")
        return 0

    if args.retest:
        for command in profile.retest_commands:
            print(command)
        return 0

    issues = fpga_video_board_scanout.validate_fpga_video_board_scanout(ROOT)
    if issues:
        print("FPGA video board scanout issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA video board scanout issues: 0")
        return 0

    print(fpga_video_board_scanout.render_fpga_video_board_scanout())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
