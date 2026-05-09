#!/usr/bin/env python3
"""Validate and print the I28-S04 FPGA frequency-margin profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_frequency_margin, fpga_gowin_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the frequency margin profile")
    parser.add_argument("--json", action="store_true", help="print the default summary as JSON")
    parser.add_argument("--template", action="store_true", help="print the sweep evidence template")
    parser.add_argument(
        "--audit-reports",
        nargs="?",
        const="build/fpga/tang_mega_138k/first_test",
        metavar="BUILD_ROOT",
        help="parse one report bundle as a frequency sweep point",
    )
    parser.add_argument("--requested-hz", type=int, help="requested clock frequency for --audit-reports")
    parser.add_argument(
        "--profile",
        default=fpga_gowin_reports.FPGA_GOWIN_REPORTS_DEFAULT_PROFILE,
        help="clock profile id used for --audit-reports",
    )
    args = parser.parse_args(argv)

    if args.template:
        print(fpga_frequency_margin.frequency_evidence_template(), end="")
        return 0

    if args.json:
        print(fpga_frequency_margin.fpga_frequency_margin_json())
        return 0

    if args.audit_reports:
        build_root = _repo_path(Path(args.audit_reports))
        if build_root is None:
            print("FPGA frequency margin:")
            print("- build root must be inside the repository")
            return 1
        try:
            report_audit = fpga_gowin_reports.audit_gowin_reports(
                ROOT / build_root,
                profile_id=args.profile,
            )
            point = fpga_frequency_margin.sweep_point_from_report_audit(
                report_audit,
                requested_hz=args.requested_hz,
            )
        except KeyError as exc:
            print(f"unknown FPGA clock profile: {exc}")
            return 1
        summary = fpga_frequency_margin.fpga_frequency_margin_summary((point,))
        print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))
        return 0 if report_audit.passed else 1

    issues = fpga_frequency_margin.validate_fpga_frequency_margin(ROOT)
    if issues:
        print("FPGA frequency margin issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA frequency margin issues: 0")
        return 0

    print(fpga_frequency_margin.render_fpga_frequency_margin())
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
