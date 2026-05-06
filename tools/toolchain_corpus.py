#!/usr/bin/env python3
"""Print or validate the I17-S04 toolchain regression corpus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import toolchain_corpus


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case",
        dest="case_id",
        help="print only one toolchain corpus case by ID",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list case IDs and categories instead of JSON fixtures",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the corpus and print a short status",
    )
    args = parser.parse_args(argv)

    cases = toolchain_corpus.toolchain_corpus()
    if args.case_id:
        cases = (toolchain_corpus.toolchain_case_by_id(args.case_id),)

    if args.check:
        issues = toolchain_corpus.validate_toolchain_corpus(cases)
        if issues:
            print("Toolchain corpus issues:")
            for issue in issues:
                print(f"- {issue}")
            return 1
        print("Toolchain corpus issues: 0")
        return 0

    if args.list:
        for case in cases:
            print(f"{case.case_id}\t{case.category.value}")
        return 0

    print(json.dumps(tuple(case.as_dict() for case in cases), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
