#!/usr/bin/env python3
"""Validate and audit the I31-S02 first-pass Gowin build evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_first_pass_gowin


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the first-pass Gowin profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--template", action="store_true", help="print a Gowin evidence template")
    parser.add_argument("--audit", metavar="PATH", help="audit a specific key=value evidence record")
    parser.add_argument("--audit-reports", metavar="BUILD_ROOT", help="audit a generated Gowin report bundle")
    parser.add_argument("--requirements", action="store_true", help="list required evidence fields")
    parser.add_argument("--retest", action="store_true", help="list retest commands")
    args = parser.parse_args(argv)

    profile = fpga_first_pass_gowin.fpga_first_pass_gowin_profile()

    if args.json:
        print(fpga_first_pass_gowin.fpga_first_pass_gowin_json())
        return 0

    if args.template:
        print(fpga_first_pass_gowin.first_pass_gowin_template(), end="")
        return 0

    if args.audit:
        path = Path(args.audit)
        if not path.is_absolute():
            path = ROOT / path
        try:
            record = fpga_first_pass_gowin.parse_first_pass_gowin(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            print(f"could not audit first-pass Gowin evidence: {exc}")
            return 1
        audit = fpga_first_pass_gowin.audit_first_pass_gowin(
            record,
            evidence_path=str(path),
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    if args.audit_reports:
        build_root = Path(args.audit_reports)
        if not build_root.is_absolute():
            build_root = ROOT / build_root
        audit = fpga_first_pass_gowin.audit_first_pass_gowin_reports(build_root)
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    if args.requirements:
        for requirement in profile.requirements:
            print(f"{requirement.name}\t{requirement.field}\t{requirement.required_policy}")
        return 0

    if args.retest:
        for command in profile.retest_commands:
            print(command)
        return 0

    issues = fpga_first_pass_gowin.validate_fpga_first_pass_gowin(ROOT)
    if issues:
        print("FPGA first-pass Gowin issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA first-pass Gowin issues: 0")
        return 0

    print(fpga_first_pass_gowin.render_fpga_first_pass_gowin())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
