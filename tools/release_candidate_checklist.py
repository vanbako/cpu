#!/usr/bin/env python3
"""Validate and audit the I33-S01 release-candidate checklist gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import release_candidate_checklist


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the RC checklist profile")
    parser.add_argument("--json", action="store_true", help="print the checklist profile as JSON")
    parser.add_argument("--template", action="store_true", help="print the checklist evidence template")
    parser.add_argument(
        "--audit-evidence",
        nargs="?",
        const=str(release_candidate_checklist.RELEASE_CANDIDATE_CHECKLIST_EVIDENCE),
        metavar="PATH",
        help="audit captured release-candidate checklist evidence",
    )
    args = parser.parse_args(argv)

    if args.json:
        print(release_candidate_checklist.release_candidate_checklist_json())
        return 0

    if args.template:
        print(release_candidate_checklist.release_candidate_checklist_template(), end="")
        return 0

    if args.audit_evidence:
        evidence_path = _repo_relative_path(Path(args.audit_evidence))
        if evidence_path is None:
            print("Release-candidate checklist audit:")
            print("- evidence path must be inside the repository")
            return 1
        audit = release_candidate_checklist.load_release_candidate_checklist_audit(
            ROOT,
            evidence_path,
        )
        print(json.dumps(audit.as_dict(), indent=2, sort_keys=True))
        return 0 if audit.accepted else 1

    issues = release_candidate_checklist.validate_release_candidate_checklist(ROOT)
    if issues:
        print("Release-candidate checklist issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.check:
        print("Release-candidate checklist issues: 0")
        return 0

    print(release_candidate_checklist.render_release_candidate_checklist())
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
