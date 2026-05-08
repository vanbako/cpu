#!/usr/bin/env python3
"""Validate and audit the I24-S02 Tang Mega 138K constraint overlay."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_constraints


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the constraint overlay profile, templates, and documentation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the constraint overlay profile as JSON",
    )
    parser.add_argument(
        "--template",
        action="store_true",
        help="print the CST template",
    )
    parser.add_argument(
        "--sdc",
        action="store_true",
        help="print the SDC timing constraints",
    )
    parser.add_argument(
        "--evidence-template",
        action="store_true",
        help="print the pin evidence template",
    )
    parser.add_argument(
        "--audit-evidence",
        nargs="?",
        const=str(fpga_constraints.FPGA_CONSTRAINTS_EVIDENCE),
        metavar="PATH",
        help="audit captured pin evidence together with I24-S01 identity evidence",
    )
    parser.add_argument(
        "--identity-evidence",
        metavar="PATH",
        help="optional path to the I24-S01 identity evidence record",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_constraints.fpga_constraints_overlay_json())
        return 0

    if args.template:
        print(fpga_constraints.cst_template(), end="")
        return 0

    if args.sdc:
        print(fpga_constraints.sdc_template(), end="")
        return 0

    if args.evidence_template:
        print(fpga_constraints.constraint_evidence_template(), end="")
        return 0

    if args.audit_evidence:
        evidence_path = _repo_relative_path(Path(args.audit_evidence))
        identity_evidence_path = (
            _repo_relative_path(Path(args.identity_evidence))
            if args.identity_evidence
            else None
        )
        if evidence_path is None or (args.identity_evidence and identity_evidence_path is None):
            print("FPGA constraints overlay audit:")
            print("- evidence paths must be inside the repository")
            return 1
        audit = fpga_constraints.load_constraint_overlay_audit(
            ROOT,
            evidence_path,
            identity_evidence_path,
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.confirmed else 1

    issues = fpga_constraints.validate_fpga_constraints_overlay(ROOT)
    if issues:
        print("FPGA constraints overlay issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA constraints overlay issues: 0")
        return 0

    print(fpga_constraints.render_fpga_constraints_overlay())
    return 0


def _repo_relative_path(path: Path) -> Path | None:
    if not path.is_absolute():
        return path
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
