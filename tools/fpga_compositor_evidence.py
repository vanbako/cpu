#!/usr/bin/env python3
"""Validate and print the I36-S06 FPGA compositor evidence archive profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_compositor_evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the compositor evidence profile")
    parser.add_argument("--json", action="store_true", help="print the evidence profile as JSON")
    parser.add_argument("--template", action="store_true", help="print an evidence archive template")
    parser.add_argument("--audit", metavar="PATH", help="audit a specific evidence archive")
    parser.add_argument("--fields", action="store_true", help="list required archive fields")
    parser.add_argument("--blockers", action="store_true", help="list evidence blockers")
    parser.add_argument("--audit-default", action="store_true", help="print the default evidence audit as JSON")
    args = parser.parse_args(argv)

    profile = fpga_compositor_evidence.fpga_compositor_evidence_profile()

    if args.json:
        print(fpga_compositor_evidence.fpga_compositor_evidence_json())
        return 0

    if args.template:
        print(fpga_compositor_evidence.compositor_evidence_template(), end="")
        return 0

    if args.audit:
        path = Path(args.audit)
        if not path.is_absolute():
            path = ROOT / path
        try:
            record = fpga_compositor_evidence.parse_compositor_evidence(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            print(f"could not audit compositor evidence: {exc}")
            return 1
        audit = fpga_compositor_evidence.audit_compositor_evidence(
            record,
            evidence_path=str(path),
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    if args.audit_default:
        print(fpga_compositor_evidence.compositor_evidence_audit_json())
        return 0

    if args.fields:
        for field in profile.required_fields:
            print(f"{field.name}\t{field.required}\t{field.description}")
        return 0

    if args.blockers:
        for blocker in profile.blockers:
            print(blocker)
        return 0

    issues = fpga_compositor_evidence.validate_fpga_compositor_evidence(ROOT)
    if issues:
        print("FPGA compositor evidence issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA compositor evidence issues: 0")
        return 0

    print(fpga_compositor_evidence.render_fpga_compositor_evidence())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
