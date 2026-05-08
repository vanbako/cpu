#!/usr/bin/env python3
"""Validate and audit the I24-S05 first-board evidence archive."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_first_board_archive


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the archive profile")
    parser.add_argument("--json", action="store_true", help="print the archive profile as JSON")
    parser.add_argument("--template", action="store_true", help="print the archive template")
    parser.add_argument(
        "--audit-archive",
        nargs="?",
        const=str(fpga_first_board_archive.FPGA_ARCHIVE_EVIDENCE),
        metavar="PATH",
        help="audit captured first-board archive evidence",
    )
    parser.add_argument(
        "--programming-evidence",
        metavar="PATH",
        help="optional I24-S04 programming evidence path for archive audit",
    )
    parser.add_argument(
        "--build-root",
        metavar="PATH",
        help="optional I24-S03 Gowin build root for the programming audit",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_first_board_archive.fpga_first_board_archive_json())
        return 0

    if args.template:
        print(fpga_first_board_archive.first_board_archive_template(), end="")
        return 0

    if args.audit_archive:
        archive_path = _repo_path(Path(args.audit_archive))
        programming_path = _optional_repo_path(args.programming_evidence)
        build_root = _optional_repo_path(args.build_root)
        if archive_path is None or programming_path is False or build_root is False:
            print("FPGA first-board archive audit:")
            print("- paths must be inside the repository")
            return 1
        audit = fpga_first_board_archive.load_first_board_archive_audit(
            ROOT,
            archive_path,
            programming_path,
            build_root,
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    issues = fpga_first_board_archive.validate_fpga_first_board_archive(ROOT)
    if issues:
        print("FPGA first-board archive issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA first-board archive issues: 0")
        return 0

    print(fpga_first_board_archive.render_fpga_first_board_archive())
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
