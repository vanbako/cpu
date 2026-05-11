#!/usr/bin/env python3
"""Validate and audit the I33-S02 release regression capture gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import release_regression_capture


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the regression capture profile")
    parser.add_argument("--json", action="store_true", help="print the regression capture profile as JSON")
    parser.add_argument("--template", action="store_true", help="print the regression capture evidence template")
    parser.add_argument(
        "--audit-evidence",
        nargs="?",
        const=str(release_regression_capture.RELEASE_REGRESSION_EVIDENCE),
        metavar="PATH",
        help="audit captured release regression evidence",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(release_regression_capture.release_regression_capture_json())
        return 0

    if args.template:
        print(release_regression_capture.release_regression_capture_template(), end="")
        return 0

    if args.audit_evidence:
        evidence_path = _repo_relative_path(Path(args.audit_evidence))
        if evidence_path is None:
            print("Release regression capture audit:")
            print("- evidence path must be inside the repository")
            return 1
        audit = release_regression_capture.load_release_regression_capture_audit(
            ROOT,
            evidence_path,
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.accepted else 1

    issues = release_regression_capture.validate_release_regression_capture(ROOT)
    if issues:
        print("Release regression capture issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("Release regression capture issues: 0")
        return 0

    print(release_regression_capture.render_release_regression_capture())
    return 0


def _repo_relative_path(path: Path) -> Path | None:
    if not path.is_absolute():
        return path
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
