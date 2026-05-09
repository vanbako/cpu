#!/usr/bin/env python3
"""Validate and audit the I28-S03 Gowin report parser."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_gowin_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the Gowin report parser")
    parser.add_argument("--json", action="store_true", help="print the parser profile as JSON")
    parser.add_argument(
        "--audit-reports",
        nargs="?",
        const="build/fpga/tang_mega_138k/first_test",
        metavar="BUILD_ROOT",
        help="parse and audit generated Gowin reports under BUILD_ROOT",
    )
    parser.add_argument(
        "--profile",
        default=fpga_gowin_reports.FPGA_GOWIN_REPORTS_DEFAULT_PROFILE,
        help="clock profile id used for timing-margin policy",
    )
    parser.add_argument("--summary", action="store_true", help="print the parser summary")
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_gowin_reports.fpga_gowin_report_parser_json())
        return 0

    if args.audit_reports:
        build_root = _repo_path(Path(args.audit_reports))
        if build_root is None:
            print("FPGA Gowin report parser:")
            print("- build root must be inside the repository")
            return 1
        try:
            audit = fpga_gowin_reports.audit_gowin_reports(
                ROOT / build_root,
                profile_id=args.profile,
            )
        except KeyError as exc:
            print(f"unknown FPGA clock profile: {exc}")
            return 1
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    issues = fpga_gowin_reports.validate_fpga_gowin_reports(ROOT)
    if issues:
        print("FPGA Gowin report parser issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA Gowin report parser issues: 0")
        return 0

    print(fpga_gowin_reports.render_gowin_report_parser())
    return 0


def _repo_path(path: Path) -> Path | None:
    if not path.is_absolute():
        return path
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
