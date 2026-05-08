#!/usr/bin/env python3
"""Validate and inspect the I25-S01 FPGA debug/status packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_debug_status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the debug/status packet profile")
    parser.add_argument("--json", action="store_true", help="print the packet profile as JSON")
    parser.add_argument("--example", action="store_true", help="print an example packet as hex")
    parser.add_argument("--decode-hex", metavar="HEX", help="decode a 32-byte packet hex string")
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_debug_status.fpga_debug_status_json())
        return 0

    if args.example:
        packet = fpga_debug_status.example_debug_status_packet()
        print(fpga_debug_status.encode_debug_status_packet(packet).hex())
        return 0

    if args.decode_hex:
        try:
            payload = bytes.fromhex(args.decode_hex)
            packet = fpga_debug_status.decode_debug_status_packet(payload)
        except ValueError as exc:
            print("FPGA debug/status packet decode failed:")
            print(f"- {exc}")
            return 1
        print(json.dumps(packet.as_dict(), indent=2, sort_keys=True))
        return 0

    issues = fpga_debug_status.validate_fpga_debug_status(ROOT)
    if issues:
        print("FPGA debug/status packet issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA debug/status packet issues: 0")
        return 0

    print(fpga_debug_status.render_fpga_debug_status_profile())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
