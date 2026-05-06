#!/usr/bin/env python3
"""Print the I20-S02 golden retire trace corpus as deterministic JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import golden_traces


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case",
        dest="case_id",
        help="print only one golden trace case by ID",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list case IDs and categories instead of JSON packets",
    )
    args = parser.parse_args(argv)

    cases = golden_traces.golden_trace_corpus()
    if args.case_id:
        cases = (golden_traces.golden_trace_case_by_id(args.case_id),)

    if args.list:
        for case in cases:
            print(f"{case.case_id}\t{case.category}")
        return 0

    print(json.dumps(tuple(case.as_dict() for case in cases), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
