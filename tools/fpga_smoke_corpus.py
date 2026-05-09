#!/usr/bin/env python3
"""Validate and print the I26-S05 FPGA smoke-program corpus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_smoke_corpus


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the FPGA smoke corpus")
    parser.add_argument("--json", action="store_true", help="print the corpus as JSON")
    parser.add_argument("--list", action="store_true", help="list corpus case IDs")
    parser.add_argument("--case", metavar="CASE_ID", help="print one corpus case as JSON")
    args = parser.parse_args(argv)

    profile = fpga_smoke_corpus.fpga_smoke_corpus_profile()

    if args.list:
        for case in profile.cases:
            print(f"{case.case_id}\t{case.category}\t{case.program_id}\t{case.bram_image_status}")
        return 0

    if args.case:
        try:
            case = profile.case_by_id(args.case)
        except KeyError:
            print(f"unknown FPGA smoke corpus case: {args.case}")
            return 1
        print(json.dumps(case.as_dict(), indent=2, sort_keys=True))
        return 0

    if args.json:
        print(fpga_smoke_corpus.fpga_smoke_corpus_json())
        return 0

    issues = fpga_smoke_corpus.validate_fpga_smoke_corpus(ROOT)
    if issues:
        print("FPGA smoke corpus issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA smoke corpus issues: 0")
        return 0

    print(fpga_smoke_corpus.render_fpga_smoke_corpus())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
