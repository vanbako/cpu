#!/usr/bin/env python3
"""Validate and audit the I24-S01 FPGA board identity profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_board_identity


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the board identity profile and documentation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the board identity profile as JSON",
    )
    parser.add_argument(
        "--template",
        action="store_true",
        help="print the key=value evidence template",
    )
    parser.add_argument(
        "--audit-evidence",
        nargs="?",
        const=str(fpga_board_identity.FPGA_BOARD_IDENTITY_EVIDENCE),
        metavar="PATH",
        help="audit a captured device identity evidence record",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_board_identity.fpga_board_identity_json())
        return 0

    if args.template:
        print(fpga_board_identity.identity_template(), end="")
        return 0

    if args.audit_evidence:
        evidence_path = Path(args.audit_evidence)
        if evidence_path.is_absolute():
            try:
                evidence_path = evidence_path.relative_to(ROOT)
            except ValueError:
                print("FPGA board identity audit:")
                print("- evidence path must be inside the repository")
                return 1
        audit = fpga_board_identity.load_identity_audit(ROOT, evidence_path)
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.confirmed else 1

    issues = fpga_board_identity.validate_fpga_board_identity(ROOT)
    if issues:
        print("FPGA board identity issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA board identity issues: 0")
        return 0

    print(fpga_board_identity.render_board_identity_profile())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
