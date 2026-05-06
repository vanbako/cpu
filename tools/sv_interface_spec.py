#!/usr/bin/env python3
"""Render the I20-S03 SystemVerilog package/interface generated spec."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import sv_contract


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="output format",
    )
    args = parser.parse_args(argv)

    if args.format == "json":
        print(sv_contract.systemverilog_contract_json())
    else:
        print(sv_contract.render_systemverilog_contract_markdown(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
