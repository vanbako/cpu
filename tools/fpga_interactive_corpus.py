#!/usr/bin/env python3
"""Validate and print the I32-S05 FPGA interactive program corpus."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_interactive_corpus


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the interactive corpus")
    parser.add_argument("--json", action="store_true", help="print the corpus profile as JSON")
    parser.add_argument("--list", action="store_true", help="list interactive corpus cases")
    parser.add_argument("--case", metavar="ID", help="print one interactive corpus case as JSON")
    args = parser.parse_args(argv)

    profile = fpga_interactive_corpus.fpga_interactive_corpus_profile()

    if args.json:
        print(fpga_interactive_corpus.fpga_interactive_corpus_json())
        return 0

    if args.list:
        for case in profile.cases:
            print(f"{case.case_id}\t{case.category}\t{case.program_id}\t{case.load_mode}")
        return 0

    if args.case:
        try:
            case = profile.case_by_id(args.case)
        except KeyError:
            print(f"unknown interactive corpus case: {args.case}")
            return 1
        import json

        print(json.dumps(case.as_dict(), indent=2, sort_keys=True))
        return 0

    issues = fpga_interactive_corpus.validate_fpga_interactive_corpus(ROOT)
    if issues:
        print("FPGA interactive corpus issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA interactive corpus issues: 0")
        return 0

    print(fpga_interactive_corpus.render_fpga_interactive_corpus(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
