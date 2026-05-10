#!/usr/bin/env python3
"""Validate and print the I32-S01 interactive monitor command profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_monitor_profile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the monitor profile")
    parser.add_argument("--json", action="store_true", help="print the monitor profile as JSON")
    parser.add_argument("--commands", action="store_true", help="list monitor commands")
    parser.add_argument("--status-codes", action="store_true", help="list monitor status codes")
    parser.add_argument("--audit-command", metavar="NAME", help="audit one command shape")
    parser.add_argument("--transport", default=fpga_monitor_profile.TRANSPORT_UART, help="transport for --audit-command")
    parser.add_argument("--target-memory", default="", help="target memory for --audit-command")
    parser.add_argument("--cell-count", type=int, default=0, help="cell count for --audit-command")
    parser.add_argument("--running", action="store_true", help="audit as if the monitor is not halted")
    parser.add_argument("--tagged", action="store_true", help="audit a command with nonzero tag bits")
    args = parser.parse_args(argv)

    profile = fpga_monitor_profile.fpga_monitor_profile()

    if args.json:
        print(fpga_monitor_profile.fpga_monitor_profile_json())
        return 0

    if args.commands:
        for command in profile.commands:
            print(f"{command.name}\t0x{command.opcode:02X}\t{command.requires_halted}\t{command.memory_policy}")
        return 0

    if args.status_codes:
        for name, code in profile.status_codes.items():
            print(f"{name}\t0x{code:04X}")
        return 0

    if args.audit_command:
        audit = fpga_monitor_profile.audit_monitor_command(
            args.audit_command,
            transport=args.transport,
            target_memory=args.target_memory,
            cell_count=args.cell_count,
            halted=not args.running,
            tag_bits_all_zero=not args.tagged,
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.passed else 1

    issues = fpga_monitor_profile.validate_fpga_monitor_profile(ROOT)
    if issues:
        print("FPGA monitor profile issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA monitor profile issues: 0")
        return 0

    print(fpga_monitor_profile.render_fpga_monitor_profile())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
