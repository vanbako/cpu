#!/usr/bin/env python3
"""Map I25 FPGA debug/status captures to Verilator replay commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_replay_mapper


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the replay mapper profile")
    parser.add_argument("--json", action="store_true", help="print the replay mapper profile as JSON")
    parser.add_argument("--example", action="store_true", help="print an example replay mapping as JSON")
    parser.add_argument("--map-hex", metavar="HEX", help="map a 32-byte debug/status packet hex string")
    args = parser.parse_args(argv)

    if args.json:
        print(fpga_replay_mapper.fpga_replay_mapper_json())
        return 0

    if args.example:
        print(json.dumps(fpga_replay_mapper.example_replay_mapping().as_dict(), indent=2, sort_keys=True))
        return 0

    if args.map_hex:
        try:
            mapping = fpga_replay_mapper.map_debug_status_hex(args.map_hex)
        except ValueError as exc:
            print("FPGA replay mapping failed:")
            print(f"- {exc}")
            return 1
        print(json.dumps(mapping.as_dict(), indent=2, sort_keys=True))
        return 0

    issues = fpga_replay_mapper.validate_fpga_replay_mapper(ROOT)
    if issues:
        print("FPGA replay mapper issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA replay mapper issues: 0")
        return 0

    print(fpga_replay_mapper.render_replay_mapping())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
