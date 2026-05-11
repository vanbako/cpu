#!/usr/bin/env python3
"""Validate and audit the I32-S06 FPGA monitor board-session evidence gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_monitor_board_session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the board-session profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--template", action="store_true", help="print the evidence template")
    parser.add_argument(
        "--audit-evidence",
        nargs="?",
        const=str(fpga_monitor_board_session.FPGA_MONITOR_BOARD_SESSION_EVIDENCE),
        metavar="PATH",
        help="audit captured I32-S06 board-session evidence",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_monitor_board_session.fpga_monitor_board_session_json())
        return 0

    if args.template:
        print(fpga_monitor_board_session.board_session_template(), end="")
        return 0

    if args.audit_evidence:
        evidence_path = _repo_relative_path(Path(args.audit_evidence))
        if evidence_path is None:
            print("FPGA monitor board-session audit:")
            print("- evidence path must be inside the repository")
            return 1
        audit = fpga_monitor_board_session.load_board_session_audit(ROOT, evidence_path)
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.accepted else 1

    issues = fpga_monitor_board_session.validate_fpga_monitor_board_session(ROOT)
    if issues:
        print("FPGA monitor board-session issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA monitor board-session issues: 0")
        return 0

    print(fpga_monitor_board_session.render_fpga_monitor_board_session())
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
