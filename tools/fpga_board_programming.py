#!/usr/bin/env python3
"""Validate and audit the I24-S04 SRAM programming evidence profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_programming


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the programming profile")
    parser.add_argument("--json", action="store_true", help="print the programming profile as JSON")
    parser.add_argument("--template", action="store_true", help="print the evidence template")
    parser.add_argument(
        "--audit-evidence",
        nargs="?",
        const=str(fpga_programming.FPGA_PROGRAMMING_EVIDENCE),
        metavar="PATH",
        help="audit captured SRAM programming evidence",
    )
    parser.add_argument(
        "--build-root",
        metavar="PATH",
        help="optional I24-S03 Gowin build root for the programming audit",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_programming.fpga_programming_json())
        return 0

    if args.template:
        print(fpga_programming.programming_evidence_template(), end="")
        return 0

    if args.audit_evidence:
        evidence_path = _repo_path(Path(args.audit_evidence))
        build_root = _optional_repo_path(args.build_root)
        if evidence_path is None or build_root is False:
            print("FPGA board programming audit:")
            print("- paths must be inside the repository")
            return 1
        audit = fpga_programming.load_programming_audit(ROOT, evidence_path, build_root)
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    issues = fpga_programming.validate_fpga_programming(ROOT)
    if issues:
        print("FPGA board programming issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA board programming issues: 0")
        return 0

    print(fpga_programming.render_fpga_programming_profile())
    return 0


def _repo_path(path: Path) -> Path | None:
    if not path.is_absolute():
        return path
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return None


def _optional_repo_path(raw: str | None) -> Path | None | bool:
    if raw is None:
        return None
    return _repo_path(Path(raw)) or False


if __name__ == "__main__":
    raise SystemExit(main())
