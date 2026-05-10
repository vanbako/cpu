#!/usr/bin/env python3
"""Validate and print the I30-S02 FPGA SoC top data/MMIO decoder contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_soc_top_decoder


def _parse_address(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the decoder contract")
    parser.add_argument("--json", action="store_true", help="print the decoder profile as JSON")
    parser.add_argument("--windows", action="store_true", help="list decode windows")
    parser.add_argument("--plan", action="store_true", help="print the Verilator command")
    parser.add_argument("--decode", type=_parse_address, metavar="CELL_ADDR", help="decode one cell address")
    parser.add_argument("--len-cells", type=int, default=1, help="transfer length for --decode")
    parser.add_argument("--write", action="store_true", help="treat --decode as a write")
    args = parser.parse_args(argv)

    profile = fpga_soc_top_decoder.fpga_soc_top_decoder_profile()

    if args.windows:
        for window in profile.windows:
            print(
                f"{window.target}\t0x{window.base_cell:08X}\t"
                f"0x{window.end_cell:08X}\ttag_sidecar={window.tag_sidecar}"
            )
        return 0

    if args.plan:
        print(profile.verilator_command)
        return 0

    if args.decode is not None:
        result = fpga_soc_top_decoder.decode_soc_top_address(
            args.decode,
            len_cells=args.len_cells,
            write=args.write,
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    if args.json:
        print(fpga_soc_top_decoder.fpga_soc_top_decoder_json())
        return 0

    issues = fpga_soc_top_decoder.validate_fpga_soc_top_decoder(ROOT)
    if issues:
        print("FPGA SoC top decoder issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA SoC top decoder issues: 0")
        return 0

    print(fpga_soc_top_decoder.render_fpga_soc_top_decoder())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
