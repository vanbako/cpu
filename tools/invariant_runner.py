#!/usr/bin/env python3
"""Run seed-stable CPU v0.1 invariant cases.

Owner stories:
- I16-S03: seed-stable invariant runner.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import invariant_runner


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0, help="deterministic run seed")
    parser.add_argument(
        "--family",
        action="append",
        help="invariant family to run; repeat to select multiple families",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        help="exact invariant case id to replay; repeat to select multiple cases",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list selected invariant case ids without running them",
    )
    args = parser.parse_args(argv)

    families = tuple(args.family or ())
    try:
        if args.list:
            selected_families = families or invariant_runner.available_families()
            for family in selected_families:
                print(f"{family}:")
                for case_id in invariant_runner.invariant_case_ids((family,)):
                    print(f"  {case_id}")
            return 0

        report = invariant_runner.run_invariants(
            seed=args.seed,
            families=families,
            case_ids=tuple(args.case_id or ()),
        )
    except (TypeError, ValueError) as exc:
        print(f"invariant runner error: {exc}")
        return 2

    print(invariant_runner.render_report(report))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
