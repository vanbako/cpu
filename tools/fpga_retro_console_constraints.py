#!/usr/bin/env python3
"""Validate and audit the I34-S02 Retro Console constraints overlay."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_retro_console_constraints


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the overlay")
    parser.add_argument("--json", action="store_true", help="print the overlay profile as JSON")
    parser.add_argument("--template", action="store_true", help="print the CST template")
    parser.add_argument("--sdc-template", action="store_true", help="print the SDC template")
    parser.add_argument(
        "--evidence-template",
        action="store_true",
        help="print the pin evidence template",
    )
    parser.add_argument(
        "--audit-evidence",
        nargs="?",
        const=str(fpga_retro_console_constraints.RETRO_CONSOLE_CONSTRAINT_EVIDENCE),
        metavar="PATH",
        help="audit captured pin evidence with I34-S01 identity evidence",
    )
    parser.add_argument(
        "--identity-evidence",
        metavar="PATH",
        help="optional path to the I34-S01 identity evidence record",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_retro_console_constraints.fpga_retro_console_constraints_json())
        return 0

    if args.template:
        print(fpga_retro_console_constraints.cst_template(), end="")
        return 0

    if args.sdc_template:
        print(fpga_retro_console_constraints.sdc_template(), end="")
        return 0

    if args.evidence_template:
        print(fpga_retro_console_constraints.constraint_evidence_template(), end="")
        return 0

    if args.audit_evidence:
        evidence_path = _repo_relative_path(Path(args.audit_evidence))
        identity_evidence_path = (
            _repo_relative_path(Path(args.identity_evidence))
            if args.identity_evidence
            else None
        )
        if evidence_path is None or (args.identity_evidence and identity_evidence_path is None):
            print("FPGA Retro Console constraints audit:")
            print("- evidence paths must be inside the repository")
            return 1
        audit = fpga_retro_console_constraints.load_constraint_overlay_audit(
            ROOT,
            evidence_path,
            identity_evidence_path,
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.confirmed else 1

    issues = fpga_retro_console_constraints.validate_fpga_retro_console_constraints(ROOT)
    if issues:
        print("FPGA Retro Console constraints issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA Retro Console constraints issues: 0")
        return 0

    print(fpga_retro_console_constraints.render_retro_console_constraints())
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
