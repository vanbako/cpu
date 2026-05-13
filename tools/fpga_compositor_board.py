#!/usr/bin/env python3
"""Validate and print the I36-S07 FPGA compositor board demo archive profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_board


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the compositor board profile")
    parser.add_argument("--json", action="store_true", help="print the compositor board profile as JSON")
    parser.add_argument("--template", action="store_true", help="print a board evidence template")
    parser.add_argument("--audit", metavar="PATH", help="audit a specific board evidence record")
    parser.add_argument("--fields", action="store_true", help="list required evidence fields")
    parser.add_argument("--retest", action="store_true", help="list retest commands")
    parser.add_argument("--blockers", action="store_true", help="list blocker policy")
    parser.add_argument("--audit-default", action="store_true", help="print the default board audit as JSON")
    args = parser.parse_args(argv)

    profile = fpga_compositor_board.fpga_compositor_board_profile()

    if args.json:
        print(fpga_compositor_board.fpga_compositor_board_json())
        return 0

    if args.template:
        print(fpga_compositor_board.compositor_board_template(), end="")
        return 0

    if args.audit:
        path = Path(args.audit)
        if not path.is_absolute():
            path = ROOT / path
        try:
            record = fpga_compositor_board.parse_compositor_board(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            print(f"could not audit compositor board evidence: {exc}")
            return 1
        audit = fpga_compositor_board.audit_compositor_board(record, evidence_path=str(path))
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    if args.audit_default:
        print(
            json.dumps(
                fpga_compositor_board.load_compositor_board_audit(ROOT).as_dict(),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.fields:
        for field in profile.required_fields:
            print(f"{field.name}\t{field.required}\t{field.description}")
        return 0

    if args.retest:
        for command in profile.retest_commands:
            print(command)
        return 0

    if args.blockers:
        for blocker in profile.blockers:
            print(blocker)
        return 0

    issues = fpga_compositor_board.validate_fpga_compositor_board(ROOT)
    if issues:
        print("FPGA compositor board issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA compositor board issues: 0")
        return 0

    print(fpga_compositor_board.render_fpga_compositor_board())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
