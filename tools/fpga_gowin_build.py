#!/usr/bin/env python3
"""Validate and audit the I24-S03 Gowin first-test build profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_board_identity, fpga_constraints, fpga_gowin_build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the Gowin build profile and documentation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the Gowin build profile as JSON",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="print the Gowin build command plan",
    )
    parser.add_argument(
        "--audit-reports",
        nargs="?",
        const="build/fpga/tang_mega_138k/first_test",
        metavar="BUILD_ROOT",
        help="audit generated Gowin reports under BUILD_ROOT",
    )
    parser.add_argument(
        "--identity-evidence",
        metavar="PATH",
        help="optional I24-S01 identity evidence path for report audit",
    )
    parser.add_argument(
        "--constraints-evidence",
        metavar="PATH",
        help="optional I24-S02 pin evidence path for report audit",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_gowin_build.fpga_gowin_build_json())
        return 0

    if args.plan:
        for command in fpga_gowin_build.fpga_gowin_command_plan():
            print(command)
        return 0

    if args.audit_reports:
        build_root = _repo_path(Path(args.audit_reports))
        identity_path = _optional_repo_path(args.identity_evidence)
        constraints_path = _optional_repo_path(args.constraints_evidence)
        if build_root is None or identity_path is False or constraints_path is False:
            print("FPGA Gowin report audit:")
            print("- paths must be inside the repository")
            return 1
        identity_audit = fpga_board_identity.load_identity_audit(ROOT, identity_path)
        constraints_audit = fpga_constraints.load_constraint_overlay_audit(
            ROOT,
            constraints_path,
            identity_path,
        )
        audit = fpga_gowin_build.audit_gowin_report_bundle(
            ROOT / build_root,
            identity_audit=identity_audit,
            constraints_audit=constraints_audit,
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    issues = fpga_gowin_build.validate_fpga_gowin_build(ROOT)
    if issues:
        print("FPGA Gowin build issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA Gowin build issues: 0")
        return 0

    print(fpga_gowin_build.render_fpga_gowin_build())
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
