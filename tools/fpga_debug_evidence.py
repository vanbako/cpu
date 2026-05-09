#!/usr/bin/env python3
"""Validate and audit the I25-S05 FPGA debug-evidence gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_debug_evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the debug evidence profile")
    parser.add_argument("--json", action="store_true", help="print the debug evidence profile as JSON")
    parser.add_argument("--template", action="store_true", help="print the debug evidence template")
    parser.add_argument(
        "--audit-evidence",
        nargs="?",
        const=str(fpga_debug_evidence.FPGA_DEBUG_EVIDENCE_PATH),
        metavar="PATH",
        help="audit captured I25-S05 debug evidence",
    )
    parser.add_argument(
        "--archive",
        metavar="PATH",
        help="optional I24-S05 first-board archive path for the debug evidence audit",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_debug_evidence.fpga_debug_evidence_json())
        return 0

    if args.template:
        print(fpga_debug_evidence.debug_evidence_template(), end="")
        return 0

    if args.audit_evidence:
        evidence_path = _repo_path(Path(args.audit_evidence))
        archive_path = _optional_repo_path(args.archive)
        if evidence_path is None or archive_path is False:
            print("FPGA debug evidence audit:")
            print("- paths must be inside the repository")
            return 1
        audit = fpga_debug_evidence.load_debug_evidence_audit(
            ROOT,
            evidence_path,
            archive_path,
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    issues = fpga_debug_evidence.validate_fpga_debug_evidence(ROOT)
    if issues:
        print("FPGA debug evidence issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA debug evidence issues: 0")
        return 0

    print(fpga_debug_evidence.render_fpga_debug_evidence_profile())
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
