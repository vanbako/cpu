#!/usr/bin/env python3
"""Validate and audit the I34-S01 Tang Retro Console 60K SOM identity gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_retro_console_identity


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the Retro Console profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--template", action="store_true", help="print the evidence template")
    parser.add_argument(
        "--audit-evidence",
        nargs="?",
        const=str(fpga_retro_console_identity.FPGA_RETRO_CONSOLE_IDENTITY_EVIDENCE),
        metavar="PATH",
        help="audit a captured Retro Console identity record",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_retro_console_identity.fpga_retro_console_identity_json())
        return 0

    if args.template:
        print(fpga_retro_console_identity.identity_template(), end="")
        return 0

    if args.audit_evidence:
        evidence_path = Path(args.audit_evidence)
        if evidence_path.is_absolute():
            try:
                evidence_path = evidence_path.relative_to(ROOT)
            except ValueError:
                print("FPGA Retro Console identity audit:")
                print("- evidence path must be inside the repository")
                return 1
        audit = fpga_retro_console_identity.load_identity_audit(ROOT, evidence_path)
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.selected else 1

    issues = fpga_retro_console_identity.validate_fpga_retro_console_identity(ROOT)
    if issues:
        print("FPGA Retro Console identity issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA Retro Console identity issues: 0")
        return 0

    print(fpga_retro_console_identity.render_retro_console_identity())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
