#!/usr/bin/env python3
"""Validate and print the I29-S04 FPGA external-memory policy profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import fpga_external_memory_policy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the external-memory policy")
    parser.add_argument("--json", action="store_true", help="print the policy profile as JSON")
    parser.add_argument("--run", action="store_true", help="run the policy fixtures as JSON")
    parser.add_argument("--rules", action="store_true", help="list policy rules")
    parser.add_argument("--fixtures", action="store_true", help="list policy fixture results")
    args = parser.parse_args(argv)

    profile = fpga_external_memory_policy.fpga_external_memory_policy_profile()

    if args.json:
        print(fpga_external_memory_policy.fpga_external_memory_policy_json())
        return 0

    if args.run:
        print(fpga_external_memory_policy.fpga_external_memory_policy_run_json())
        return 0

    if args.rules:
        for rule in profile.rules:
            print(f"{rule.name}\t{rule.area}\t{rule.requirement}")
        return 0

    if args.fixtures:
        run = fpga_external_memory_policy.run_fpga_external_memory_policy_fixtures()
        for fixture in run.fixtures:
            print(f"{fixture.case_id}\t{fixture.area}\t{fixture.passed}\t{fixture.observed}")
        return 0

    issues = fpga_external_memory_policy.validate_fpga_external_memory_policy(ROOT)
    if issues:
        print("FPGA external-memory policy issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("FPGA external-memory policy issues: 0")
        return 0

    print(fpga_external_memory_policy.render_fpga_external_memory_policy())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
