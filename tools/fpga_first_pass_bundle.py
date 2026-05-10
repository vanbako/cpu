#!/usr/bin/env python3
"""Validate and audit the I31-S01 first-pass FPGA build bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_first_pass_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the bundle profile")
    parser.add_argument("--json", action="store_true", help="print the bundle profile as JSON")
    parser.add_argument("--template", action="store_true", help="print a bundle record template")
    parser.add_argument("--audit", metavar="PATH", help="audit a specific bundle record")
    parser.add_argument("--items", action="store_true", help="list frozen bundle items")
    parser.add_argument("--signatures", action="store_true", help="list expected LED/UART/probe signatures")
    parser.add_argument("--retest", action="store_true", help="list retest commands")
    args = parser.parse_args(argv)

    profile = fpga_first_pass_bundle.fpga_first_pass_bundle_profile()

    if args.json:
        print(fpga_first_pass_bundle.fpga_first_pass_bundle_json())
        return 0

    if args.template:
        print(fpga_first_pass_bundle.first_pass_bundle_template(), end="")
        return 0

    if args.audit:
        path = Path(args.audit)
        if not path.is_absolute():
            path = ROOT / path
        try:
            record = fpga_first_pass_bundle.parse_first_pass_bundle(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            print(f"could not audit first-pass build bundle: {exc}")
            return 1
        audit = fpga_first_pass_bundle.audit_first_pass_bundle(
            record,
            evidence_path=str(path),
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    if args.items:
        for item in profile.items:
            print(f"{item.name}\t{item.value}\t{item.status}\t{item.source_gate}")
        return 0

    if args.signatures:
        for signature in profile.expected_signatures:
            print(f"{signature.interface}\t{signature.expected}")
        return 0

    if args.retest:
        for command in profile.retest_commands:
            print(command)
        return 0

    issues = fpga_first_pass_bundle.validate_fpga_first_pass_bundle(ROOT)
    if issues:
        print("FPGA first-pass build bundle issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA first-pass build bundle issues: 0")
        return 0

    print(fpga_first_pass_bundle.render_fpga_first_pass_bundle())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
