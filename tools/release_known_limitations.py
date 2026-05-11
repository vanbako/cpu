#!/usr/bin/env python3
"""Validate and audit the I33-S04 known-limitations freeze gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import release_known_limitations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the known-limitations profile")
    parser.add_argument("--json", action="store_true", help="print the known-limitations profile as JSON")
    parser.add_argument("--template", action="store_true", help="print the known-limitations evidence template")
    parser.add_argument(
        "--audit-evidence",
        nargs="?",
        const=str(release_known_limitations.RELEASE_LIMITATIONS_EVIDENCE),
        metavar="PATH",
        help="audit captured known-limitations freeze evidence",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(release_known_limitations.release_limitations_json())
        return 0

    if args.template:
        print(release_known_limitations.release_limitations_template(), end="")
        return 0

    if args.audit_evidence:
        evidence_path = _repo_relative_path(Path(args.audit_evidence))
        if evidence_path is None:
            print("Known-limitations freeze audit:")
            print("- evidence path must be inside the repository")
            return 1
        audit = release_known_limitations.load_release_limitations_audit(
            ROOT,
            evidence_path,
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.accepted else 1

    issues = release_known_limitations.validate_release_limitations(ROOT)
    if issues:
        print("Known-limitations freeze issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("Known-limitations freeze issues: 0")
        return 0

    print(release_known_limitations.render_release_limitations())
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
