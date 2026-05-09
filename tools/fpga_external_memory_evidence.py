#!/usr/bin/env python3
"""Validate and print the I29-S05 FPGA external-memory evidence profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_external_memory_evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the evidence profile")
    parser.add_argument("--json", action="store_true", help="print the evidence profile as JSON")
    parser.add_argument("--template", action="store_true", help="print an evidence record template")
    parser.add_argument("--audit", metavar="PATH", help="audit a specific evidence record")
    parser.add_argument("--fields", action="store_true", help="list required evidence fields")
    parser.add_argument("--blockers", action="store_true", help="list evidence blockers")
    args = parser.parse_args(argv)

    profile = fpga_external_memory_evidence.fpga_external_memory_evidence_profile()

    if args.json:
        print(fpga_external_memory_evidence.fpga_external_memory_evidence_json())
        return 0

    if args.template:
        print(fpga_external_memory_evidence.external_memory_evidence_template(), end="")
        return 0

    if args.audit:
        path = Path(args.audit)
        if not path.is_absolute():
            path = ROOT / path
        try:
            record = fpga_external_memory_evidence.parse_external_memory_evidence(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            print(f"could not audit external-memory evidence: {exc}")
            return 1
        audit = fpga_external_memory_evidence.audit_external_memory_evidence(
            record,
            evidence_path=str(path),
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    if args.fields:
        for field in profile.required_fields:
            print(f"{field.name}\t{field.required}\t{field.description}")
        return 0

    if args.blockers:
        for blocker in profile.blockers:
            print(blocker)
        return 0

    issues = fpga_external_memory_evidence.validate_fpga_external_memory_evidence(ROOT)
    if issues:
        print("FPGA external-memory evidence issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA external-memory evidence issues: 0")
        return 0

    print(fpga_external_memory_evidence.render_fpga_external_memory_evidence())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
