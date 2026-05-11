#!/usr/bin/env python3
"""Validate and audit the I34-S05 Retro Console failure replay gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_retro_console_replay


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the replay classification profile")
    parser.add_argument("--json", action="store_true", help="print the profile as JSON")
    parser.add_argument("--template", action="store_true", help="print an evidence template")
    parser.add_argument("--audit", metavar="PATH", help="audit a specific key=value classification record")
    parser.add_argument("--classes", action="store_true", help="list allowed failure classes")
    parser.add_argument("--retest", action="store_true", help="list retest commands")
    args = parser.parse_args(argv)

    profile = fpga_retro_console_replay.fpga_retro_console_replay_profile()

    if args.json:
        print(fpga_retro_console_replay.fpga_retro_console_replay_json())
        return 0

    if args.template:
        print(fpga_retro_console_replay.retro_console_replay_template(), end="")
        return 0

    if args.audit:
        path = Path(args.audit)
        if not path.is_absolute():
            path = ROOT / path
        try:
            record = fpga_retro_console_replay.parse_retro_console_replay(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            print(f"could not audit Retro Console replay evidence: {exc}")
            return 1
        audit = fpga_retro_console_replay.audit_retro_console_replay(
            record,
            evidence_path=str(path),
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    if args.classes:
        for failure_class in profile.failure_classes:
            print(failure_class)
        return 0

    if args.retest:
        for command in profile.retest_commands:
            print(command)
        return 0

    issues = fpga_retro_console_replay.validate_fpga_retro_console_replay(ROOT)
    if issues:
        print("FPGA Retro Console replay issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA Retro Console replay issues: 0")
        return 0

    print(fpga_retro_console_replay.render_fpga_retro_console_replay())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
